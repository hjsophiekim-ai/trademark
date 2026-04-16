"""상품유사군코드.xlsx 기준 유사군코드 자동 도출."""

from __future__ import annotations

import re
import zipfile
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
SIMILARITY_CODE_SOURCE_PATH = DOCS_DIR / "상품유사군코드.xlsx"

XML_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SALES_TERMS = ("도매", "소매", "판매", "판매대행", "판매알선", "중개업", "구매대행")
CONFIDENCE_RANK = {"exact": 4, "high": 3, "medium": 2, "fallback": 1}
CLASS_FALLBACK_CODES = {
    36: "S173699",
    37: "S173799",
    39: "S173999",
    40: "S174099",
    42: "S174299",
    43: "S174399",
    44: "S174499",
    45: "S174599",
}

MANUAL_CODE_METADATA: dict[str, dict] = {
    "S0201": {
        "class_no": 36,
        "name": "금융, 통화 및 은행업",
        "description": "예금접수업, 자금대부업, 내국환거래업, 증권업 등 금융 거래 서비스",
    },
    "S0301": {
        "class_no": 36,
        "name": "보험업",
        "description": "보험 인수, 보험 중개, 보험 관련 서비스",
    },
    "S120401": {
        "class_no": 36,
        "name": "재무가치평가업, 재무관리업, 재무상담업",
        "description": "재무평가, 재무관리, 재무상담, 재무자문 관련 서비스",
    },
    "S1212": {
        "class_no": 36,
        "name": "부동산 등 관리 · 임대 · 감정 관련 서비스업",
        "description": "부동산 중개, 관리, 감정, 임대 관련 서비스군",
    },
    "S121201": {
        "class_no": 36,
        "name": "부동산관리업, 부동산중개업",
        "description": "부동산 관리, 분양, 중개 관련 서비스",
    },
    "S121202": {
        "class_no": 36,
        "name": "부동산감정업, 부동산평가업",
        "description": "부동산 감정 및 평가 관련 서비스",
    },
    "S121203": {
        "class_no": 36,
        "name": "부동산임대업",
        "description": "부동산 임대 및 임차 관련 서비스",
    },
    "S123301": {
        "class_no": 42,
        "name": "컴퓨터시스템의 설계 및 자문업, 컴퓨터 소프트웨어의 자문 및 개발업",
        "description": "컴퓨터 시스템 설계, 소프트웨어 개발 및 자문 서비스",
    },
    "S173699": {
        "class_no": 36,
        "name": "제36류에 속하는 기타 서비스업",
        "description": "기부금모집조직업 등 제36류 기타 서비스업",
    },
    "S173799": {
        "class_no": 37,
        "name": "제37류에 속하는 기타 서비스업",
        "description": "제37류 기타 서비스업",
    },
    "S173999": {
        "class_no": 39,
        "name": "제39류에 속하는 기타 서비스업",
        "description": "제39류 기타 서비스업",
    },
    "S174099": {
        "class_no": 40,
        "name": "제40류에 속하는 기타 서비스업",
        "description": "제40류 기타 서비스업",
    },
    "S174299": {
        "class_no": 42,
        "name": "제42류에 속하는 기타 서비스업",
        "description": "제42류 기타 서비스업",
    },
    "S174399": {
        "class_no": 43,
        "name": "제43류에 속하는 기타 서비스업",
        "description": "제43류 기타 서비스업",
    },
    "S174499": {
        "class_no": 44,
        "name": "제44류에 속하는 기타 서비스업",
        "description": "제44류 기타 서비스업",
    },
    "S174599": {
        "class_no": 45,
        "name": "제45류에 속하는 기타 서비스업",
        "description": "제45류 기타 서비스업",
    },
    "S4101": {
        "class_no": 41,
        "name": "교육업",
        "description": "교육, 강의, 훈련 관련 서비스",
    },
    "S4301": {
        "class_no": 43,
        "name": "카페/음식점업",
        "description": "카페, 레스토랑, 음식 제공 서비스",
    },
    "G1201": {
        "class_no": 3,
        "name": "화장품",
        "description": "비의료용 화장품 및 세면용품",
    },
    "G1001": {
        "class_no": 3,
        "name": "가정용 탈지제, 세탁용 광택제, 탈색제",
        "description": "표백제 및 기타 세탁용 제제",
    },
    "G1202": {
        "class_no": 3,
        "name": "향",
        "description": "향, 향료, 향수 관련 상품",
    },
    "G2601": {
        "class_no": 20,
        "name": "가구, 비금속제 가구부속품",
        "description": "가정용/사무용/정원용 가구 및 비금속제 가구부속품",
    },
    "G390802": {
        "class_no": 9,
        "name": "소프트웨어",
        "description": "기록 및 내려받기 가능한 소프트웨어, 컴퓨터 프로그램",
    },
    "G390803": {
        "class_no": 9,
        "name": "컴퓨터, 전자관, 태블릿 컴퓨터",
        "description": "컴퓨터 및 컴퓨터주변기기",
    },
    "G4503": {
        "class_no": 25,
        "name": "의류",
        "description": "셔츠, 티셔츠, 바지 등 의류 상품",
    },
}

