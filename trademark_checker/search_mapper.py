"""상품명으로 류 추천을 제공한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List


PRODUCT_SEARCH_MAP: Dict[str, List[dict]] = {
    "가구": [
        {"류": "20류", "설명": "가구 제조/판매", "예시": "소파, 침대, 책상, 의자", "아이콘": "🪑"},
        {"류": "35류", "설명": "가구 소매업", "예시": "가구 판매점, 온라인몰", "아이콘": "🛍️"},
        {"류": "37류", "설명": "인테리어 서비스", "예시": "인테리어 시공", "아이콘": "🏠"},
    ],
    "커피": [
        {"류": "30류", "설명": "커피 제품", "예시": "커피원두, 캡슐커피, 믹스커피", "아이콘": "☕"},
        {"류": "43류", "설명": "카페/음식점", "예시": "커피숍, 카페, 테이크아웃", "아이콘": "🍽️"},
        {"류": "35류", "설명": "커피 소매업", "예시": "온라인 커피몰", "아이콘": "🛍️"},
    ],
    "옷": [
        {"류": "25류", "설명": "의류/패션", "예시": "티셔츠, 바지, 재킷, 원피스", "아이콘": "👕"},
        {"류": "35류", "설명": "의류 소매업", "예시": "옷가게, 온라인 쇼핑몰", "아이콘": "🛍️"},
    ],
    "의류": [
        {"류": "25류", "설명": "의류/패션", "예시": "티셔츠, 바지, 재킷", "아이콘": "👕"},
        {"류": "35류", "설명": "의류 소매업", "예시": "옷가게, 온라인 쇼핑몰", "아이콘": "🛍️"},
    ],
    "티셔츠": [
        {"류": "25류", "설명": "의류/패션", "예시": "티셔츠, 캐주얼의류", "아이콘": "👕"},
        {"류": "35류", "설명": "의류 소매업", "예시": "의류 판매업", "아이콘": "🛍️"},
    ],
    "신발": [
        {"류": "25류", "설명": "신발류", "예시": "운동화, 구두, 샌들", "아이콘": "👟"},
        {"류": "35류", "설명": "신발 소매업", "예시": "신발 판매점", "아이콘": "🛍️"},
    ],
    "화장품": [
        {"류": "3류", "설명": "화장품/미용", "예시": "스킨케어, 색조, 향수", "아이콘": "💄"},
        {"류": "44류", "설명": "미용 서비스", "예시": "피부관리, 미용실", "아이콘": "✨"},
        {"류": "35류", "설명": "화장품 소매업", "예시": "화장품 판매점", "아이콘": "🛍️"},
    ],
    "앱": [
        {"류": "9류", "설명": "소프트웨어/앱", "예시": "모바일앱, 프로그램", "아이콘": "📱"},
        {"류": "42류", "설명": "IT 서비스", "예시": "앱개발, IT컨설팅", "아이콘": "💻"},
    ],
    "음식점": [
        {"류": "43류", "설명": "음식점/식당", "예시": "레스토랑, 분식집, 치킨집", "아이콘": "🍽️"},
        {"류": "30류", "설명": "식품류", "예시": "소스, 양념, 반조리식품", "아이콘": "🥘"},
    ],
    "카페": [
        {"류": "43류", "설명": "카페/음료점", "예시": "커피숍, 디저트카페", "아이콘": "☕"},
        {"류": "30류", "설명": "커피/음료 제품", "예시": "커피원두, 차", "아이콘": "🥤"},
    ],
    "병원": [
        {"류": "44류", "설명": "의료 서비스", "예시": "병원, 의원, 클리닉", "아이콘": "🏥"},
        {"류": "10류", "설명": "의료기기", "예시": "의료장비, 수술도구", "아이콘": "🩺"},
    ],
    "학원": [
        {"류": "41류", "설명": "교육 서비스", "예시": "학원, 교습소, 온라인강의", "아이콘": "📘"},
    ],
    "게임": [
        {"류": "9류", "설명": "게임 소프트웨어", "예시": "게임앱, 비디오게임", "아이콘": "🎮"},
        {"류": "41류", "설명": "게임 서비스", "예시": "온라인게임 서비스", "아이콘": "🕹️"},
        {"류": "28류", "설명": "게임기/완구", "예시": "보드게임, 장난감", "아이콘": "🧸"},
    ],
    "가방": [
        {"류": "18류", "설명": "가방/가죽제품", "예시": "핸드백, 백팩, 지갑", "아이콘": "👜"},
        {"류": "35류", "설명": "가방 소매업", "예시": "가방 판매점", "아이콘": "🛍️"},
    ],
    "시계": [
        {"류": "14류", "설명": "시계/귀금속", "예시": "손목시계, 스마트워치", "아이콘": "⌚"},
        {"류": "35류", "설명": "시계 소매업", "예시": "시계 판매점", "아이콘": "🛍️"},
    ],
    "책": [
        {"류": "16류", "설명": "출판물/문구", "예시": "책, 잡지, 교재", "아이콘": "📚"},
        {"류": "41류", "설명": "출판/교육 서비스", "예시": "출판사, 교육콘텐츠", "아이콘": "📝"},
    ],
    "부동산": [
        {"류": "36류", "설명": "부동산 서비스", "예시": "부동산중개, 임대관리", "아이콘": "🏢"},
    ],
    "여행": [
        {"류": "39류", "설명": "여행/운송", "예시": "여행사, 투어, 렌터카", "아이콘": "✈️"},
        {"류": "43류", "설명": "숙박 서비스", "예시": "호텔, 펜션, 게스트하우스", "아이콘": "🛏️"},
    ],
    "건강": [
        {"류": "5류", "설명": "건강기능식품/의약품", "예시": "영양제, 건강식품", "아이콘": "💊"},
        {"류": "44류", "설명": "건강 서비스", "예시": "헬스케어, 건강검진", "아이콘": "🩺"},
    ],
    "반려동물": [
        {"류": "31류", "설명": "동물사료/반려용품", "예시": "펫푸드, 간식", "아이콘": "🐾"},
        {"류": "44류", "설명": "동물병원/펫서비스", "예시": "동물병원, 펫샵", "아이콘": "🐶"},
    ],
}

ALIASES = {
    "쇼파": "가구",
    "소파": "가구",
    "책상": "가구",
    "의자": "가구",
    "앱개발": "앱",
    "소프트웨어": "앱",
    "프로그램": "앱",
    "스킨케어": "화장품",
    "뷰티": "화장품",
    "식당": "음식점",
    "레스토랑": "음식점",
    "커피숍": "카페",
    "디저트카페": "카페",
    "원두": "커피",
    "병의원": "병원",
    "교습소": "학원",
}


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def _score(source: str, target: str) -> float:
    left = _normalize(source)
    right = _normalize(target)
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.93
    return SequenceMatcher(None, left, right).ratio()


def get_category_suggestions(query: str, limit: int = 3) -> List[dict]:
    """입력 키워드에 맞는 상품/서비스 추천을 반환한다."""
    if not query.strip():
        return []

    alias_target = ALIASES.get(_normalize(query), query)
    results: List[dict] = []
    seen = set()

    for keyword, rows in PRODUCT_SEARCH_MAP.items():
        match_score = max(_score(query, keyword), _score(alias_target, keyword))
        if match_score < 0.35:
            continue
        for row in rows:
            unique_key = (row["류"], row["설명"])
            if unique_key in seen:
                continue
            seen.add(unique_key)
            results.append({**row, "키워드": keyword, "매칭점수": round(match_score, 3)})

    results.sort(
        key=lambda item: (
            -item["매칭점수"],
            int(item["류"].replace("류", "")),
            item["설명"],
        )
    )
    return results[:limit]


def search_products(query: str, limit: int = 3) -> List[dict]:
    """기존 호환용 영문 키 결과도 함께 제공한다."""
    return [
        {
            "class_no": row["류"],
            "description": row["설명"],
            "example": row["예시"],
            "icon": row["아이콘"],
            "keyword": row["키워드"],
            "match_score": row["매칭점수"],
        }
        for row in get_category_suggestions(query, limit=limit)
    ]


def get_catalog() -> Dict[str, List[dict]]:
    """기존 호환용 카탈로그."""
    goods: List[dict] = []
    services: List[dict] = []
    seen = set()

    for keyword, rows in PRODUCT_SEARCH_MAP.items():
        for row in rows:
            unique_key = (row["류"], row["설명"])
            if unique_key in seen:
                continue
            seen.add(unique_key)
            payload = {
                "class_no": row["류"],
                "description": row["설명"],
                "example": row["예시"],
                "icon": row["아이콘"],
                "keyword": keyword,
            }
            class_number = int(row["류"].replace("류", ""))
            if class_number <= 34:
                goods.append(payload)
            else:
                services.append(payload)

    goods.sort(key=lambda item: (int(item["class_no"].replace("류", "")), item["description"]))
    services.sort(key=lambda item: (int(item["class_no"].replace("류", "")), item["description"]))
    return {"goods": goods, "services": services}
