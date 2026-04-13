"""상품명에서 유사군 코드를 추천한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List

SIMILARITY_CODE_DB: Dict[str, List[dict]] = {
    "티셔츠": [
        {"code": "G4503", "name": "양말류", "설명": "티셔츠, 양말 등 기본의류", "추천": True},
        {"code": "G450101", "name": "의류(일반)", "설명": "일반 의류 전체", "추천": True},
        {"code": "S2045", "name": "속옷 소매업", "설명": "의류 판매업", "추천": True, "판매업": True},
        {"code": "S2027", "name": "의류 소매업", "설명": "의류 판매점/쇼핑몰", "추천": True, "판매업": True},
    ],
    "바지": [
        {"code": "G450101", "name": "의류(일반)", "설명": "바지, 청바지 등", "추천": True},
        {"code": "G4503", "name": "양말류", "설명": "기본 의류", "추천": False},
        {"code": "S2027", "name": "의류 소매업", "설명": "의류 판매업", "추천": True, "판매업": True},
    ],
    "운동화": [
        {"code": "G450601", "name": "신발류", "설명": "운동화, 스니커즈", "추천": True},
        {"code": "G270101", "name": "신발(일반)", "설명": "일반 신발류", "추천": True},
        {"code": "S2027", "name": "신발 소매업", "설명": "신발 판매점", "추천": True, "판매업": True},
    ],
    "책상": [
        {"code": "G2001", "name": "가구류", "설명": "책상, 테이블, 가구 전반", "추천": True},
        {"code": "G2002", "name": "사무용가구", "설명": "사무용 책상, 의자", "추천": True},
        {"code": "S2021", "name": "가구 소매업", "설명": "가구 판매점/쇼핑몰", "추천": True, "판매업": True},
    ],
    "소파": [
        {"code": "G2001", "name": "가구류", "설명": "소파, 쇼파, 가구", "추천": True},
        {"code": "S2021", "name": "가구 소매업", "설명": "가구 판매업", "추천": True, "판매업": True},
    ],
    "화장품": [
        {"code": "G1201", "name": "화장품류", "설명": "스킨케어, 색조화장품", "추천": True},
        {"code": "G1202", "name": "향수류", "설명": "향수, 방향제", "추천": False},
        {"code": "S120907", "name": "화장품 소매업", "설명": "화장품 판매점", "추천": True, "판매업": True},
    ],
    "스킨케어": [
        {"code": "G1201", "name": "화장품류", "설명": "스킨, 로션, 크림 등 화장품", "추천": True},
        {"code": "S120907", "name": "화장품 소매업", "설명": "화장품 판매점", "추천": True, "판매업": True},
    ],
    "반지": [
        {"code": "G3002", "name": "귀금속류", "설명": "반지, 목걸이, 귀걸이", "추천": True},
        {"code": "G4509", "name": "귀걸이류", "설명": "귀걸이 전용", "추천": False},
        {"code": "S2030", "name": "귀금속 소매업", "설명": "귀금속 판매점", "추천": True, "판매업": True},
    ],
    "앱": [
        {"code": "G0901", "name": "컴퓨터소프트웨어", "설명": "앱, 프로그램, 소프트웨어", "추천": True},
        {"code": "G0903", "name": "스마트폰앱", "설명": "모바일 애플리케이션", "추천": True},
    ],
    "커피": [
        {"code": "G3001", "name": "커피/차류", "설명": "커피원두, 인스턴트커피", "추천": True},
        {"code": "S4301", "name": "카페/음식점업", "설명": "카페, 커피숍 운영", "추천": True, "판매업": True},
    ],
    "카페": [
        {"code": "S4301", "name": "카페/음식점업", "설명": "카페, 커피숍 운영", "추천": True, "판매업": True},
        {"code": "G3001", "name": "커피/차류", "설명": "커피 상품도 함께 보호 가능", "추천": False},
    ],
}

ALIASES = {
    "쇼파": "소파",
    "책장": "책상",
    "테이블": "책상",
    "운동신발": "운동화",
    "스킨": "스킨케어",
    "화장": "화장품",
    "앱개발": "앱",
    "커피숍": "카페",
}


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def _score(query: str, key: str) -> float:
    nq = _normalize(query)
    nk = _normalize(key)
    if nq == nk:
        return 1.0
    if nq in nk or nk in nq:
        return 0.9
    return SequenceMatcher(None, nq, nk).ratio()


def suggest_similarity_codes(product_name: str, limit: int = 6) -> List[dict]:
    if not product_name.strip():
        return []

    normalized = _normalize(product_name)
    target = ALIASES.get(normalized, normalized)
    matches: List[dict] = []

    for key, codes in SIMILARITY_CODE_DB.items():
        score = max(_score(product_name, key), _score(target, key))
        if score < 0.35:
            continue
        for code in codes:
            matches.append({"기준상품": key, "매칭점수": round(score, 3), **code})

    deduped = {}
    for item in matches:
        current = deduped.get(item["code"])
        if current is None or item["매칭점수"] > current["매칭점수"]:
            deduped[item["code"]] = item

    sorted_items = sorted(
        deduped.values(),
        key=lambda row: (
            not row.get("추천", False),
            not row.get("판매업", False),
            -row["매칭점수"],
            row["code"],
        ),
    )
    return sorted_items[:limit]