EXACT_LABEL_RULES = {
    (36, "금융, 통화 및 은행업"): {
        "primary": "S0201",
        "candidates": ["S0201", "S120401", "S173699"],
    },
    (36, "보험서비스업"): {
        "primary": "S0301",
        "candidates": ["S0301", "S173699"],
    },
    (36, "부동산업"): {
        "primary": "S1212",
        "candidates": ["S1212", "S121201", "S121202", "S121203", "S173699"],
    },
    (20, "가구, 거울, 액자"): {
        "primary": "G2601",
        "candidates": ["G2601"],
    },
    (3, "비의료용 화장품 및 세면용품"): {
        "primary": "G1201",
        "candidates": ["G1201", "G1202"],
    },
    (3, "표백제 및 기타 세탁용 제제"): {
        "primary": "G1001",
        "candidates": ["G1001", "G1201"],
    },
    (9, "기록 및 내려받기 가능한 멀티미디어 파일, 컴퓨터 소프트웨어, 빈 디지털 또는 아날로그 기록 및 저장매체"): {
        "primary": "G390802",
        "candidates": ["G390802"],
    },
    (9, "컴퓨터 및 컴퓨터주변기기"): {
        "primary": "G390803",
        "candidates": ["G390803", "G390802"],
    },
    (42, "컴퓨터 하드웨어 및 소프트웨어의 디자인 및 개발업"): {
        "primary": "S123301",
        "candidates": ["S123301", "S174299"],
    },
}

KEYWORD_RULES = (
    {
        "classes": {36},
        "keywords": ("금융", "통화", "은행", "환전", "외환", "대출", "예금", "증권", "신용카드", "atm", "가상자산", "가상화폐"),
        "primary": "S0201",
        "candidates": ["S0201", "S120401", "S173699"],
    },
    {
        "classes": {36},
        "keywords": ("보험",),
        "primary": "S0301",
        "candidates": ["S0301", "S173699"],
    },
    {
        "classes": {36},
        "keywords": ("재무평가", "재무가치평가", "재무관리", "재무상담", "재무자문", "재무설계", "financialconsultancy", "financialmanagement"),
        "primary": "S120401",
        "candidates": ["S120401", "S0201", "S173699"],
    },
    {
        "classes": {36},
        "keywords": ("부동산", "중개", "임대", "감정", "평가", "분양"),
        "primary": "S1212",
        "candidates": ["S1212", "S121201", "S121202", "S121203", "S173699"],
    },
    {
        "classes": {9},
        "keywords": ("소프트웨어", "프로그램", "애플리케이션", "응용프로그램", "멀티미디어파일"),
        "primary": "G390802",
        "candidates": ["G390802"],
    },
    {
        "classes": {9},
        "keywords": ("컴퓨터", "컴퓨터주변기기", "태블릿"),
        "primary": "G390803",
        "candidates": ["G390803", "G390802"],
    },
    {
        "classes": {20},
        "keywords": ("가구", "거울", "액자", "캐비닛", "의자", "선반", "정원용가구", "사무용가구"),
        "primary": "G2601",
        "candidates": ["G2601"],
    },
    {
        "classes": {3},
        "keywords": ("화장품", "세면용품", "비누", "미용", "방취제"),
        "primary": "G1201",
        "candidates": ["G1201", "G1202"],
    },
    {
        "classes": {3},
        "keywords": ("표백제", "세탁용", "탈색제"),
        "primary": "G1001",
        "candidates": ["G1001", "G1201"],
    },
    {
        "classes": {3},
        "keywords": ("향", "향수", "향료", "라벤더", "자스민", "장미유"),
        "primary": "G1202",
        "candidates": ["G1202", "G1201"],
    },
    {
        "classes": {25},
        "keywords": ("의류", "셔츠", "티셔츠", "팬츠", "모자", "신발"),
        "primary": "G4503",
        "candidates": ["G4503"],
    },
    {
        "classes": {41},
        "keywords": ("교육", "훈련", "강의", "학원", "이러닝"),
        "primary": "S4101",
        "candidates": ["S4101"],
    },
    {
        "classes": {42},
        "keywords": ("소프트웨어", "클라우드", "saas", "플랫폼", "개발업", "디자인및개발업"),
        "primary": "S123301",
        "candidates": ["S123301", "S174299"],
    },
    {
        "classes": {43},
        "keywords": ("카페", "레스토랑", "음식점", "숙박"),
        "primary": "S4301",
        "candidates": ["S4301", "S174399"],
    },
)


