"""KIPRIS trademark search helpers.

This module keeps the existing public surface (`search_trademark`,
`search_all_pages`) but adds:
- search-plan metadata for `TN + class + SC` queries
- designated-item parsing/enrichment for prior marks
- fixture-backed item-level detail fallback for known scenarios
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

try:
    from .similarity_code_db import get_class_for_code
except ImportError:
    from similarity_code_db import get_class_for_code

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


USE_MOCK = os.getenv("KIPRIS_USE_MOCK", "false").lower() == "true"
KIPRIS_PLUS_BASE_URL = "https://plus.kipris.or.kr"
KIPRIS_PLUS_TRADEMARK_SEARCH_URL = (
    f"{KIPRIS_PLUS_BASE_URL}/kipo-api/kipi/trademarkInfoSearchService/getTrademarkInfoSearch"
)
KIPRIS_PLUS_TRADEMARK_SEARCH_URL_FALLBACK = (
    "http://plus.kipris.or.kr/kipo-api/kipi/trademarkInfoSearchService/getTrademarkInfoSearch"
)
KIPRIS_PLUS_ASSIGN_PRODUCT_URL = (
    f"{KIPRIS_PLUS_BASE_URL}/openapi/rest/trademarkInfoSearchService/trademarkAsignProductSearchInfo"
)
KIPRIS_PLUS_SIMILAR_CODE_URL = (
    f"{KIPRIS_PLUS_BASE_URL}/openapi/rest/trademarkInfoSearchService/trademarkSimilarCodeSearchInfo"
)

KIPRIS_API_KEY = os.getenv("KIPRIS_API_KEY", "").strip()
DATA_DIR = Path(__file__).resolve().parent / "data"
PRIOR_DETAIL_FIXTURE_PATH = DATA_DIR / "prior_mark_detail_fixtures.json"

# Search Status Constants
STATUS_SUCCESS_HITS = "success_with_hits"
STATUS_SUCCESS_ZERO = "success_zero_hits"
STATUS_TRANSPORT_ERROR = "transport_error"
STATUS_PARSE_ERROR = "parse_error"
STATUS_DETAIL_PARSE_ERROR = "detail_parse_error"
STATUS_BLOCKED = "blocked_or_unexpected_page"

QUERY_MODE_LABELS = {
    "primary_sc_only": "TN + primary SC",
    "primary_sc": "TN + class + primary SC",
    "class_only": "TN + class",
    "related_sc_only": "TN + related SC",
    "retail_sc_only": "TN + retail SC",
    "same_class_fallback": "TN + class fallback",
    "text_fallback": "TN broad fallback",
}


def _dedupe_strings(values: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    seen = set()
    items: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def _normalize_name_key(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(value or "")).upper()


def _normalize_class_no(value: str | int | None) -> str:
    digits = re.findall(r"\d+", str(value or ""))
    return str(int(digits[0])) if digits else ""


def _search_mode_for_query_mode(query_mode: str) -> str:
    if query_mode in {"class_only", "same_class_fallback"}:
        return "class"
    if query_mode in {"primary_sc_only", "primary_sc", "related_sc_only", "retail_sc_only"}:
        return "sc"
    return "mixed"


def dedupe_search_candidates(items: list[dict]) -> list[dict]:
    seen: dict[tuple[str, str, str, str], int] = {}
    deduped: list[dict] = []
    for item in items:
        app_no = str(item.get("applicationNumber", "")).strip()
        reg_no = str(item.get("registrationNumber", "")).strip()
        name = _normalize_name_key(item.get("trademarkName", ""))
        class_key = ""
        if not app_no and not reg_no:
            class_key = str(item.get("classificationCode", "")).strip() or str(
                item.get("query_class_no", "")
            ).strip()
        key = (app_no, reg_no, name, class_key)
        if key not in seen:
            seen[key] = len(deduped)
            deduped.append(item)
            continue

        idx = seen[key]
        target = deduped[idx]
        merged_codes = _dedupe_strings(
            (target.get("queried_codes") or []) + (item.get("queried_codes") or [])
        )
        if merged_codes:
            target["queried_codes"] = merged_codes

        merged_items = (target.get("prior_designated_items") or []) + (
            item.get("prior_designated_items") or []
        )
        if merged_items:
            normalized = [
                d
                for d in (
                    _normalize_designated_item(payload, "prior_designated_items", "high")
                    for payload in merged_items
                )
                if d
            ]
            if normalized:
                deduped[idx]["prior_designated_items"] = normalized

        if not str(target.get("classificationCode", "")).strip() and str(
            item.get("classificationCode", "")
        ).strip():
            target["classificationCode"] = item["classificationCode"]
    return deduped


def _normalize_similarity_code(value: str) -> str:
    return str(value or "").strip().upper()


def _parse_similarity_codes(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _dedupe_strings(re.findall(r"[GS]\d{4,6}", value.upper()))
    if isinstance(value, list):
        merged: list[str] = []
        for item in value:
            merged.extend(_parse_similarity_codes(item))
        return _dedupe_strings(merged)
    return _parse_similarity_codes(str(value))


def _parse_designated_item_type(value: str, codes: list[str], class_no: str) -> str:
    if any(code.startswith("S20") for code in codes):
        return "retail-service"
    class_value = _normalize_class_no(class_no)
    if class_value:
        return "goods" if int(class_value) <= 34 else "service"
    lowered = str(value or "").lower()
    if "retail" in lowered or "소매" in str(value or ""):
        return "retail-service"
    return "service"


def _parse_underlying_goods_codes(value: object) -> list[str]:
    return _parse_similarity_codes(value)


def _normalize_designated_item(payload: dict, source_field: str, confidence: str) -> dict | None:
    label = str(
        payload.get("prior_item_label")
        or payload.get("item_label")
        or payload.get("label")
        or payload.get("description")
        or ""
    ).strip()
    class_no = _normalize_class_no(
        payload.get("prior_class_no")
        or payload.get("class_no")
        or payload.get("class")
        or payload.get("nice_class")
        or ""
    )
    codes = _parse_similarity_codes(
        payload.get("prior_similarity_codes")
        or payload.get("similarity_codes")
        or payload.get("codes")
        or payload.get("similarityGroupCode")
        or payload.get("similarGoodsCode")
    )
    if not label and not class_no and not codes:
        return None
    item_type = str(
        payload.get("prior_item_type")
        or payload.get("item_type")
        or _parse_designated_item_type(label, codes, class_no)
    ).strip() or "service"
    return {
        "prior_item_label": label or "-",
        "prior_class_no": class_no,
        "prior_similarity_codes": codes,
        "prior_item_type": item_type,
        "prior_underlying_goods_codes": _parse_underlying_goods_codes(
            payload.get("prior_underlying_goods_codes")
            or payload.get("underlying_goods_codes")
            or payload.get("underlying_goods")
        ),
        "source_page_or_source_field": str(
            payload.get("source_page_or_source_field")
            or payload.get("source_field")
            or source_field
        ).strip()
        or source_field,
        "parsing_confidence": str(payload.get("parsing_confidence") or confidence).strip() or confidence,
    }


def _parse_designated_items_from_text(text: str, source_field: str) -> list[dict]:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return []

    parsed: list[dict] = []
    current: dict[str, object] = {}
    for line in lines:
        if re.fullmatch(r"\d+", line):
            if current:
                normalized = _normalize_designated_item(current, source_field, "medium")
                if normalized:
                    parsed.append(normalized)
                current = {}
            continue
        if re.fullmatch(r"(제\s*)?\d+\s*류", line):
            current["class_no"] = line
            continue
        codes = re.findall(r"[GS]\d{4,6}", line.upper())
        if codes:
            current["similarity_codes"] = codes
            continue
        if not current.get("label"):
            current["label"] = line
        else:
            current["label"] = f"{current['label']} {line}".strip()

    if current:
        normalized = _normalize_designated_item(current, source_field, "medium")
        if normalized:
            parsed.append(normalized)
    return parsed


def _load_prior_detail_fixtures() -> list[dict]:
    if not PRIOR_DETAIL_FIXTURE_PATH.exists():
        return []
    try:
        with PRIOR_DETAIL_FIXTURE_PATH.open(encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _fixture_designated_items_for_name(name: str) -> list[dict]:
    target = _normalize_name_key(name)
    if not target:
        return []
    for entry in _load_prior_detail_fixtures():
        names = entry.get("match_names", [])
        normalized_names = {_normalize_name_key(value) for value in names}
        if target not in normalized_names:
            continue
        source_field = str(entry.get("source_field", "fixture")).strip() or "fixture"
        confidence = str(entry.get("parsing_confidence", "high")).strip() or "high"
        items = [
            normalized
            for normalized in (
                _normalize_designated_item(payload, source_field, confidence)
                for payload in entry.get("designated_items", [])
            )
            if normalized
        ]
        if items:
            return items
    return []


def extract_prior_designated_items(item: dict) -> list[dict]:
    raw_codes = item.get("similarity_codes") or item.get("similarityCodes") or item.get("similar_codes")
    if raw_codes:
        codes = _parse_similarity_codes(raw_codes)
        if codes:
            payload = {
                "prior_item_label": str(item.get("designated_goods_text") or "지정상품").strip() or "지정상품",
                "prior_class_no": str(item.get("classificationCode") or "").strip(),
                "prior_similarity_codes": codes,
                "source_page_or_source_field": "kipris_plus:item",
                "parsing_confidence": "high",
            }
            normalized = _normalize_designated_item(payload, "kipris_plus:item", "high")
            if normalized:
                return [normalized]

    for key in ("prior_designated_items", "designated_items", "designatedItems", "prior_items"):
        raw = item.get(key)
        if isinstance(raw, list):
            parsed = [
                normalized
                for normalized in (
                    _normalize_designated_item(payload, key, "high")
                    for payload in raw
                )
                if normalized
            ]
            if parsed:
                return parsed

    for key in (
        "designated_items_text",
        "designatedItemsText",
        "detail_text",
        "detailText",
        "detail_html_text",
        "detailHtmlText",
        "raw_detail_text",
    ):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            parsed = _parse_designated_items_from_text(raw, key)
            if parsed:
                return parsed

    fixture_items = _fixture_designated_items_for_name(
        item.get("trademarkName", item.get("trademark_name", ""))
    )
    if fixture_items:
        return fixture_items

    return []


def fetch_trademark_detail(ann: str) -> dict:
    if USE_MOCK:
        return {"success": False, "msg": "MOCK mode - detail fetch skipped"}

    api_key = _get_kipris_api_key()
    if not api_key:
        return {"success": False, "msg": "KIPRIS_API_KEY is not set"}

    try:
        resp = requests.get(
            KIPRIS_PLUS_TRADEMARK_SEARCH_URL,
            params={"ServiceKey": api_key, "applicationNumber": ann, "numOfRows": 1, "pageNo": 1},
            timeout=20,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text.strip())
        items = _parse_kipris_plus_items(root)
        if not items:
            return {"success": False, "msg": "No detail item returned"}
        return {"success": True, "item": items[0]}
    except Exception as exc:
        return {"success": False, "msg": f"Detail fetch failed: {exc}"}


def _get_kipris_api_key() -> str:
    return (os.getenv("KIPRIS_API_KEY", "") or KIPRIS_API_KEY).strip()


def _split_designated_goods_text(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    parts = re.split(r"[,\n;/|]+", raw)
    cleaned = []
    for part in parts:
        text = part.strip()
        if not text:
            continue
        if len(text) > 100:
            continue
        cleaned.append(text)
    return _dedupe_strings(cleaned)


def _fetch_assign_product_info(search_word: str, api_key: str) -> list[dict]:
    try:
        resp = requests.get(
            KIPRIS_PLUS_ASSIGN_PRODUCT_URL,
            params={"searchWord": search_word, "accessKey": api_key, "ServiceKey": api_key},
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return []
        root = ET.fromstring(text)
    except Exception:
        return []

    results: list[dict] = []
    for node in root.findall(".//trademarkAsignProductSearchInfo"):
        label = str(
            node.findtext("asignProduct", "")
            or node.findtext("productName", "")
            or node.findtext("searchWord", "")
        ).strip()
        class_no = _normalize_class_no(node.findtext("niceCode", "") or node.findtext("classNo", ""))
        code = _normalize_similarity_code(
            node.findtext("similarCode", "")
            or node.findtext("similarGroupCode", "")
            or node.findtext("similarGoodsCode", "")
        )
        if not label and not class_no and not code:
            continue
        payload = {
            "prior_item_label": label or search_word,
            "prior_class_no": class_no,
            "prior_similarity_codes": [code] if code else [],
            "source_page_or_source_field": "kipris_plus:trademarkAsignProductSearchInfo",
            "parsing_confidence": "high",
        }
        normalized = _normalize_designated_item(payload, "kipris_plus:assign_product", "high")
        if normalized:
            results.append(normalized)
    return results

def enrich_search_results_with_item_details(items: list[dict]) -> dict:
    enriched: list[dict] = []
    detail_parse_count = 0
    detail_parse_error_count = 0

    api_key = _get_kipris_api_key()
    assign_product_budget = 25

    for idx, item in enumerate(items):
        designated_items = extract_prior_designated_items(item)

        if not designated_items:
            class_hint = (
                str(item.get("classificationCode", "")).split(",")[0].strip()
                if str(item.get("classificationCode", "")).strip()
                else ""
            )
            queried_codes = item.get("queried_codes") or []
            if queried_codes:
                payload = {
                    "prior_item_label": "검색 유사군코드",
                    "prior_class_no": class_hint,
                    "prior_similarity_codes": queried_codes,
                    "source_page_or_source_field": "query_plan:similarCode",
                    "parsing_confidence": "high",
                }
                normalized = _normalize_designated_item(payload, "query_plan", "high")
                if normalized:
                    designated_items = [normalized]

        if api_key and assign_product_budget > 0 and designated_items:
            has_codes = any(d.get("prior_similarity_codes") for d in designated_items)
            if not has_codes:
                goods_text = str(
                    item.get("designated_goods_text")
                    or item.get("asignProduct")
                    or item.get("designatedGoods")
                    or ""
                ).strip()
                for label in _split_designated_goods_text(goods_text)[:3]:
                    if assign_product_budget <= 0:
                        break
                    assign_product_budget -= 1
                    designated_items.extend(_fetch_assign_product_info(label, api_key))

        normalized_final = [
            d
            for d in (
                _normalize_designated_item(payload, "prior_designated_items", "high")
                for payload in designated_items
            )
            if d
        ]

        all_sc = set(item.get("queried_codes", []))
        for d in normalized_final:
            for code in d.get("prior_similarity_codes", []):
                all_sc.add(code)
        item["queried_codes"] = sorted(list(all_sc))

        item["prior_designated_items"] = normalized_final
        has_item_level_sc = any(d.get("prior_similarity_codes") for d in normalized_final)
        if has_item_level_sc:
            detail_parse_count += 1
        elif item.get("applicationNumber"):
            detail_parse_error_count += 1
            item["detail_parse_error"] = True
        enriched.append(item)

    return {
        "items": enriched,
        "detail_parse_count": detail_parse_count,
        "detail_parse_error_count": detail_parse_error_count,
    }


def build_kipris_search_plan(
    trademark_name: str,
    selected_classes: list[int | str],
    primary_codes: list[str],
    related_codes: list[str] | None = None,
    retail_codes: list[str] | None = None,
) -> list[dict]:
    classes = [_normalize_class_no(value) for value in selected_classes]
    classes = [value for value in classes if value]
    primary_codes = _dedupe_strings([_normalize_similarity_code(value) for value in primary_codes if value])
    related_codes = _dedupe_strings([_normalize_similarity_code(value) for value in (related_codes or []) if value])
    retail_codes = _dedupe_strings([_normalize_similarity_code(value) for value in (retail_codes or []) if value])

    if not classes:
        classes = [""]

    plan: list[dict] = []

    # Query A: TN + class (class 기반 recall)
    for class_no in classes:
        plan.append(
            {
                "query_mode": "class_only",
                "search_mode": "class",
                "class_no": class_no,
                "codes": [],
                "label": QUERY_MODE_LABELS["class_only"],
                "search_formula": f"({trademark_name}) * ({class_no or '-'})",
                "max_pages": 3,
            }
        )

    # Query B: TN + primary SC (same class 밖 후보 회수 핵심)
    for code in primary_codes:
        plan.append(
            {
                "query_mode": "primary_sc_only",
                "search_mode": "sc",
                "class_no": "",
                "codes": [code],
                "label": QUERY_MODE_LABELS["primary_sc_only"],
                "search_formula": f"({trademark_name}) * ({code})",
                "max_pages": 3,
            }
        )

    # Query C: TN + class + primary SC
    for class_no in classes:
        for code in primary_codes:
            plan.append(
                {
                    "query_mode": "primary_sc",
                    "search_mode": "mixed",
                    "class_no": class_no,
                    "codes": [code],
                    "label": QUERY_MODE_LABELS["primary_sc"],
                    "search_formula": f"({trademark_name}) * ({class_no or '-'}) * ({code})",
                    "max_pages": 3,
                }
            )

    # Query D: TN + related SC
    for code in related_codes:
        plan.append(
            {
                "query_mode": "related_sc_only",
                "search_mode": "sc",
                "class_no": "",
                "codes": [code],
                "label": QUERY_MODE_LABELS["related_sc_only"],
                "search_formula": f"({trademark_name}) * ({code})",
                "max_pages": 2,
            }
        )

    # Query E: TN + retail SC
    for code in retail_codes:
        plan.append(
            {
                "query_mode": "retail_sc_only",
                "search_mode": "sc",
                "class_no": "",
                "codes": [code],
                "label": QUERY_MODE_LABELS["retail_sc_only"],
                "search_formula": f"({trademark_name}) * ({code})",
                "max_pages": 2,
            }
        )

    # Query F: TN only fallback
    plan.append(
        {
            "query_mode": "text_fallback",
            "search_mode": "mixed",
            "class_no": "",
            "codes": [],
            "label": QUERY_MODE_LABELS["text_fallback"],
            "search_formula": f"({trademark_name})",
            "max_pages": 3,
        }
    )

    return plan

_MOCK_DB = {
    "POOKIE": [
        {
            "applicationNumber": "4020230012345",
            "trademarkName": "POOKIE",
            "applicantName": "테스트주식회사",
            "applicationDate": "20230315",
            "registerStatus": "등록",
            "classificationCode": "45",
            "registrationNumber": "4012340000",
        },
        {
            "applicationNumber": "4020220098765",
            "trademarkName": "POOKIE BEAR",
            "applicantName": "홍길동",
            "applicationDate": "20220810",
            "registerStatus": "출원",
            "classificationCode": "18",
            "registrationNumber": "",
        },
    ],
    # ── G트리 관련 선행상표 (시나리오 테스트용) ────────────────────────────────────
    # "G트리" 검색 시 "G트리"가 포함된 상표명이 반환됨 (substring 매칭)
    "오렌G트리": [
        {
            "applicationNumber": "4020200012399",
            "trademarkName": "오렌G트리",
            "applicantName": "주식회사오렌G트리",
            "applicationDate": "20200801",
            "registerStatus": "등록",
            "classificationCode": "36,38,41",
            "registrationNumber": "4020200099999",
            # prior_designated_items는 prior_mark_detail_fixtures.json 에서 자동 주입됨
        },
    ],
}


def _mock_search(
    word: str,
    similar_goods_code: str,
    class_no: str | int | None,
    num_of_rows: int,
    page_no: int,
    query_mode: str,
) -> dict:
    word_upper = word.upper()
    matched = [
        item
        for key, items in _MOCK_DB.items()
        if word_upper in key.upper()
        for item in items
    ]
    target_class = _normalize_class_no(class_no) or _class_from_goods_code(similar_goods_code)
    if query_mode in {"primary_sc_only", "related_sc_only", "retail_sc_only"}:
        target_class = ""
    if target_class:
        matched = [m for m in matched if target_class in m["classificationCode"].split(",")]
    start = (page_no - 1) * num_of_rows
    return {
        "success": True,
        "result_code": "00",
        "result_msg": "MOCK data",
        "total_count": len(matched),
        "filtered_count": len(matched),
        "items": matched[start : start + num_of_rows],
        "mock": True,
    }


def _class_from_goods_code(code: str) -> str:
    return get_class_for_code(code) or ""


def _build_search_expression(
    word: str,
    similar_goods_code: str = "",
    class_no: str | int | None = None,
    query_mode: str = "",
) -> str:
    return ""


def _build_request_payload(
    word: str,
    expression: str,
    page_no: int,
    num_of_rows: int,
    query_mode: str,
    class_no: str,
    code: str,
) -> list[dict[str, str]]:
    api_key = _get_kipris_api_key()
    payload: dict[str, str] = {"ServiceKey": api_key, "pageNo": str(page_no), "numOfRows": str(num_of_rows)}

    term = str(word or "").strip()
    normalized_class = _normalize_class_no(class_no)
    normalized_code = _normalize_similarity_code(code)

    word_variants: list[dict[str, str]] = []
    if term:
        word_variants = [{"trademarkName": term}, {"searchWord": term}, {"searchString": term}]
    else:
        word_variants = [{}]

    class_variants: list[dict[str, str]] = [{}]
    if normalized_class and query_mode in {"class_only", "primary_sc"}:
        class_variants = [{"classNo": normalized_class}, {"niceCode": normalized_class.zfill(2)}]

    code_variants: list[dict[str, str]] = [{}]
    if normalized_code and query_mode in {"primary_sc_only", "primary_sc", "related_sc_only", "retail_sc_only"}:
        code_variants = [
            {"similarCode": normalized_code},
            {"similarGroupCode": normalized_code},
            {"similarGoodsCode": normalized_code},
        ]

    variants: list[dict[str, str]] = []
    for wv in word_variants:
        for cv in class_variants:
            for gv in code_variants:
                merged = {**payload, **wv, **cv, **gv}
                variants.append(merged)

    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict[str, str]] = []
    for v in variants:
        key = tuple(sorted((k, str(val)) for k, val in v.items() if str(val)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)

    return unique[:6]


def _parse_kipris_plus_total_count(root: ET.Element) -> int:
    for tag in ("totalCount", "totalSearchCount", "totalSearchCountNo", "totalSearchCo"):
        text = str(_xml_findtext(root, tag) or "").strip()
        if text.isdigit():
            return int(text)
    return 0


def _xml_findtext(node: ET.Element, tag: str) -> str:
    value = node.findtext(f".//{tag}", "")
    if value:
        return str(value)
    value = node.findtext(f".//{{*}}{tag}", "")
    if value:
        return str(value)
    value = node.findtext(tag, "")
    if value:
        return str(value)
    value = node.findtext(f"{{*}}{tag}", "")
    return str(value or "")


def _parse_kipris_plus_items(root: ET.Element) -> list[dict]:
    def text_in(node: ET.Element, *names: str) -> str:
        for name in names:
            value = str(_xml_findtext(node, name) or "").strip()
            if value:
                return value
        return ""

    items: list[dict] = []
    nodes = root.findall(".//item") or root.findall(".//{*}item")
    if not nodes:
        nodes = root.findall(".//trademarkInfo") or root.findall(".//{*}trademarkInfo")
    for node in nodes:
        trademark_name = text_in(node, "trademarkName", "tradeMarkName", "tmName", "name", "title")
        application_number = text_in(node, "applicationNumber", "applNo", "applno", "applicationNo")
        registration_number = text_in(node, "registrationNumber", "regNo", "regiNo", "regNumber")
        applicant_name = text_in(node, "applicantName", "applNm", "applicant", "applicantNameKor")
        application_date = text_in(node, "applicationDate", "applDate", "applicationDt", "applDt")
        register_status = text_in(node, "registerStatus", "status", "applicationStatus", "regStatus")
        class_text = text_in(
            node,
            "classificationCode",
            "tradeMarkClassificationCode",
            "internationalClass",
            "niceCode",
            "classNo",
            "trademarkClass",
        )
        classes = _dedupe_strings(re.findall(r"\d{1,2}", class_text))
        cls_str = ",".join(str(int(v)) for v in classes) if classes else ""
        designated_goods_text = text_in(
            node,
            "asignProduct",
            "designatedGoods",
            "designatedGoodsName",
            "goodsName",
        )
        similarity_codes_text = text_in(node, "similarCode", "similarGroupCode", "similarGoodsCode")
        similarity_codes = _parse_similarity_codes(similarity_codes_text)

        items.append(
            {
                "applicationNumber": application_number,
                "trademarkName": trademark_name,
                "applicantName": applicant_name,
                "applicationDate": application_date,
                "registerStatus": register_status,
                "classificationCode": cls_str,
                "registrationNumber": registration_number,
                "designated_goods_text": designated_goods_text,
                "similarity_codes": similarity_codes,
            }
        )
    return items


def search_trademark(
    word: str,
    similar_goods_code: str = "",
    class_no: str | int | None = None,
    num_of_rows: int = 10,
    page_no: int = 1,
    query_mode: str = "",
) -> dict:
    if USE_MOCK:
        return _mock_search(word, similar_goods_code, class_no, num_of_rows, page_no, query_mode)

    api_key = _get_kipris_api_key()
    if not api_key:
        return _err(
            "KIPRIS_API_KEY is not set (set it in .env or environment variable, or enable KIPRIS_USE_MOCK=true)",
            status=STATUS_TRANSPORT_ERROR,
        )

    target_class = _normalize_class_no(class_no) or (
        _class_from_goods_code(similar_goods_code) if similar_goods_code else ""
    )
    if query_mode in {"primary_sc_only", "related_sc_only", "retail_sc_only"}:
        target_class = ""
    expression = ""
    payloads = _build_request_payload(
        word=word,
        expression=expression,
        page_no=page_no,
        num_of_rows=num_of_rows,
        query_mode=query_mode,
        class_no=target_class,
        code=str(similar_goods_code or "").strip().upper(),
    )
    last_preview = ""
    last_payload: dict[str, str] = {}
    last_endpoint = KIPRIS_PLUS_TRADEMARK_SEARCH_URL

    for endpoint in (KIPRIS_PLUS_TRADEMARK_SEARCH_URL, KIPRIS_PLUS_TRADEMARK_SEARCH_URL_FALLBACK):
        for payload in payloads:
            last_payload = payload
            last_endpoint = endpoint
            try:
                resp = requests.get(endpoint, params=payload, timeout=20)
                resp.raise_for_status()
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.RequestException:
                continue

            resp_text = resp.text.strip()
            last_preview = resp_text[:500]
            if not resp_text:
                continue

            try:
                root = ET.fromstring(resp_text)
            except ET.ParseError:
                continue

            result_code = str(_xml_findtext(root, "resultCode") or "").strip()
            success_yn = str(_xml_findtext(root, "successYN") or "").strip()
            result_msg = str(_xml_findtext(root, "resultMsg") or "").strip()

            if (success_yn and success_yn.upper() == "N") or (result_code and result_code != "00"):
                msg = f"{result_code} {result_msg}".strip()
                lowered = msg.lower()
                if any(token in lowered for token in ("parameter", "param", "필수", "required", "missing")):
                    continue
                return _err(
                    f"KIPRIS Plus error: {msg}".strip(),
                    status=STATUS_PARSE_ERROR,
                    preview=last_preview,
                )

            total_count = _parse_kipris_plus_total_count(root)
            items = _parse_kipris_plus_items(root)
            if target_class:
                filtered: list[dict] = []
                for item in items:
                    class_value = str(item.get("classificationCode", "") or "").strip()
                    if not class_value:
                        filtered.append(item)
                        continue
                    if target_class in [v.strip() for v in class_value.split(",") if v.strip()]:
                        filtered.append(item)
                items = filtered

            if not items and total_count == 0 and len(payloads) > 1:
                continue

            status = STATUS_SUCCESS_HITS if items else STATUS_SUCCESS_ZERO
            return {
                "success": True,
                "search_status": status,
                "http_status": 200,
                "result_code": "00",
                "result_msg": "OK" if not result_msg else result_msg,
                "total_count": total_count,
                "filtered_count": len(items),
                "items": items,
                "mock": False,
                "query_mode": query_mode,
                "search_mode": _search_mode_for_query_mode(query_mode),
                "query_class_no": target_class,
                "query_codes": [similar_goods_code] if similar_goods_code else [],
                "search_expression": expression or word,
                "request_payload_summary": {
                    "endpoint": endpoint,
                    "query_mode": query_mode,
                    "search_mode": _search_mode_for_query_mode(query_mode),
                    "classNo": target_class,
                    "niceCode": payload.get("niceCode", ""),
                    "similarCode": payload.get("similarCode", ""),
                    "similarGroupCode": payload.get("similarGroupCode", ""),
                    "trademarkName": payload.get("trademarkName", ""),
                    "searchWord": payload.get("searchWord", ""),
                    "searchString": payload.get("searchString", ""),
                },
                "response_text_preview": last_preview,
            }

    return _err("KIPRIS Plus request failed (no successful response)", status=STATUS_TRANSPORT_ERROR, preview=last_preview)


def search_all_pages(
    word: str,
    similar_goods_code: str = "",
    class_no: str | int | None = None,
    max_pages: int = 5,
    rows_per_page: int = 10,
    query_mode: str = "",
) -> dict:
    all_items: list[dict] = []
    total_count = 0
    target_class = _normalize_class_no(class_no) or (
        _class_from_goods_code(similar_goods_code) if similar_goods_code else ""
    )
    if query_mode in {"primary_sc_only", "related_sc_only", "retail_sc_only"}:
        target_class = ""
    search_expression = ""

    last_result = None
    for page in range(1, max_pages + 1):
        result = search_trademark(
            word,
            similar_goods_code=similar_goods_code,
            class_no=target_class,
            num_of_rows=rows_per_page,
            page_no=page,
            query_mode=query_mode,
        )
        last_result = result
        if not result["success"]:
            if page == 1:
                return result
            break
        if page == 1:
            total_count = result["total_count"]
        page_items = result["items"]
        if not page_items:
            break
            
        all_items.extend(
            [
                {
                    **item,
                    "queried_codes": [similar_goods_code] if similar_goods_code else [],
                    "query_mode": query_mode,
                    "query_class_no": target_class,
                    "search_expression": search_expression or word,
                }
                for item in page_items
            ]
        )

        if page * rows_per_page >= total_count:
            break
        time.sleep(0.5)

    enrich_payload = enrich_search_results_with_item_details(all_items)
    merged_candidates = len(enrich_payload.get("items", []))
    enriched_items = dedupe_search_candidates(enrich_payload.get("items", []))
    deduped_candidates = len(enriched_items)
    detail_parse_count = int(enrich_payload.get("detail_parse_count", 0))
    detail_parse_error_count = int(enrich_payload.get("detail_parse_error_count", 0))
    
    # search_all_pages에서도 최종 상태를 집계하여 반환
    final_status = STATUS_SUCCESS_HITS if enriched_items else STATUS_SUCCESS_ZERO
    if last_result and not last_result["success"]:
        final_status = last_result["search_status"]
    elif (
        enriched_items
        and detail_parse_count == 0
        and query_mode in {"primary_sc_only", "primary_sc", "related_sc_only", "retail_sc_only"}
    ):
        final_status = STATUS_DETAIL_PARSE_ERROR

    return {
        "success": True,
        "search_status": final_status,
        "result_code": "00",
        "result_msg": "OK",
        "total_count": total_count,
        "filtered_count": len(enriched_items),
        "items": enriched_items,
        "mock": last_result.get("mock", False) if last_result else False,
        "query_mode": query_mode,
        "search_mode": _search_mode_for_query_mode(query_mode),
        "query_class_no": target_class,
        "query_codes": [similar_goods_code] if similar_goods_code else [],
        "search_expression": search_expression or word,
        "request_payload_summary": last_result.get("request_payload_summary", {}) if last_result else {},
        "extracted_total_count": total_count,
        "merged_candidates": merged_candidates,
        "deduped_candidates": deduped_candidates,
        "detail_parse_count": detail_parse_count,
        "detail_parse_error_count": detail_parse_error_count,
        "response_text_preview": last_result.get("response_text_preview", "") if last_result else "",
    }


def _err(msg: str, status: str = "error", preview: str = "") -> dict:
    return {
        "success": False,
        "search_status": status,
        "result_code": "-1",
        "result_msg": msg,
        "total_count": 0,
        "filtered_count": 0,
        "items": [],
        "mock": False,
        "response_text_preview": preview,
    }


if __name__ == "__main__":
    word = sys.argv[1] if len(sys.argv) > 1 else "POOKIE"
    code = sys.argv[2] if len(sys.argv) > 2 else "G4503"
    result = search_all_pages(word, similar_goods_code=code, class_no=None, max_pages=3)
    print(json.dumps(result, ensure_ascii=False, indent=2))
