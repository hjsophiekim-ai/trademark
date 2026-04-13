"""키프리스 검색식 자동 생성"""
import re

# 영→한 대표 단어 음역 맵
EN_TO_KO = {
    "STYLE": "스타일", "FASHION": "패션", "BRAND": "브랜드",
    "BEAUTY": "뷰티", "LIFE": "라이프", "TECH": "테크",
    "LOVE": "러브", "STAR": "스타", "PLUS": "플러스",
    "PRO": "프로", "MAX": "맥스", "KING": "킹",
    "QUEEN": "퀸", "SHOP": "샵", "MARKET": "마켓",
    "WORLD": "월드", "GLOBAL": "글로벌", "DESIGN": "디자인",
    "ART": "아트", "SMART": "스마트", "BLUE": "블루",
    "GREEN": "그린", "RED": "레드", "GOLD": "골드",
    "SILVER": "실버", "ONE": "원", "PRIME": "프라임",
    "FOOD": "푸드", "CAFE": "카페", "FRESH": "프레시",
    "POOKIE": "푸키", "COOKIE": "쿠키", "LUCKY": "럭키",
    "HAPPY": "해피", "GOOD": "굿", "BEST": "베스트",
    "SUPER": "슈퍼", "SUPER": "수퍼", "POWER": "파워",
    "NATURE": "네이처", "BIO": "바이오", "ECO": "에코",
}


def generate_variants(word: str) -> list[str]:
    """단어의 유사 변형 목록 생성"""
    variants = set()
    w = word.strip().upper()
    wl = w.lower()

    # 원본
    variants.add(w)
    variants.add(wl)

    # 음소 변형 (p↔f, c↔k, s↔z, 모음 변형)
    subs = [
        ("PH", "F"), ("F", "PH"),
        ("C", "K"), ("K", "C"),
        ("S", "Z"), ("Z", "S"),
        ("IE", "Y"), ("Y", "IE"),
        ("OO", "U"), ("U", "OO"),
        ("EE", "I"), ("I", "EE"),
    ]
    for frm, to in subs:
        if frm in w:
            variants.add(w.replace(frm, to, 1))
        if frm in wl:
            variants.add(wl.replace(frm, to, 1))

    # 와일드카드
    if len(w) >= 4:
        variants.add(wl[:3] + "?")
        variants.add(wl[:max(3, len(wl) - 1)] + "?")

    # 한글 음역
    ko = EN_TO_KO.get(w)
    if ko:
        variants.add(ko)

    return sorted(v for v in variants if v)


def generate_search_formula(trademark_name: str, similar_codes: list[str]) -> str:
    """키프리스 검색식 생성 (TN=[...] SC=...)"""
    words = re.split(r"[\s\-_]+", trademark_name.strip())
    all_variants = []
    for word in words:
        if word:
            all_variants.extend(generate_variants(word))

    unique = list(dict.fromkeys(all_variants))
    tn_part = f"TN=[{'+'.join(unique)}]"
    sc_part = f" SC={'+'.join(similar_codes)}" if similar_codes else ""
    return tn_part + sc_part


def analyze_trademark_name(name: str) -> dict:
    """상표명 분석 (한글/영문/혼합 판단)"""
    has_korean = bool(re.search(r"[가-힣]", name))
    has_english = bool(re.search(r"[a-zA-Z]", name))
    has_number = bool(re.search(r"\d", name))
    words = re.split(r"[\s\-_]+", name.strip())
    return {
        "type": "혼합" if (has_korean and has_english) else ("한글" if has_korean else "영문"),
        "word_count": len([w for w in words if w]),
        "char_count": len(name.replace(" ", "")),
        "has_number": has_number,
        "words": [w for w in words if w],
    }