def dedupe_strings(values: Iterable[str]) -> list[str]:
    seen = set()
    items: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def dedupe_ints(values: Iterable[int | str]) -> list[int]:
    seen = set()
    items: list[int] = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number in seen:
            continue
        seen.add(number)
        items.append(number)
    return sorted(items)


def _normalize_display_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_match_text(value: object) -> str:
    text = _normalize_display_text(value)
    if not text:
        return ""
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^\w가-힣]", "", text.lower())
    for suffix in ("업", "서비스", "서비스업"):
        if text.endswith(suffix) and len(text) > len(suffix) + 1:
            text = text[: -len(suffix)]
    return text


def _score(source: str, target: str) -> float:
    left = _normalize_match_text(source)
    right = _normalize_match_text(target)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def _extract_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", XML_NS):
        fragments = [node.text or "" for node in item.findall(".//main:t", XML_NS)]
        values.append("".join(fragments))
    return values


def _column_name(cell_ref: str) -> str:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    return match.group(1) if match else ""


def _read_excel_rows(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _extract_shared_strings(archive)
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[dict[str, str]] = []
    for row in root.findall(".//main:sheetData/main:row", XML_NS):
        current: dict[str, str] = {}
        for cell in row.findall("main:c", XML_NS):
            ref = cell.attrib.get("r", "")
            column = _column_name(ref)
            cell_type = cell.attrib.get("t")
            value = ""
            if cell_type == "inlineStr":
                value = "".join(node.text or "" for node in cell.findall(".//main:t", XML_NS))
            else:
                node = cell.find("main:v", XML_NS)
                raw = node.text if node is not None else ""
                if cell_type == "s" and raw:
                    value = shared_strings[int(raw)]
                else:
                    value = raw or ""
            if column:
                current[column] = _normalize_display_text(value)
        rows.append(current)
    return rows


def _split_codes(value: object) -> list[str]:
    raw = re.split(r"[,/;|·\n]+", str(value or ""))
    return dedupe_strings(part.strip().upper() for part in raw if part.strip())


def _parse_class_number(value: object) -> int | None:
    digits = re.findall(r"\d+", str(value or ""))
    return int(digits[0]) if digits else None


def _format_class_no(class_no: int | None) -> str:
    return f"제{class_no}류" if class_no else ""


def _is_sales_code(code: str, labels: Iterable[str]) -> bool:
    if code.startswith("S20"):
        return True
    haystack = " ".join(labels)
    return any(term in haystack for term in SALES_TERMS)


@lru_cache(maxsize=1)
def load_similarity_source_rows() -> list[dict]:
    rows = _read_excel_rows(SIMILARITY_CODE_SOURCE_PATH)
    parsed_rows: list[dict] = []
    for row in rows[1:]:
        label = _normalize_display_text(row.get("B", ""))
        class_no = _parse_class_number(row.get("C", ""))
        codes = _split_codes(row.get("D", ""))
        if not label or class_no is None or not codes:
            continue
        parsed_rows.append(
            {
                "label": label,
                "class_no": class_no,
                "codes": codes,
                "normalized_label": _normalize_match_text(label),
            }
        )
    return parsed_rows


@lru_cache(maxsize=1)
def load_similarity_code_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for row in load_similarity_source_rows():
        for code in row["codes"]:
            payload = catalog.setdefault(
                code,
                {
                    "code": code,
                    "class_no": None,
                    "name": "",
                    "description": "",
                    "examples": [],
                    "row_classes": [],
                    "is_sales": False,
                },
            )
            payload["examples"] = dedupe_strings([*payload["examples"], row["label"]])
            payload["row_classes"] = dedupe_ints([*payload["row_classes"], row["class_no"]])
            payload["is_sales"] = payload["is_sales"] or _is_sales_code(code, [row["label"]])

    for code, payload in catalog.items():
        override = MANUAL_CODE_METADATA.get(code, {})
        payload["class_no"] = override.get("class_no") or (
            payload["row_classes"][0] if len(payload["row_classes"]) == 1 else None
        )
        payload["name"] = override.get("name") or (payload["examples"][0] if payload["examples"] else code)
        payload["description"] = override.get("description") or ", ".join(payload["examples"][:4])
        payload["recommended"] = not payload["is_sales"]
        payload["class_no_text"] = _format_class_no(payload["class_no"])
    return catalog


@lru_cache(maxsize=1)
def _build_exact_label_index() -> dict[tuple[int, str], list[str]]:
    index: dict[tuple[int, str], list[str]] = {}
    for row in load_similarity_source_rows():
        key = (row["class_no"], row["normalized_label"])
        index[key] = dedupe_strings([*index.get(key, []), *row["codes"]])
    return index


def _candidate_from_code(
    code: str,
    *,
    reason: str,
    confidence: str,
    score: float,
    matched_text: str = "",
    fallback_used: bool = False,
    selected: bool = False,
) -> dict:
    metadata = load_similarity_code_catalog().get(code, {"code": code})
    class_no = metadata.get("class_no")
    return {
        "code": code,
        "name": metadata.get("name", code),
        "description": metadata.get("description", ""),
        "examples": list(metadata.get("examples", [])),
        "recommended": bool(metadata.get("recommended", True)),
        "is_sales": bool(metadata.get("is_sales", False)),
        "class_no": metadata.get("class_no_text") or _format_class_no(class_no),
        "class_number": class_no,
        "match_score": round(score, 3),
        "match_reason": reason,
        "match_confidence": confidence,
        "matched_text": matched_text,
        "fallback_used": fallback_used,
        "selected": selected,
    }


def _store_candidate(store: dict[str, dict], candidate: dict) -> None:
    current = store.get(candidate["code"])
    if current is None:
        store[candidate["code"]] = candidate
        return
    current_rank = (
        bool(current.get("selected")),
        CONFIDENCE_RANK.get(current.get("match_confidence", "fallback"), 0),
        float(current.get("match_score", 0.0)),
    )
    next_rank = (
        bool(candidate.get("selected")),
        CONFIDENCE_RANK.get(candidate.get("match_confidence", "fallback"), 0),
        float(candidate.get("match_score", 0.0)),
    )
    if next_rank > current_rank:
        store[candidate["code"]] = candidate


def _normalize_classes(seed_classes: Iterable[int | str] | None, class_no: str | int | None = None) -> list[int]:
    classes = dedupe_ints(seed_classes or [])
    if classes:
        return classes
    parsed = _parse_class_number(class_no)
    return [parsed] if parsed else []


def _class_matches(code: str, selected_classes: list[int]) -> bool:
    if not selected_classes:
        return True
    metadata = load_similarity_code_catalog().get(code, {})
    class_no = metadata.get("class_no")
    if class_no is None:
        return True
    return int(class_no) in selected_classes


def _apply_exact_rule(store: dict[str, dict], label: str, selected_classes: list[int]) -> bool:
    matched = False
    for class_no in selected_classes or [None]:
        rule = EXACT_LABEL_RULES.get((class_no, label)) if class_no is not None else None
        if not rule:
            continue
        for index, code in enumerate(rule["candidates"]):
            _store_candidate(
                store,
                _candidate_from_code(
                    code,
                    reason="exact_label_match",
                    confidence="exact",
                    score=1.0 - index * 0.01,
                    matched_text=label,
                    selected=code == rule["primary"],
                ),
            )
            matched = True
    return matched


def _apply_exact_xlsx_match(store: dict[str, dict], label: str, selected_classes: list[int]) -> bool:
    normalized = _normalize_match_text(label)
    matched = False
    for class_no in selected_classes or []:
        codes = _build_exact_label_index().get((class_no, normalized), [])
        if not codes:
            continue
        chosen = None
        if class_no <= 34:
            chosen = next((code for code in codes if code.startswith("G")), codes[0])
        else:
            chosen = next((code for code in codes if code.startswith("S")), codes[0])
        for index, code in enumerate(codes):
            _store_candidate(
                store,
                _candidate_from_code(
                    code,
                    reason="exact_label_match",
                    confidence="exact",
                    score=0.99 - index * 0.01,
                    matched_text=label,
                    selected=code == chosen,
                ),
            )
            matched = True
    return matched


def _apply_semantic_match(store: dict[str, dict], label: str, selected_classes: list[int]) -> bool:
    matched = False
    normalized_label = _normalize_match_text(label)
    if not normalized_label:
        return False
    for row in load_similarity_source_rows():
        if selected_classes and row["class_no"] not in selected_classes:
            continue
        score = _score(label, row["label"])
        if score < 0.72:
            continue
        chosen = None
        if row["class_no"] <= 34:
            chosen = next((code for code in row["codes"] if code.startswith("G")), row["codes"][0])
        else:
            chosen = next((code for code in row["codes"] if code.startswith("S")), row["codes"][0])
        confidence = "high" if score >= 0.9 else "medium"
        for code in row["codes"]:
            if selected_classes and not _class_matches(code, selected_classes):
                metadata = load_similarity_code_catalog().get(code, {})
                if metadata.get("is_sales"):
                    continue
            _store_candidate(
                store,
                _candidate_from_code(
                    code,
                    reason="normalized_semantic_match",
                    confidence=confidence,
                    score=score,
                    matched_text=row["label"],
                    selected=code == chosen,
                ),
            )
            matched = True
    return matched


def _apply_keyword_rule(
    store: dict[str, dict],
    texts: Iterable[str],
    selected_classes: list[int],
    *,
    base_score: float,
    confidence: str,
) -> bool:
    normalized_text = " ".join(_normalize_match_text(text) for text in texts if _normalize_match_text(text))
    matched = False
    for rule in KEYWORD_RULES:
        if selected_classes and not (set(selected_classes) & set(rule["classes"])):
            continue
        if not any(keyword in normalized_text for keyword in rule["keywords"]):
            continue
        for index, code in enumerate(rule["candidates"]):
            _store_candidate(
                store,
                _candidate_from_code(
                    code,
                    reason="keyword_dictionary_match",
                    confidence=confidence,
                    score=base_score - index * 0.01,
                    matched_text=rule["primary"],
                    selected=code == rule["primary"],
                ),
            )
        matched = True
    return matched


def _apply_same_class_fallback(store: dict[str, dict], selected_classes: list[int]) -> bool:
    matched = False
    for class_no in selected_classes:
        fallback_code = CLASS_FALLBACK_CODES.get(class_no)
        if not fallback_code:
            continue
        _store_candidate(
            store,
            _candidate_from_code(
                fallback_code,
                reason="same_class_fallback",
                confidence="fallback",
                score=0.4,
                matched_text=_format_class_no(class_no),
                fallback_used=True,
                selected=True,
            ),
        )
        matched = True
    return matched


def _sorted_candidates(store: dict[str, dict]) -> list[dict]:
    return sorted(
        store.values(),
        key=lambda item: (
            not item.get("selected", False),
            -CONFIDENCE_RANK.get(item.get("match_confidence", "fallback"), 0),
            -float(item.get("match_score", 0.0)),
            item.get("is_sales", False),
            item["code"],
        ),
    )


def derive_similarity_mapping(
    product_name: str,
    *,
    class_no: str | int | None = None,
    seed_classes: Iterable[int | str] | None = None,
    seed_keywords: Iterable[str] | None = None,
    seed_codes: Iterable[str] | None = None,
    limit: int = 8,
) -> dict:
    selected_classes = _normalize_classes(seed_classes, class_no)
    keywords = dedupe_strings(seed_keywords or [])
    store: dict[str, dict] = {}
    label = _normalize_display_text(product_name)
    matched = False

    if label:
        matched = _apply_exact_rule(store, label, selected_classes) or matched
        matched = _apply_exact_xlsx_match(store, label, selected_classes) or matched
        matched = _apply_semantic_match(store, label, selected_classes) or matched

    if label:
        matched = _apply_keyword_rule(
            store,
            [label],
            selected_classes,
            base_score=0.97,
            confidence="high",
        ) or matched
    if keywords:
        matched = _apply_keyword_rule(
            store,
            keywords,
            selected_classes,
            base_score=0.9,
            confidence="medium",
        ) or matched

    for code in dedupe_strings(seed_codes or []):
        if selected_classes and not _class_matches(code, selected_classes):
            continue
        _store_candidate(
            store,
            _candidate_from_code(
                code,
                reason="seed_code",
                confidence="high",
                score=0.88,
                matched_text=label,
                selected=False,
            ),
        )

    if not matched:
        _apply_same_class_fallback(store, selected_classes)

    candidates = _sorted_candidates(store)[:limit]
    if candidates:
        normalized_candidates = []
        for index, row in enumerate(candidates):
            normalized_row = dict(row)
            normalized_row["selected"] = index == 0
            normalized_candidates.append(normalized_row)
        candidates = normalized_candidates
    chosen_row = candidates[0] if candidates else None
    chosen_codes = [chosen_row["code"]] if chosen_row else []
    return {
        "candidate_rows": candidates,
        "candidate_codes": dedupe_strings(row["code"] for row in candidates),
        "chosen_codes": dedupe_strings(chosen_codes),
        "match_reason": chosen_row.get("match_reason", "same_class_fallback") if chosen_row else "same_class_fallback",
        "match_confidence": chosen_row.get("match_confidence", "fallback") if chosen_row else "fallback",
        "fallback_used": bool(chosen_row.get("fallback_used", False)) if chosen_row else bool(selected_classes),
    }


def get_similarity_codes(
    product_name: str,
    class_no: str | None = None,
    limit: int = 8,
    seed_classes: Iterable[int | str] | None = None,
    seed_keywords: Iterable[str] | None = None,
    seed_codes: Iterable[str] | None = None,
) -> list[dict]:
    mapping = derive_similarity_mapping(
        product_name,
        class_no=class_no,
        seed_classes=seed_classes,
        seed_keywords=seed_keywords,
        seed_codes=seed_codes,
        limit=limit,
    )
    return list(mapping["candidate_rows"])


def get_code_metadata(code: str) -> dict | None:
    row = load_similarity_code_catalog().get(str(code or "").strip().upper())
    if not row:
        return None
    return {
        "code": row["code"],
        "name": row["name"],
        "description": row["description"],
        "examples": list(row.get("examples", [])),
        "recommended": bool(row.get("recommended", True)),
        "is_sales": bool(row.get("is_sales", False)),
        "class_no": row.get("class_no_text", ""),
    }


def get_class_for_code(code: str) -> str | None:
    row = load_similarity_code_catalog().get(str(code or "").strip().upper())
    if not row:
        return None
    return row.get("class_no_text") or None


def get_all_codes_by_class(class_no: str | int) -> list[dict]:
    target_class = _parse_class_number(class_no)
    if target_class is None:
        return []
    rows: list[dict] = []
    seen = set()
    for source_row in load_similarity_source_rows():
        if source_row["class_no"] != target_class:
            continue
        for code in source_row["codes"]:
            if code in seen:
                continue
            seen.add(code)
            metadata = get_code_metadata(code) or {"code": code, "name": code, "description": ""}
            rows.append(
                {
                    **metadata,
                    "class_no": _format_class_no(target_class),
                }
            )
    rows.sort(key=lambda item: (item["code"], item["name"]))
    return rows


def suggest_similarity_codes(product_name: str, limit: int = 6) -> list[dict]:
    return get_similarity_codes(product_name, limit=limit)
