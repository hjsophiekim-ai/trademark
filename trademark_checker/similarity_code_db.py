"""니스분류 선택값을 우선 반영하는 유사군코드 추천."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from nice_catalog import dedupe_ints, dedupe_strings, flatten_subgroups


SIMILARITY_CODE_DB: dict[str, list[dict]] = {
    "의류": [
        {"code": "G4503", "name": "의류", "description": "의류 기본 분류", "recommended": True, "class_no": "제25류"},
        {"code": "G450101", "name": "의류(일반)", "description": "일반 의류 전반", "recommended": True, "class_no": "제25류"},
        {"code": "S2045", "name": "특정상품 판매업", "description": "의류 판매업", "recommended": True, "is_sales": True, "class_no": "제35류"},
        {"code": "S2027", "name": "의류 판매업", "description": "의류 판매 및 쇼핑몰", "recommended": True, "is_sales": True, "class_no": "제35류"},
    ],
    "화장품": [
        {"code": "G1201", "name": "화장품류", "description": "기초화장품, 메이크업, 화장품", "recommended": True, "class_no": "제3류"},
        {"code": "G1202", "name": "향료류", "description": "향수, 방향제", "recommended": False, "class_no": "제3류"},
        {"code": "S120907", "name": "화장품 판매업", "description": "화장품 유통 및 판매", "recommended": True, "is_sales": True, "class_no": "제35류"},
    ],
    "가구": [
        {"code": "G2001", "name": "가구류", "description": "소파, 침대, 일반 가구", "recommended": True, "class_no": "제20류"},
        {"code": "G2002", "name": "사무용가구", "description": "책상, 의자, 캐비닛", "recommended": True, "class_no": "제20류"},
        {"code": "S2021", "name": "가구 판매업", "description": "가구 판매 및 쇼핑몰", "recommended": True, "is_sales": True, "class_no": "제35류"},
    ],
    "소프트웨어": [
        {"code": "G390802", "name": "소프트웨어", "description": "다운로드 가능한 소프트웨어, 응용프로그램", "recommended": True, "class_no": "제9류"},
        {"code": "G0901", "name": "컴퓨터 소프트웨어", "description": "컴퓨터 프로그램, AI 소프트웨어", "recommended": True, "class_no": "제9류"},
        {"code": "G0903", "name": "모바일 애플리케이션", "description": "모바일 앱, 애플리케이션", "recommended": True, "class_no": "제9류"},
    ],
    "소프트웨어서비스": [
        {"code": "S420201", "name": "소프트웨어 서비스업", "description": "SaaS, 클라우드, 호스팅", "recommended": True, "class_no": "제42류"},
        {"code": "S420202", "name": "플랫폼 서비스업", "description": "온라인 플랫폼, API 제공", "recommended": True, "class_no": "제42류"},
        {"code": "S380102", "name": "통신 플랫폼 서비스업", "description": "메시징, 통신 기반 플랫폼", "recommended": False, "class_no": "제38류"},
        {"code": "S350601", "name": "온라인 플랫폼 판매중개업", "description": "앱마켓, 플랫폼 판매중개", "recommended": False, "class_no": "제35류"},
    ],
    "카페": [
        {"code": "S4301", "name": "카페/음식점업", "description": "카페, 음식점, 음료 제공", "recommended": True, "is_sales": True, "class_no": "제43류"},
        {"code": "G3001", "name": "커피/차류", "description": "커피, 원두, 차류", "recommended": False, "class_no": "제30류"},
    ],
    "커피": [
        {"code": "G3001", "name": "커피/차류", "description": "커피, 차, 로스팅 원두", "recommended": True, "class_no": "제30류"},
        {"code": "S4301", "name": "카페/음식점업", "description": "카페, 커피전문점 운영", "recommended": True, "is_sales": True, "class_no": "제43류"},
    ],
    "교육": [
        {"code": "S4101", "name": "교육서비스업", "description": "교육, 강의, 훈련", "recommended": True, "class_no": "제41류"},
        {"code": "S4104", "name": "온라인 교육 플랫폼업", "description": "교육 플랫폼, 이러닝", "recommended": True, "class_no": "제41류"},
        {"code": "S420202", "name": "플랫폼 서비스업", "description": "교육용 플랫폼 제공", "recommended": False, "class_no": "제42류"},
    ],
}

ALIASES = {
    "쇼핑몰": "의류",
    "온라인몰": "의류",
    "saas": "소프트웨어서비스",
    "app": "소프트웨어",
    "앱": "소프트웨어",
    "뷰티": "화장품",
    "레스토랑": "카페",
    "카페브랜드": "카페",
    "가구점": "가구",
}

CODE_METADATA = {
    row["code"]: {**row, "base_keyword": keyword}
    for keyword, rows in SIMILARITY_CODE_DB.items()
    for row in rows
}


def _normalize(text: str) -> str:
    return str(text or "").strip().lower().replace(" ", "")


def _score(source: str, target: str) -> float:
    left = _normalize(source)
    right = _normalize(target)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.9
    return SequenceMatcher(None, left, right).ratio()


def _normalize_class_list(values: Iterable[int | str] | None) -> list[int]:
    return dedupe_ints(values or [])


def _format_class_no(value: int | str) -> str:
    return f"제{int(value)}류"


def _matches_class(row: dict, seed_classes: list[int]) -> bool:
    if not seed_classes:
        return True
    digits = "".join(ch for ch in str(row.get("class_no", "")) if ch.isdigit())
    if not digits:
        return False
    return int(digits) in seed_classes


def _candidate_from_code(code: str) -> dict:
    row = CODE_METADATA.get(code)
    if row:
        return row.copy()
    digits = "".join(ch for ch in code if ch.isdigit())
    class_no = _format_class_no(digits or 0) if digits else ""
    return {
        "code": code,
        "name": code,
        "description": "선택 상품군 기준으로 추천된 유사군코드",
        "recommended": True,
        "class_no": class_no,
        "base_keyword": "catalog_seed",
    }


def _seeded_codes(seed_codes: Iterable[str], seed_classes: list[int]) -> list[dict]:
    rows: list[dict] = []
    for code in dedupe_strings(seed_codes):
        candidate = _candidate_from_code(code)
        if _matches_class(candidate, seed_classes):
            candidate["match_score"] = 1.0
            candidate["seed_source"] = "selected_subgroup"
            rows.append(candidate)
    return rows


def _seeded_keyword_codes(seed_keywords: Iterable[str], seed_classes: list[int]) -> list[dict]:
    if not seed_keywords:
        return []

    normalized_seed_keywords = {_normalize(keyword) for keyword in seed_keywords}
    rows: list[dict] = []

    for subgroup in flatten_subgroups():
        subgroup_classes = _normalize_class_list(subgroup.get("nice_classes", []))
        if seed_classes and not set(subgroup_classes) & set(seed_classes):
            continue
        keyword_pool = {_normalize(keyword) for keyword in subgroup.get("keywords", [])}
        if not keyword_pool & normalized_seed_keywords:
            continue
        for code in subgroup.get("similarity_codes", []):
            candidate = _candidate_from_code(code)
            candidate["match_score"] = max(candidate.get("match_score", 0.0), 0.98)
            candidate["seed_source"] = "selected_keywords"
            rows.append(candidate)

    for keyword in normalized_seed_keywords:
        alias_target = ALIASES.get(keyword, keyword)
        for base_keyword, candidate_rows in SIMILARITY_CODE_DB.items():
            if max(_score(keyword, base_keyword), _score(alias_target, base_keyword)) < 0.45:
                continue
            for row in candidate_rows:
                if not _matches_class(row, seed_classes) and not row.get("is_sales"):
                    continue
                rows.append({**row, "match_score": 0.9, "seed_source": "selected_keywords"})

    return rows


def _search_codes(product_name: str, seed_classes: list[int]) -> list[dict]:
    if not product_name.strip():
        return []

    alias_target = ALIASES.get(_normalize(product_name), product_name)
    matches: list[dict] = []
    for keyword, rows in SIMILARITY_CODE_DB.items():
        match_score = max(_score(product_name, keyword), _score(alias_target, keyword))
        if match_score < 0.35:
            continue
        for row in rows:
            if not _matches_class(row, seed_classes) and not row.get("is_sales"):
                continue
            matches.append({**row, "match_score": round(match_score, 3)})
    return matches


def _dedupe_candidates(rows: Iterable[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for row in rows:
        current = deduped.get(row["code"])
        if current is None or row.get("match_score", 0.0) > current.get("match_score", 0.0):
            deduped[row["code"]] = row
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            item.get("seed_source") not in {"selected_subgroup", "selected_keywords"},
            not item.get("recommended", False),
            item.get("is_sales", False),
            -float(item.get("match_score", 0.0)),
            item["code"],
        ),
    )
    return ordered


def get_similarity_codes(
    product_name: str,
    class_no: str | None = None,
    limit: int = 8,
    seed_classes: Iterable[int | str] | None = None,
    seed_keywords: Iterable[str] | None = None,
    seed_codes: Iterable[str] | None = None,
) -> list[dict]:
    selected_classes = _normalize_class_list(seed_classes)
    if not selected_classes and class_no:
        digits = "".join(ch for ch in str(class_no) if ch.isdigit())
        if digits:
            selected_classes = [int(digits)]

    rows = []
    rows.extend(_seeded_codes(seed_codes or [], selected_classes))
    rows.extend(_seeded_keyword_codes(seed_keywords or [], selected_classes))
    rows.extend(_search_codes(product_name, selected_classes))
    return _dedupe_candidates(rows)[:limit]


def get_code_metadata(code: str) -> dict | None:
    row = CODE_METADATA.get(code)
    return row.copy() if row else None


def get_class_for_code(code: str) -> str | None:
    row = CODE_METADATA.get(code)
    return row.get("class_no") if row else None


def get_all_codes_by_class(class_no: str | int) -> list[dict]:
    digits = "".join(ch for ch in str(class_no) if ch.isdigit())
    target = _format_class_no(digits) if digits else str(class_no)
    rows = []
    seen = set()
    for items in SIMILARITY_CODE_DB.values():
        for row in items:
            if row.get("class_no") != target:
                continue
            if row["code"] in seen:
                continue
            seen.add(row["code"])
            rows.append(row.copy())
    rows.sort(key=lambda item: (item["code"], item["name"]))
    return rows


def suggest_similarity_codes(product_name: str, limit: int = 6) -> list[dict]:
    return get_similarity_codes(product_name, limit=limit)
