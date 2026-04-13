"""상품명과 류 기준으로 유사군 코드를 추천한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List


SIMILARITY_CODE_DB: Dict[str, List[dict]] = {
    "티셔츠": [
        {"code": "G4503", "name": "양말류", "설명": "티셔츠, 양말 등 기본의류", "추천": True, "류": "25류"},
        {"code": "G450101", "name": "의류(일반)", "설명": "일반 의류 전체", "추천": True, "류": "25류"},
        {"code": "S2045", "name": "속옷 소매업", "설명": "의류 판매업", "추천": True, "판매업": True, "류": "35류"},
        {"code": "S2027", "name": "의류 소매업", "설명": "의류 판매점/쇼핑몰", "추천": True, "판매업": True, "류": "35류"},
    ],
    "바지": [
        {"code": "G450101", "name": "의류(일반)", "설명": "바지, 청바지 등", "추천": True, "류": "25류"},
        {"code": "G4503", "name": "양말류", "설명": "기본 의류", "추천": False, "류": "25류"},
        {"code": "S2027", "name": "의류 소매업", "설명": "의류 판매업", "추천": True, "판매업": True, "류": "35류"},
    ],
    "운동화": [
        {"code": "G450601", "name": "신발류", "설명": "운동화, 스니커즈", "추천": True, "류": "25류"},
        {"code": "G270101", "name": "신발(일반)", "설명": "일반 신발류", "추천": True, "류": "25류"},
        {"code": "S2027", "name": "신발 소매업", "설명": "신발 판매점", "추천": True, "판매업": True, "류": "35류"},
    ],
    "책상": [
        {"code": "G2001", "name": "가구류", "설명": "책상, 테이블, 가구 전반", "추천": True, "류": "20류"},
        {"code": "G2002", "name": "사무용가구", "설명": "사무용 책상, 의자", "추천": True, "류": "20류"},
        {"code": "S2021", "name": "가구 소매업", "설명": "가구 판매점/쇼핑몰", "추천": True, "판매업": True, "류": "35류"},
    ],
    "소파": [
        {"code": "G2001", "name": "가구류", "설명": "소파, 쇼파, 가구", "추천": True, "류": "20류"},
        {"code": "S2021", "name": "가구 소매업", "설명": "가구 판매업", "추천": True, "판매업": True, "류": "35류"},
    ],
    "화장품": [
        {"code": "G1201", "name": "화장품류", "설명": "스킨케어, 색조화장품", "추천": True, "류": "3류"},
        {"code": "G1202", "name": "향수류", "설명": "향수, 방향제", "추천": False, "류": "3류"},
        {"code": "S120907", "name": "화장품 소매업", "설명": "화장품 판매점", "추천": True, "판매업": True, "류": "35류"},
    ],
    "스킨케어": [
        {"code": "G1201", "name": "화장품류", "설명": "스킨, 로션, 크림 등 기초화장품", "추천": True, "류": "3류"},
        {"code": "S120907", "name": "화장품 소매업", "설명": "화장품 판매점", "추천": True, "판매업": True, "류": "35류"},
    ],
    "앱": [
        {"code": "G0901", "name": "컴퓨터소프트웨어", "설명": "앱, 프로그램, 소프트웨어", "추천": True, "류": "9류"},
        {"code": "G0903", "name": "스마트폰앱", "설명": "모바일 애플리케이션", "추천": True, "류": "9류"},
    ],
    "커피": [
        {"code": "G3001", "name": "커피/차류", "설명": "커피원두, 인스턴트커피", "추천": True, "류": "30류"},
        {"code": "S4301", "name": "카페/음식점업", "설명": "카페, 커피숍 운영", "추천": True, "판매업": True, "류": "43류"},
    ],
    "카페": [
        {"code": "S4301", "name": "카페/음식점업", "설명": "카페, 커피숍 운영", "추천": True, "판매업": True, "류": "43류"},
        {"code": "G3001", "name": "커피/차류", "설명": "커피 상품도 함께 보호 가능", "추천": False, "류": "30류"},
    ],
}

ALIASES = {
    "쇼파": "소파",
    "테이블": "책상",
    "책장": "책상",
    "스킨": "스킨케어",
    "앱개발": "앱",
    "커피숍": "카페",
    "식당": "카페",
}

CODE_METADATA = {
    row["code"]: {**row, "기준상품": keyword}
    for keyword, rows in SIMILARITY_CODE_DB.items()
    for row in rows
}


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def _score(source: str, target: str) -> float:
    left = _normalize(source)
    right = _normalize(target)
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.9
    return SequenceMatcher(None, left, right).ratio()


def _matches_class(row: dict, class_no: str | None) -> bool:
    if not class_no:
        return True
    return row.get("류") == class_no


def get_similarity_codes(product_name: str, class_no: str | None = None, limit: int = 8) -> List[dict]:
    """입력 상품명과 선택 류에 맞는 유사군 코드를 반환한다."""
    if not product_name.strip():
        return []

    alias_target = ALIASES.get(_normalize(product_name), product_name)
    matches: List[dict] = []

    for keyword, rows in SIMILARITY_CODE_DB.items():
        match_score = max(_score(product_name, keyword), _score(alias_target, keyword))
        if match_score < 0.35:
            continue
        for row in rows:
            if not _matches_class(row, class_no):
                if not row.get("판매업"):
                    continue
            matches.append({**row, "기준상품": keyword, "매칭점수": round(match_score, 3)})

    deduped = {}
    for row in matches:
        current = deduped.get(row["code"])
        if current is None or row["매칭점수"] > current["매칭점수"]:
            deduped[row["code"]] = row

    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            not item.get("추천", False),
            item.get("판매업", False),
            -item["매칭점수"],
            item["code"],
        ),
    )
    return ordered[:limit]


def get_code_metadata(code: str) -> dict | None:
    """유사군코드 메타데이터를 반환한다."""
    row = CODE_METADATA.get(code)
    return row.copy() if row else None


def get_class_for_code(code: str) -> str | None:
    """유사군코드에 연결된 류를 반환한다."""
    row = CODE_METADATA.get(code)
    return row.get("류") if row else None


def get_all_codes_by_class(class_no: str) -> List[dict]:
    """선택한 류에서 직접 고를 수 있는 전체 유사군 코드를 반환한다."""
    rows = []
    seen = set()
    for items in SIMILARITY_CODE_DB.values():
        for row in items:
            if row.get("류") != class_no:
                continue
            if row["code"] in seen:
                continue
            seen.add(row["code"])
            rows.append(row.copy())

    rows.sort(key=lambda item: (item["code"], item["name"]))
    return rows


def suggest_similarity_codes(product_name: str, limit: int = 6) -> List[dict]:
    """기존 호환용 영문 키 결과."""
    return [
        {
            "code": row["code"],
            "name": row["name"],
            "description": row["설명"],
            "recommended": row.get("추천", False),
            "is_sales": row.get("판매업", False),
            "base_product": row["기준상품"],
            "match_score": row["매칭점수"],
        }
        for row in get_similarity_codes(product_name, limit=limit)
    ]
