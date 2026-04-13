"""KIPRIS API 연동 + Mock 폴백
G코드/S코드 분리 검색 후 합산 지원
"""
import os
import re
import requests

KIPRIS_BASE = "http://plus.kipris.or.kr/kipo-api/kipi"


# ─── 유사도 계산 ────────────────────────────────────────────────
def _similarity_score(query: str, target: str) -> int:
    """두 상표명 간 유사도 점수 (0~100)"""
    q = re.sub(r"[^가-힣a-zA-Z0-9]", "", query).upper()
    t = re.sub(r"[^가-힣a-zA-Z0-9]", "", target).upper()
    if not q or not t:
        return 0
    if q == t:
        return 100
    if q in t or t in q:
        shorter, longer = (q, t) if len(q) <= len(t) else (t, q)
        return int(80 * len(shorter) / len(longer))
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1)) if len(s) >= 2 else set(s)
    bq, bt = bigrams(q), bigrams(t)
    if not bq or not bt:
        common = sum(1 for c in q if c in t)
        return int(60 * common / max(len(q), len(t)))
    overlap = len(bq & bt)
    score = int(2 * overlap / (len(bq) + len(bt)) * 100)
    return min(score, 79)


def _make_reason(query: str, target: str, score: int) -> str:
    q = re.sub(r"[^가-힣a-zA-Z0-9]", "", query).upper()
    t = re.sub(r"[^가-힣a-zA-Z0-9]", "", target).upper()
    if q == t:
        return "상표명 완전 일치"
    if q in t:
        return f"검색어 '{query}'이(가) 대상 상표에 포함"
    if t in q:
        return f"대상 상표 '{target}'이(가) 검색어에 포함"
    if score >= 60:
        return "칭호·외관 유사 (음절 구성 유사)"
    if score >= 40:
        return "일부 칭호 유사"
    return "음소 유사 가능성"


# ─── 단일 코드 API 호출 ─────────────────────────────────────────
def _fetch_one_code(name: str, code: str, api_key: str) -> list[dict]:
    """단일 유사군 코드로 KIPRIS 검색 → item 리스트 반환"""
    import xml.etree.ElementTree as ET

    params = {
        "ServiceKey": api_key,
        "trademarkName": name,
        "numOfRows": 20,
        "pageNo": 1,
    }
    if code:
        params["similarCode"] = code

    url = f"{KIPRIS_BASE}/trademarkInfoSearchService/getTrademarkInfoSearch"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)

    result_code = (root.findtext(".//resultCode") or
                   root.findtext(".//resultcode") or "").strip()
    if result_code and result_code != "00":
        result_msg = (root.findtext(".//resultMsg") or
                      root.findtext(".//resultmsg") or "")
        raise ValueError(f"KIPRIS 오류 [{result_code}]: {result_msg}")

    items = []
    for item in root.findall(".//item"):
        def get(tag):
            return (item.findtext(tag) or "").strip()

        app_no = get("applicationNumber") or get("출원번호")
        if not app_no:
            continue

        trademark = (get("tradeMarkName") or get("title") or
                     get("trademarkName") or "")
        applicant = get("applicantName") or get("출원인") or get("applicant") or ""
        app_date  = get("applicationDate") or get("출원일자") or get("applyDate") or ""
        status    = (get("registerStatus") or get("등록상태") or
                     get("trademarkStatus") or get("status") or "")

        score  = _similarity_score(name, trademark)
        reason = _make_reason(name, trademark, score)

        items.append({
            "출원번호": app_no,
            "상표명":   trademark or "(명칭 없음)",
            "출원인":   applicant or "-",
            "출원일":   app_date[:10] if len(app_date) >= 10 else app_date,
            "상태":     status or "-",
            "유사도":   score,
            "유사이유": reason,
        })
    return items


# ─── G/S 코드 분리 복수 검색 ────────────────────────────────────
def search_with_breakdown(trademark_name: str, similar_codes: list[str]) -> tuple[list[dict], dict]:
    """G코드/S코드 각각 검색 후 합산
    Returns:
        (결과 리스트, {"G": G건수, "S": S건수, "total": 전체건수, "source": "API"|"MOCK"})
    """
    api_key = os.getenv("KIPRIS_API_KEY", "").strip()

    if api_key:
        try:
            return _api_breakdown(trademark_name, similar_codes, api_key)
        except Exception as e:
            print(f"[KIPRIS API 오류] {e} → Mock 사용")

    # Mock 폴백
    results = _mock_results(trademark_name, similar_codes)
    g_codes = [c for c in similar_codes if c.upper().startswith("G")]
    s_codes = [c for c in similar_codes if c.upper().startswith("S")]
    total = len(results)
    g_cnt = max(0, total - len(s_codes))   # mock 분배 (근사치)
    s_cnt = total - g_cnt
    return results, {"G": g_cnt, "S": s_cnt, "total": total, "source": "MOCK"}


