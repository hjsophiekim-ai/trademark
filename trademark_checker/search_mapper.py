"""상품/서비스 검색어를 류 추천으로 변환한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List


PRODUCT_SEARCH_MAP: Dict[str, List[dict]] = {
    "가구": [
        {"class_no": "20류", "description": "가구 제조/판매", "example": "소파, 침대, 책상, 의자", "icon": "🪑"},
        {"class_no": "35류", "description": "가구 소매업", "example": "가구 판매점, 온라인몰", "icon": "🛍️"},
        {"class_no": "37류", "description": "인테리어 서비스", "example": "인테리어 시공", "icon": "🏠"},
    ],
    "커피": [
        {"class_no": "30류", "description": "커피 제품", "example": "커피원두, 캡슐커피, 믹스커피", "icon": "☕"},
        {"class_no": "43류", "description": "카페/음식점", "example": "커피숍, 카페, 테이크아웃", "icon": "🍽️"},
        {"class_no": "35류", "description": "커피 소매업", "example": "온라인 커피몰", "icon": "🛍️"},
    ],
    "옷": [
        {"class_no": "25류", "description": "의류/패션", "example": "티셔츠, 바지, 재킷, 원피스", "icon": "👕"},
        {"class_no": "35류", "description": "의류 소매업", "example": "옷가게, 온라인 쇼핑몰", "icon": "🛍️"},
    ],
    "의류": [
        {"class_no": "25류", "description": "의류/패션", "example": "티셔츠, 바지, 재킷", "icon": "👕"},
        {"class_no": "35류", "description": "의류 소매업", "example": "옷가게, 온라인 쇼핑몰", "icon": "🛍️"},
    ],
    "티셔츠": [
        {"class_no": "25류", "description": "의류/패션", "example": "티셔츠, 캐주얼의류", "icon": "👕"},
        {"class_no": "35류", "description": "의류 소매업", "example": "의류 판매업", "icon": "🛍️"},
    ],
    "신발": [
        {"class_no": "25류", "description": "신발류", "example": "운동화, 구두, 샌들", "icon": "👟"},
        {"class_no": "35류", "description": "신발 소매업", "example": "신발 판매점", "icon": "🛍️"},
    ],
    "화장품": [
        {"class_no": "3류", "description": "화장품/미용", "example": "스킨케어, 색조, 향수", "icon": "💄"},
        {"class_no": "44류", "description": "미용 서비스", "example": "피부관리, 미용실", "icon": "✨"},
        {"class_no": "35류", "description": "화장품 소매업", "example": "화장품 판매점", "icon": "🛍️"},
    ],
    "앱": [
        {"class_no": "9류", "description": "소프트웨어/앱", "example": "모바일앱, 프로그램", "icon": "📱"},
        {"class_no": "42류", "description": "IT 서비스", "example": "앱개발, IT컨설팅", "icon": "💻"},
    ],
    "음식점": [
        {"class_no": "43류", "description": "음식점/식당", "example": "레스토랑, 분식집, 치킨집", "icon": "🍽️"},
        {"class_no": "30류", "description": "식품류", "example": "소스, 양념, 반조리식품", "icon": "🥘"},
    ],
    "카페": [
        {"class_no": "43류", "description": "카페/음료점", "example": "커피숍, 디저트카페", "icon": "☕"},
        {"class_no": "30류", "description": "커피/음료 제품", "example": "커피원두, 차", "icon": "🥤"},
    ],
    "병원": [
        {"class_no": "44류", "description": "의료 서비스", "example": "병원, 의원, 클리닉", "icon": "🏥"},
        {"class_no": "10류", "description": "의료기기", "example": "의료장비, 수술도구", "icon": "🩺"},
    ],
    "학원": [
        {"class_no": "41류", "description": "교육 서비스", "example": "학원, 교습소, 온라인강의", "icon": "📘"},
    ],
    "게임": [
        {"class_no": "9류", "description": "게임 소프트웨어", "example": "게임앱, 비디오게임", "icon": "🎮"},
        {"class_no": "41류", "description": "게임 서비스", "example": "온라인게임 서비스", "icon": "🕹️"},
        {"class_no": "28류", "description": "게임기/완구", "example": "보드게임, 장난감", "icon": "🧸"},
    ],
    "가방": [
        {"class_no": "18류", "description": "가방/가죽제품", "example": "핸드백, 백팩, 지갑", "icon": "👜"},
        {"class_no": "35류", "description": "가방 소매업", "example": "가방 판매점", "icon": "🛍️"},
    ],
    "시계": [
        {"class_no": "14류", "description": "시계/귀금속", "example": "손목시계, 스마트워치", "icon": "⌚"},
        {"class_no": "35류", "description": "시계 소매업", "example": "시계 판매점", "icon": "🛍️"},
    ],
    "책": [
        {"class_no": "16류", "description": "출판물/문구", "example": "책, 잡지, 교재", "icon": "📚"},
        {"class_no": "41류", "description": "출판/교육 서비스", "example": "출판사, 교육콘텐츠", "icon": "📝"},
    ],
    "부동산": [
        {"class_no": "36류", "description": "부동산 서비스", "example": "부동산중개, 임대관리", "icon": "🏢"},
    ],
    "여행": [
        {"class_no": "39류", "description": "여행/운송", "example": "여행사, 투어, 렌터카", "icon": "✈️"},
        {"class_no": "43류", "description": "숙박 서비스", "example": "호텔, 펜션, 게스트하우스", "icon": "🛏️"},
    ],
    "건강": [
        {"class_no": "5류", "description": "건강기능식품/의약품", "example": "영양제, 건강식품", "icon": "💊"},
        {"class_no": "44류", "description": "건강 서비스", "example": "헬스케어, 건강검진", "icon": "🩺"},
    ],
    "반려동물": [
        {"class_no": "31류", "description": "동물사료/반려용품", "example": "펫푸드, 간식", "icon": "🐾"},
        {"class_no": "44류", "description": "동물병원/펫서비스", "example": "동물병원, 펫샵", "icon": "🐶"},
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


def search_products(query: str, limit: int = 3) -> List[dict]:
    """입력어와 가장 가까운 상품/서비스 추천을 반환한다."""
    if not query.strip():
        return []

    normalized = _normalize(query)
    alias_target = ALIASES.get(normalized, query)
    results: List[dict] = []
    seen = set()

    for keyword, options in PRODUCT_SEARCH_MAP.items():
        match_score = max(_score(query, keyword), _score(alias_target, keyword))
        if match_score < 0.35:
            continue
        for option in options:
            unique_key = (option["class_no"], option["description"])
            if unique_key in seen:
                continue
            seen.add(unique_key)
            results.append({"keyword": keyword, "match_score": round(match_score, 3), **option})

    results.sort(
        key=lambda item: (
            -item["match_score"],
            int(item["class_no"].replace("류", "")),
            item["description"],
        )
    )
    return results[:limit]


def get_catalog() -> Dict[str, List[dict]]:
    """전체 상품/서비스 카탈로그를 상품과 서비스로 분리해서 반환한다."""
    goods: List[dict] = []
    services: List[dict] = []
    seen = set()

    for keyword, options in PRODUCT_SEARCH_MAP.items():
        for option in options:
            unique_key = (option["class_no"], option["description"])
            if unique_key in seen:
                continue
            seen.add(unique_key)
            payload = {"keyword": keyword, **option}
            class_number = int(option["class_no"].replace("류", ""))
            if class_number <= 34:
                goods.append(payload)
            else:
                services.append(payload)

    goods.sort(key=lambda item: (int(item["class_no"].replace("류", "")), item["description"]))
    services.sort(key=lambda item: (int(item["class_no"].replace("류", "")), item["description"]))
    return {"goods": goods, "services": services}
