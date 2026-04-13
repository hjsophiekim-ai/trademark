"""상품명으로 유사군 코드를 추천한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List


SIMILARITY_CODE_DB: Dict[str, List[dict]] = {
    "티셔츠": [
        {"code": "G4503", "name": "양말류", "description": "티셔츠, 양말 등 기본의류", "recommended": True},
        {"code": "G450101", "name": "의류(일반)", "description": "일반 의류 전체", "recommended": True},
        {"code": "S2045", "name": "속옷 소매업", "description": "의류 판매업", "recommended": True, "is_sales": True},
        {"code": "S2027", "name": "의류 소매업", "description": "의류 판매점/쇼핑몰", "recommended": True, "is_sales": True},
    ],
    "바지": [
        {"code": "G450101", "name": "의류(일반)", "description": "바지, 청바지 등", "recommended": True},
        {"code": "G4503", "name": "양말류", "description": "기본 의류", "recommended": False},
        {"code": "S2027", "name": "의류 소매업", "description": "의류 판매업", "recommended": True, "is_sales": True},
    ],
    "운동화": [
        {"code": "G450601", "name": "신발류", "description": "운동화, 스니커즈", "recommended": True},
        {"code": "G270101", "name": "신발(일반)", "description": "일반 신발류", "recommended": True},
        {"code": "S2027", "name": "신발 소매업", "description": "신발 판매점", "recommended": True, "is_sales": True},
    ],
    "책상": [
        {"code": "G2001", "name": "가구류", "description": "책상, 테이블, 가구 전반", "recommended": True},
        {"code": "G2002", "name": "사무용가구", "description": "사무용 책상, 의자", "recommended": True},
        {"code": "S2021", "name": "가구 소매업", "description": "가구 판매점/쇼핑몰", "recommended": True, "is_sales": True},
    ],
    "소파": [
        {"code": "G2001", "name": "가구류", "description": "소파, 쇼파, 가구", "recommended": True},
        {"code": "S2021", "name": "가구 소매업", "description": "가구 판매업", "recommended": True, "is_sales": True},
    ],
    "화장품": [
        {"code": "G1201", "name": "화장품류", "description": "스킨케어, 색조화장품", "recommended": True},
        {"code": "G1202", "name": "향수류", "description": "향수, 방향제", "recommended": False},
        {"code": "S120907", "name": "화장품 소매업", "description": "화장품 판매점", "recommended": True, "is_sales": True},
    ],
    "스킨케어": [
        {"code": "G1201", "name": "화장품류", "description": "스킨, 로션, 크림 등 기초화장품", "recommended": True},
        {"code": "S120907", "name": "화장품 소매업", "description": "화장품 판매점", "recommended": True, "is_sales": True},
    ],
    "반지": [
        {"code": "G3002", "name": "귀금속류", "description": "반지, 목걸이, 귀걸이", "recommended": True},
        {"code": "G4509", "name": "귀걸이류", "description": "귀걸이 전용", "recommended": False},
        {"code": "S2030", "name": "귀금속 소매업", "description": "귀금속 판매점", "recommended": True, "is_sales": True},
    ],
    "앱": [
        {"code": "G0901", "name": "컴퓨터소프트웨어", "description": "앱, 프로그램, 소프트웨어", "recommended": True},
        {"code": "G0903", "name": "스마트폰앱", "description": "모바일 애플리케이션", "recommended": True},
    ],
    "커피": [
        {"code": "G3001", "name": "커피/차류", "description": "커피원두, 인스턴트커피", "recommended": True},
        {"code": "S4301", "name": "카페/음식점업", "description": "카페, 커피숍 운영", "recommended": True, "is_sales": True},
    ],
    "카페": [
        {"code": "S4301", "name": "카페/음식점업", "description": "카페, 커피숍 운영", "recommended": True, "is_sales": True},
        {"code": "G3001", "name": "커피/차류", "description": "커피 상품도 함께 보호 가능", "recommended": False},
    ],
}

ALIASES = {
    "쇼파": "소파",
    "책장": "책상",
    "테이블": "책상",
    "스킨": "스킨케어",
    "앱개발": "앱",
    "커피숍": "카페",
    "음식점": "카페",
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


def suggest_similarity_codes(product_name: str, limit: int = 6) -> List[dict]:
    """입력 상품명과 가장 가까운 유사군 코드를 추천한다."""
    if not product_name.strip():
        return []

    normalized = _normalize(product_name)
    alias_target = ALIASES.get(normalized, product_name)
    matches: List[dict] = []

    for keyword, codes in SIMILARITY_CODE_DB.items():
        match_score = max(_score(product_name, keyword), _score(alias_target, keyword))
        if match_score < 0.35:
            continue
        for code in codes:
            matches.append({"base_product": keyword, "match_score": round(match_score, 3), **code})

    deduped = {}
    for item in matches:
        current = deduped.get(item["code"])
        if current is None or item["match_score"] > current["match_score"]:
            deduped[item["code"]] = item

    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            not item.get("recommended", False),
            item.get("is_sales", False),
            -item["match_score"],
            item["code"],
        ),
    )
    return ordered[:limit]