def _api_breakdown(name: str, codes: list[str], api_key: str) -> tuple[list[dict], dict]:
    g_codes = [c for c in codes if c.upper().startswith("G")]
    s_codes = [c for c in codes if c.upper().startswith("S")]

    seen: dict[str, dict] = {}   # 출원번호 → item (중복 제거)
    g_cnt = 0
    s_cnt = 0

    # G코드 검색
    for code in g_codes:
        items = _fetch_one_code(name, code, api_key)
        for item in items:
            if item["출원번호"] not in seen:
                seen[item["출원번호"]] = item
                g_cnt += 1

    # S코드 검색
    for code in s_codes:
        items = _fetch_one_code(name, code, api_key)
        for item in items:
            if item["출원번호"] not in seen:
                seen[item["출원번호"]] = item
                s_cnt += 1

    # 코드가 없는 경우 코드 없이 1회 검색
    if not g_codes and not s_codes:
        items = _fetch_one_code(name, "", api_key)
        for item in items:
            if item["출원번호"] not in seen:
                seen[item["출원번호"]] = item

    results = sorted(seen.values(), key=lambda x: x["유사도"], reverse=True)[:50]
    total = len(results)
    return results, {"G": g_cnt, "S": s_cnt, "total": total, "source": "API"}


# ─── 기존 호환 함수 (단순 래퍼) ─────────────────────────────────
def search_similar_trademarks(trademark_name: str, similar_codes: list[str]) -> list[dict]:
    results, _ = search_with_breakdown(trademark_name, similar_codes)
    return results


# ─── Mock 데이터 ─────────────────────────────────────────────────
MOCK_DB = {
    "POOKIE": [
        {"출원번호": "4020210088765", "상표명": "POOKIE STYLE", "출원인": "(주)푸키패션",
         "출원일": "2021-05-10", "상태": "등록", "유사도": 72,
         "유사이유": "요부 'POOKIE' 칭호 동일, 지정상품 동일류"},
        {"출원번호": "4020220034512", "상표명": "POOKEE", "출원인": "김○○",
         "출원일": "2022-03-14", "상태": "출원", "유사도": 58,
         "유사이유": "칭호 유사(POOKIE↔POOKEE), 스펠링 차이"},
        {"출원번호": "4020190056123", "상표명": "푸키", "출원인": "박△△",
         "출원일": "2019-08-22", "상태": "등록", "유사도": 65,
         "유사이유": "영문 'POOKIE' ↔ 한글 '푸키' 음역 동일"},
    ],
    "COOKIE": [
        {"출원번호": "4020200011111", "상표명": "COOKIE BEAR", "출원인": "쿠키베어㈜",
         "출원일": "2020-01-15", "상태": "등록", "유사도": 68,
         "유사이유": "요부 'COOKIE' 동일"},
    ],
    "DEFAULT": [
        {"출원번호": "4020230044444", "상표명": "{name} PLUS", "출원인": "(주)샘플코리아",
         "출원일": "2023-06-01", "상태": "등록", "유사도": 45,
         "유사이유": "일부 칭호 유사"},
        {"출원번호": "4020240022222", "상표명": "{name_lower}", "출원인": "홍길동",
         "출원일": "2024-03-15", "상태": "출원", "유사도": 60,
         "유사이유": "전체 칭호 유사"},
    ],
}


def _mock_results(name: str, codes: list[str]) -> list[dict]:
    upper = name.upper().split()[0]
    base = MOCK_DB.get(upper, MOCK_DB["DEFAULT"])
    results = []
    for r in base:
        item = r.copy()
        item["상표명"] = (item["상표명"]
                         .replace("{name}", name.upper())
                         .replace("{name_lower}", name.lower()))
        results.append(item)
    return results


# ─── 위험도 ─────────────────────────────────────────────────────
def get_risk_level(results: list[dict]) -> tuple[str, str]:
    if not results:
        return "LOW", "저위험"
    max_score = max(r["유사도"] for r in results)
    if max_score >= 70:
        return "HIGH", "고위험"
    if max_score >= 50:
        return "MEDIUM", "중위험"
    return "LOW", "저위험"
