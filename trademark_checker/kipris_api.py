"""
KIPRIS 상표 검색 — 웹 스크래핑 방식
엔드포인트: https://www.kipris.or.kr/kportal/resulta.do (AJAX)

검색 전략:
  1. 상표명으로 KIPRIS AJAX API 호출 → XML 파싱
  2. 유사군코드(G4503 등)가 지정된 경우:
     - G 코드 앞 2자리 숫자 → 류 번호(예: G4503 → 45류)
     - 검색 결과의 류코드(PRC 필드)와 비교해 클라이언트 필터링
  3. 반환 형식은 Mock 데이터와 동일

반환 dict:
  {
    "success": bool,
    "result_code": str,    # "00" = 성공
    "result_msg": str,
    "total_count": int,    # 필터 전 전체 건수
    "filtered_count": int, # 유사군코드 필터 후 건수
    "items": [
      {
        "applicationNumber": str,   # 출원번호
        "trademarkName": str,       # 상표명 (한글 또는 영문)
        "applicantName": str,       # 출원인
        "applicationDate": str,     # 출원일 YYYYMMDD
        "registerStatus": str,      # 출원/등록/거절/포기 등
        "classificationCode": str,  # 류 번호(복수 시 쉼표 구분)
        "registrationNumber": str,  # 등록번호 (없으면 "")
      }
    ],
    "mock": bool,
  }
"""

import os
import re
import sys
import requests
import xml.etree.ElementTree as ET

from similarity_code_db import get_class_for_code

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── 설정 ──────────────────────────────────────────────────────────
BASE_URL  = "https://www.kipris.or.kr/kportal/resulta.do"
USE_MOCK  = os.getenv("KIPRIS_USE_MOCK", "false").lower() == "true"

_SESSION  = None

def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.kipris.or.kr/kportal/search/search_trademark.do",
            "X-Requested-With": "XMLHttpRequest",
        })
    return _SESSION


# ── Mock 데이터 ────────────────────────────────────────────────────
_MOCK_DB = {
    "POOKIE": [
        {"applicationNumber": "4020230012345", "trademarkName": "POOKIE",
         "applicantName": "테스트주식회사", "applicationDate": "20230315",
         "registerStatus": "등록", "classificationCode": "45",
         "registrationNumber": "4012340000"},
        {"applicationNumber": "4020220098765", "trademarkName": "POOKIE BEAR",
         "applicantName": "홍길동", "applicationDate": "20220810",
         "registerStatus": "출원", "classificationCode": "18",
         "registrationNumber": ""},
    ],
}

def _mock_search(word: str, similar_goods_code: str, num_of_rows: int, page_no: int) -> dict:
    word_upper = word.upper()
    matched = [
        item for key, items in _MOCK_DB.items()
        if word_upper in key.upper()
        for item in items
    ]
    if similar_goods_code:
        cls = _class_from_goods_code(similar_goods_code)
        if cls:
            matched = [m for m in matched if cls in m["classificationCode"].split(",")]
    start = (page_no - 1) * num_of_rows
    return {
        "success": True, "result_code": "00", "result_msg": "MOCK 데이터",
        "total_count": len(matched), "filtered_count": len(matched),
        "items": matched[start: start + num_of_rows], "mock": True,
    }


# ── 유사군코드 → 류 번호 변환 ────────────────────────────────────
# G코드는 코드 앞 숫자가 류 번호와 일치하지 않으므로 (예: G270101→25류, G4503→25류)
# 외부 룩업테이블 없이는 정확한 매핑 불가 → 필터링은 호출자(app.py)에 위임
def _class_from_goods_code(code: str) -> str:
    """
    유사군코드에서 류 번호를 추출합니다.
    G/S 코드는 코드 숫자와 류 번호가 일치하지 않는 경우가 많으므로
    이 함수는 기본적으로 빈 문자열을 반환합니다.
    실제 필터링은 app.py의 CODE_TO_CLASS 룩업테이블을 사용하세요.
    """
    return get_class_for_code(code) or ""


# ── XML 파싱 헬퍼 ─────────────────────────────────────────────────
def _parse_classes(prc_html: str) -> list[str]:
    """
    PRC HTML에서 류 번호 목록 추출.
    '<a ...>09</a> <a ...>42</a>' → ['9', '42']
    '<font title="09 42 45"> .... </font>' → ['9', '42', '45']
    """
    # font title 우선 (전체 목록 포함)
    font_match = re.search(r'<font title="([^"]+)"', prc_html)
    if font_match:
        nums = font_match.group(1).split()
        return [str(int(n)) for n in nums if n.isdigit()]
    # 링크 텍스트
    nums = re.findall(r'>(\d+)<', prc_html)
    return [str(int(n)) for n in nums if n.isdigit()]


def _clean_name(html: str) -> str:
    """HTML 태그 제거 후 상표명 정리."""
    text = re.sub(r'<[^>]+>', '', html).strip()
    text = text.strip('"\'')
    return text


def _parse_articles(root: ET.Element) -> list[dict]:
    items = []
    for art in root.findall(".//article"):
        ktn = art.findtext("KTN", "").strip()
        etn = _clean_name(art.findtext("ETN", ""))
        name = ktn if ktn else etn

        classes = _parse_classes(art.findtext("PRC", ""))
        cls_str = ",".join(classes) if classes else ""

        items.append({
            "applicationNumber":  art.findtext("ANN", "").strip(),
            "trademarkName":      name,
            "applicantName":      art.findtext("APNM", "").strip(),
            "applicationDate":    art.findtext("AD", "").strip(),
            "registerStatus":     art.findtext("LST", "").strip(),
            "classificationCode": cls_str,
            "registrationNumber": art.findtext("RNN", "").strip(),
        })
    return items


# ── 핵심 함수 ─────────────────────────────────────────────────────
def search_trademark(
    word: str,
    similar_goods_code: str = "",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    KIPRIS에서 상표명 + 유사군코드로 검색합니다.

    Args:
        word:               검색할 상표명 (예: "POOKIE")
        similar_goods_code: 유사군코드 (예: "G4503"). 생략 시 전체 반환.
        num_of_rows:        페이지당 결과 수 (기본 10)
        page_no:            페이지 번호 (기본 1)

    Returns:
        표준 dict (상단 docstring 참조)
    """
    if USE_MOCK:
        return _mock_search(word, similar_goods_code, num_of_rows, page_no)

    target_class = _class_from_goods_code(similar_goods_code) if similar_goods_code else ""

    sess = _get_session()
    try:
        resp = sess.post(
            BASE_URL,
            data={
                "next":                    "trademarkList",
                "FROM":                    "SEARCH",
                "searchInTransKorToEng":   "N",
                "searchInTransEngToKor":   "N",
                "row":                     str(num_of_rows),
                "queryText":               word,
                "expression":              word,
                "page":                    str(page_no),
            },
            timeout=20,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return _err("서버 응답 타임아웃 (20초)")
    except requests.exceptions.RequestException as e:
        return _err(str(e))

    try:
        root = ET.fromstring(resp.text.strip())
    except ET.ParseError as e:
        return _err(f"XML 파싱 실패: {e}")

    flag = root.findtext("flag", "")
    if flag != "SUCCESS":
        msg = root.findtext("message", flag)
        return _err(f"KIPRIS 오류: {msg}")

    total_count = int(root.findtext(".//searchFound", "0"))
    items = _parse_articles(root)

    # 유사군코드 클라이언트 필터링
    if target_class:
        items = [
            item for item in items
            if target_class in item["classificationCode"].split(",")
        ]

    return {
        "success":        True,
        "result_code":    "00",
        "result_msg":     "OK",
        "total_count":    total_count,
        "filtered_count": len(items),
        "items":          items,
        "mock":           False,
    }


def search_all_pages(
    word: str,
    similar_goods_code: str = "",
    max_pages: int = 5,
    rows_per_page: int = 10,
) -> dict:
    """
    여러 페이지를 자동으로 순회하며 전체 결과를 수집합니다.
    유사군코드 필터링 시 서버가 필터를 지원하지 않으므로
    모든 페이지에서 클라이언트 필터링합니다.

    Args:
        max_pages: 최대 탐색 페이지 수 (기본 5 = 최대 50건)
    """
    all_items = []
    total_count = 0
    target_class = _class_from_goods_code(similar_goods_code) if similar_goods_code else ""

    for page in range(1, max_pages + 1):
        result = search_trademark(word, similar_goods_code="", num_of_rows=rows_per_page, page_no=page)
        if not result["success"]:
            if page == 1:
                return result
            break
        if page == 1:
            total_count = result["total_count"]
        page_items = result["items"]
        if not page_items:
            break

        if target_class:
            page_items = [
                item for item in page_items
                if target_class in item["classificationCode"].split(",")
            ]
        all_items.extend(page_items)

        # 마지막 페이지면 중단
        fetched = page * rows_per_page
        if fetched >= total_count:
            break

        # KIPRIS 서버 부하 방지
        import time as _time
        _time.sleep(0.5)

    return {
        "success":        True,
        "result_code":    "00",
        "result_msg":     "OK",
        "total_count":    total_count,
        "filtered_count": len(all_items),
        "items":          all_items,
        "mock":           False,
    }


def _err(msg: str) -> dict:
    return {
        "success": False, "result_code": "-1", "result_msg": msg,
        "total_count": 0, "filtered_count": 0, "items": [], "mock": False,
    }


# ── CLI / 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    word = sys.argv[1] if len(sys.argv) > 1 else "POOKIE"
    code = sys.argv[2] if len(sys.argv) > 2 else "G4503"

    print(f"검색어: {word}  /  유사군코드: {code or '(없음)'}")
    target_cls = _class_from_goods_code(code) if code else ""
    if target_cls:
        print(f"유사군코드 {code} → {target_cls}류 필터링")
    print()

    result = search_all_pages(word, similar_goods_code=code, max_pages=6)

    if not result["success"]:
        print(f"[오류] {result['result_msg']}")
        sys.exit(1)

    mock_label = " [MOCK]" if result["mock"] else ""
    print(f"전체 '{word}' 검색 결과: {result['total_count']}건{mock_label}")
    if code:
        print(f"유사군코드 {code} ({target_cls}류) 필터 후: {result['filtered_count']}건")
    print()

    if not result["items"]:
        print("조건에 맞는 결과 없음")
    else:
        print(f"{'출원번호':<16} {'상표명':<22} {'출원인':<18} {'출원일':<10} {'상태':<6} {'류'}")
        print("-" * 90)
        for item in result["items"]:
            print(
                f"{item['applicationNumber']:<16} "
                f"{item['trademarkName'][:20]:<22} "
                f"{item['applicantName'][:16]:<18} "
                f"{item['applicationDate']:<10} "
                f"{item['registerStatus']:<6} "
                f"{item['classificationCode']}"
            )
