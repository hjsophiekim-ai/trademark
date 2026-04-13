"""
상표 유사성 검토 도구 — Streamlit 앱
KIPRIS 실시간 웹 스크래핑 방식 (API 키 불필요)
"""

import io
import re
import time
import datetime
import streamlit as st
import pandas as pd
from fpdf import FPDF

import kipris_api  # 동일 폴더의 kipris_api.py

# ─── 페이지 설정 ────────────────────────────────────────────────
st.set_page_config(
    page_title="상표 유사성 검토",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 유사군 코드 데이터 (Python) ────────────────────────────────
SIMILAR_GROUP_CODES = [
    # 25류
    {"code": "G270101", "class": 25, "name": "의류(일반)",    "examples": ["티셔츠", "바지", "재킷"]},
    {"code": "G430301", "class": 25, "name": "내의류",        "examples": ["속옷", "팬티"]},
    {"code": "G450101", "class": 25, "name": "신발",          "examples": ["운동화", "구두"]},
    {"code": "G4502",   "class": 25, "name": "모자류",        "examples": ["야구모자", "비니"]},
    {"code": "G4503",   "class": 25, "name": "양말류",        "examples": ["양말", "스타킹"]},
    {"code": "G450401", "class": 25, "name": "장갑류",        "examples": ["면장갑", "가죽장갑"]},
    {"code": "G4513",   "class": 25, "name": "수영복",        "examples": ["수영복", "래시가드"]},
    {"code": "G450501", "class": 25, "name": "유아복",        "examples": ["배내옷", "유아복"]},
    # 18류
    {"code": "G2501",   "class": 18, "name": "가방류",        "examples": ["핸드백", "지갑"]},
    {"code": "G2703",   "class": 18, "name": "여행 가방",     "examples": ["캐리어", "여행가방"]},
    # 14류
    {"code": "G3002",   "class": 14, "name": "귀금속류",      "examples": ["금", "은"]},
    {"code": "G3501",   "class": 14, "name": "보석류",        "examples": ["다이아몬드", "루비"]},
    {"code": "G4509",   "class": 14, "name": "반지",          "examples": ["결혼반지"]},
    {"code": "G4401",   "class": 14, "name": "목걸이",        "examples": ["체인 목걸이"]},
    {"code": "G4510",   "class": 14, "name": "귀걸이",        "examples": ["귀걸이"]},
    {"code": "G3601",   "class": 14, "name": "시계",          "examples": ["손목시계"]},
    # 3류
    {"code": "G0301",   "class":  3, "name": "화장품류",      "examples": ["로션", "크림"]},
    {"code": "G0302",   "class":  3, "name": "향수류",        "examples": ["향수"]},
    {"code": "G0303",   "class":  3, "name": "두발 용품",     "examples": ["샴푸", "린스"]},
    # 9류
    {"code": "G0901",   "class":  9, "name": "컴퓨터",        "examples": ["노트북", "태블릿"]},
    {"code": "G0902",   "class":  9, "name": "소프트웨어",    "examples": ["앱", "프로그램"]},
    {"code": "G0903",   "class":  9, "name": "스마트폰",      "examples": ["스마트폰"]},
    # 35류 서비스
    {"code": "S2027",   "class": 35, "name": "의류 소매업",   "examples": ["의류 소매점"]},
    {"code": "S2043",   "class": 35, "name": "의류 도매업",   "examples": ["의류 도매상"]},
    {"code": "S2045",   "class": 35, "name": "속옷 소매업",   "examples": ["속옷 가게"]},
    {"code": "S2025",   "class": 35, "name": "가방 소매업",   "examples": ["가방 가게"]},
    {"code": "S2030",   "class": 35, "name": "귀금속 소매업", "examples": ["귀금속 상점"]},
    {"code": "S2012",   "class": 35, "name": "온라인 쇼핑몰", "examples": ["온라인 쇼핑몰"]},
    # 기타 서비스
    {"code": "S4301",   "class": 43, "name": "음식점업",      "examples": ["음식점", "카페"]},
    {"code": "S4302",   "class": 43, "name": "숙박업",        "examples": ["호텔"]},
    {"code": "S4101",   "class": 41, "name": "교육업",        "examples": ["학원"]},
    {"code": "S4102",   "class": 41, "name": "엔터테인먼트업", "examples": ["공연"]},
    {"code": "S4201",   "class": 42, "name": "IT 서비스업",   "examples": ["소프트웨어 개발"]},
    {"code": "S4202",   "class": 42, "name": "플랫폼 서비스", "examples": ["SNS 플랫폼"]},
    {"code": "S4401",   "class": 44, "name": "의료업",        "examples": ["병원"]},
    {"code": "S4402",   "class": 44, "name": "미용업",        "examples": ["미용실"]},
]

CODE_TO_CLASS = {g["code"]: g["class"] for g in SIMILAR_GROUP_CODES}
CODE_TO_NAME  = {g["code"]: g["name"]  for g in SIMILAR_GROUP_CODES}

def class_from_code(code: str) -> int:
    """유사군코드 → 류 번호"""
    if code in CODE_TO_CLASS:
        return CODE_TO_CLASS[code]
    m = re.match(r'[GgSs](\d{2})', code)
    if m:
        return int(m.group(1))
    return 0


# ─── 비용 계산기 ────────────────────────────────────────────────
FEES = {
    "APP_BASE":        62_000,
    "APP_EXCESS":       2_000,
    "REG_10Y":        211_000,
    "REG_5Y_HALF":    106_000,
    "PAPER_RATE":        0.20,
    "ATTY_BASE":      330_000,
    "ATTY_EXTRA_DISC":   0.90,
    "SMALL_BIZ_DISC":    0.50,
    "SME_DISC":          0.30,
}

def calculate_cost(classes: int, goods_per_class: list[int],
                   applicant_type: str, reg_term: int,
                   is_online: bool, include_atty: bool,
                   custom_atty: int = 0) -> dict:
    rows = []

    # 출원료
    app_fee = 0
    for i, g in enumerate(goods_per_class[:classes]):
        excess = max(0, g - 6)
        fee = FEES["APP_BASE"] + excess * FEES["APP_EXCESS"]
        app_fee += fee
        rows.append({"항목": f"출원료 {i+1}류 ({g}개 상품)", "금액": fee})

    if not is_online:
        sur = int(app_fee * FEES["PAPER_RATE"])
        app_fee += sur
        rows.append({"항목": "종이출원 가산 (20%)", "금액": sur})

    disc_rate = 0.0
    disc_label = ""
    if applicant_type == "소상공인":
        disc_rate, disc_label = FEES["SMALL_BIZ_DISC"], "소상공인 50% 감면"
    elif applicant_type == "중소기업":
        disc_rate, disc_label = FEES["SME_DISC"], "중소기업 30% 감면"
    if disc_rate:
        disc = int(app_fee * disc_rate)
        app_fee -= disc
        rows.append({"항목": disc_label, "금액": -disc})

    # 등록료
    if reg_term == 10:
        reg_fee = FEES["REG_10Y"] * classes
        rows.append({"항목": f"등록료 10년 일시납 ({classes}류)", "금액": reg_fee})
    else:
        reg_fee = FEES["REG_5Y_HALF"] * classes * 2
        rows.append({"항목": f"등록료 5년 전기납 ({classes}류)", "금액": FEES["REG_5Y_HALF"] * classes})
        rows.append({"항목": f"등록료 5년 후기납 ({classes}류)", "금액": FEES["REG_5Y_HALF"] * classes})

    # 변리사
    atty_fee = 0
    if include_atty:
        if custom_atty:
            atty_fee = custom_atty * classes
        else:
            atty_fee = FEES["ATTY_BASE"]
            for _ in range(1, classes):
                atty_fee += int(FEES["ATTY_BASE"] * FEES["ATTY_EXTRA_DISC"])
        rows.append({"항목": f"변리사 수임료 ({classes}류)", "금액": atty_fee})

    total = app_fee + reg_fee + atty_fee
    rows.append({"항목": "합계", "금액": total})
    return {"app": app_fee, "reg": reg_fee, "atty": atty_fee, "total": total, "rows": rows}


# ─── KIPRIS 검색 (재시도 + Mock 폴백) ───────────────────────────
def kipris_search_with_retry(word: str, codes: list[str],
                             max_pages: int = 5, timeout: int = 10) -> dict:
    """
    G코드 + S코드 각각 검색 → 합산 → 중복 제거
    실패 시 3회 재시도, 최종 실패 시 Mock 폴백
    """
    # 코드별 류 번호 수집 (중복 제거)
    classes = list({class_from_code(c) for c in codes if class_from_code(c) > 0})

    all_items: dict[str, dict] = {}   # applicationNumber → item
    total_count = 0
    is_mock = False
    source_label = ""

    for attempt in range(3):
        try:
            # 원본 타임아웃 일시 변경
            orig_timeout = kipris_api._get_session().get_adapter("https://").max_retries
            result = kipris_api.search_all_pages(
                word,
                similar_goods_code="",
                max_pages=max_pages,
                rows_per_page=10,
            )
            if result["success"]:
                total_count = result["total_count"]
                for item in result["items"]:
                    ann = item["applicationNumber"]
                    if ann and ann not in all_items:
                        all_items[ann] = item
                source_label = "실제 KIPRIS 데이터"
                break
        except Exception as e:
            if attempt < 2:
                time.sleep(0.5)
            else:
                # Mock 폴백
                result = kipris_api._mock_search(word, "", 50, 1)
                for item in result["items"]:
                    all_items[item["applicationNumber"]] = item
                total_count = result["total_count"]
                is_mock = True
                source_label = "Mock 데이터 (KIPRIS 연결 실패)"

    # 류 번호 필터링 (클라이언트)
    items = list(all_items.values())
    if classes and not is_mock:
        filtered = []
        for item in items:
            item_classes = [
                int(c) for c in item.get("classificationCode", "").split(",")
                if c.strip().isdigit()
            ]
            if any(c in item_classes for c in classes):
                filtered.append(item)
        items = filtered if filtered else items   # 필터 결과 없으면 전체 반환

    return {
        "items": items,
        "total_count": total_count,
        "filtered_count": len(items),
        "is_mock": is_mock,
        "source_label": source_label,
    }


# ─── 등록 가능성 계산 ───────────────────────────────────────────
STATUS_WEIGHT = {
    "등록": 1.0,
    "출원": 0.7,
    "심사중": 0.6,
    "거절": 0.1,
    "포기": 0.1,
    "무효": 0.1,
    "취하": 0.1,
    "소멸": 0.1,
}

def calc_registration_probability(word: str, items: list[dict]) -> tuple[float, str, str]:
    """
    (확률 0~100, 위험도, 의견) 반환
    - 동일 이름 등록 건: 큰 감점
    - 유사 이름 출원/등록: 중간 감점
    """
    word_upper = word.upper().strip()
    score = 100.0

    exact_active = []   # 동일 이름, 등록/출원 중
    similar_active = [] # 유사 이름, 등록/출원 중

    for item in items:
        name = item.get("trademarkName", "").upper().strip()
        status = item.get("registerStatus", "")
        weight = STATUS_WEIGHT.get(status, 0.5)

        if weight < 0.2:  # 거절·포기·소멸 → 무시
            continue

        if name == word_upper:
            exact_active.append(item)
            score -= 35 * weight
        elif word_upper in name or name in word_upper:
            similar_active.append(item)
            score -= 12 * weight
        elif _phonetic_similar(word_upper, name):
            similar_active.append(item)
            score -= 8 * weight

    score = max(0.0, min(100.0, score))

    if score >= 70:
        risk = "LOW"
        opinion = (
            f"'{word}'와 동일하거나 유사한 선행 상표가 적어 등록 가능성이 높습니다. "
            "단, 이 결과는 자동 분석이며 최종 판단은 변리사 검토가 필요합니다."
        )
    elif score >= 40:
        risk = "MEDIUM"
        opinion = (
            f"유사한 선행 상표 {len(similar_active)}건이 발견되었습니다. "
            "심사 단계에서 거절 가능성이 있으므로 전문가 검토를 권장합니다."
        )
    else:
        risk = "HIGH"
        opinion = (
            f"동일 또는 유사 상표 {len(exact_active) + len(similar_active)}건이 등록/출원 중입니다. "
            "등록이 어려울 수 있으며 상표명 변경 또는 류/상품 범위 조정이 필요합니다."
        )

    return round(score, 1), risk, opinion


def _phonetic_similar(a: str, b: str) -> bool:
    """간단한 음성 유사 판정 (첫 3글자 일치 + 길이 차이 ≤2)"""
    if len(a) < 3 or len(b) < 3:
        return False
    return a[:3] == b[:3] and abs(len(a) - len(b)) <= 2


# ─── PDF 생성 ───────────────────────────────────────────────────
class KoreanPDF(FPDF):
    """한글 폰트 지원 PDF (fpdf2 v2.5+ 방식)"""
    def __init__(self):
        super().__init__()
        import os
        self._korean_font = "helvetica"
        regular = "C:/Windows/Fonts/malgun.ttf"
        bold    = "C:/Windows/Fonts/malgunbd.ttf"
        try:
            if os.path.exists(regular):
                self.add_font("Korean",  "", regular)
                self._korean_font = "Korean"
            if os.path.exists(bold):
                self.add_font("KoreanB", "", bold)
        except Exception:
            pass

    def set_korean(self, size=10, bold=False):
        if bold and self._korean_font == "Korean":
            # Bold 폰트가 등록된 경우 KoreanB 사용, 없으면 Korean으로 폴백
            try:
                self.set_font("KoreanB", "", size)
                return
            except Exception:
                pass
        self.set_font(self._korean_font, "", size)

    def header(self):
        self.set_korean(9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "상표 유사성 검토 보고서 | 자동 생성 문서", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_korean(8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"- {self.page_no()} -", align="C")
        self.set_text_color(0, 0, 0)


def generate_pdf(word: str, codes: list[str], items: list[dict],
                 prob: float, risk: str, opinion: str,
                 cost_rows: list[dict] | None = None) -> bytes:
    pdf = KoreanPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    today = datetime.date.today().strftime("%Y년 %m월 %d일")

    # 제목
    pdf.set_korean(18, bold=True)
    pdf.cell(0, 12, "상표 유사성 검토 보고서", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_korean(10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"작성일: {today}  |  데이터 출처: KIPRIS 실시간 검색", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # 기본 정보
    pdf.set_fill_color(240, 245, 255)
    pdf.set_korean(11, bold=True)
    pdf.cell(0, 8, " 검토 대상 상표", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_korean(11)
    pdf.cell(35, 7, "상표명:", new_x="RIGHT")
    pdf.set_korean(13, bold=True)
    pdf.cell(0, 7, word, new_x="LMARGIN", new_y="NEXT")
    pdf.set_korean(10)
    code_str = "  ".join([f"{c} ({CODE_TO_NAME.get(c, '')})" for c in codes]) if codes else "미지정"
    pdf.cell(35, 7, "유사군코드:", new_x="RIGHT")
    pdf.cell(0, 7, code_str, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 등록 가능성
    risk_colors = {"LOW": (34, 197, 94), "MEDIUM": (234, 179, 8), "HIGH": (239, 68, 68)}
    risk_labels = {"LOW": "저위험 (등록 유리)", "MEDIUM": "중위험 (주의 필요)", "HIGH": "고위험 (등록 불리)"}
    rc = risk_colors.get(risk, (100, 100, 100))

    pdf.set_fill_color(240, 245, 255)
    pdf.set_korean(11, bold=True)
    pdf.cell(0, 8, " 등록 가능성 분석", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_korean(10)
    pdf.cell(35, 7, "등록 가능성:", new_x="RIGHT")
    pdf.set_text_color(*rc)
    pdf.set_korean(13, bold=True)
    pdf.cell(30, 7, f"{prob}%", new_x="RIGHT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_korean(10)
    pdf.cell(0, 7, f"  [{risk_labels.get(risk, risk)}]", new_x="LMARGIN", new_y="NEXT")
    pdf.set_korean(10)
    pdf.multi_cell(0, 6, f"검토 의견: {opinion}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 선행 상표 목록
    pdf.set_fill_color(240, 245, 255)
    pdf.set_korean(11, bold=True)
    pdf.cell(0, 8, f" 선행 유사상표 ({len(items)}건)", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    if not items:
        pdf.set_korean(10)
        pdf.cell(0, 7, "선행 상표 없음", new_x="LMARGIN", new_y="NEXT")
    else:
        # 테이블 헤더
        col_w = [38, 46, 38, 22, 16, 20]
        headers = ["출원번호", "상표명", "출원인", "출원일", "상태", "류"]
        pdf.set_fill_color(60, 90, 160)
        pdf.set_text_color(255, 255, 255)
        pdf.set_korean(9, bold=True)
        for h, w in zip(headers, col_w):
            pdf.cell(w, 7, h, border=1, fill=True, align="C", new_x="RIGHT")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_korean(8)

        for i, item in enumerate(items[:50]):
            fill = i % 2 == 0
            pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
            row = [
                item.get("applicationNumber", "")[:14],
                item.get("trademarkName", "")[:18],
                item.get("applicantName", "")[:14],
                item.get("applicationDate", ""),
                item.get("registerStatus", ""),
                item.get("classificationCode", "")[:8],
            ]
            for val, w in zip(row, col_w):
                pdf.cell(w, 6, str(val), border=1, fill=fill, new_x="RIGHT")
            pdf.ln()
        if len(items) > 50:
            pdf.set_korean(9)
            pdf.cell(0, 6, f"  ※ 총 {len(items)}건 중 50건 표시", new_x="LMARGIN", new_y="NEXT")

    # 비용 계산
    if cost_rows:
        pdf.add_page()
        pdf.set_fill_color(240, 245, 255)
        pdf.set_korean(11, bold=True)
        pdf.cell(0, 8, " 출원 비용 예상", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_korean(10)
        for row in cost_rows:
            label = str(row.get("항목", ""))
            amount = row.get("금액", 0)
            is_total = label == "합계"
            if is_total:
                pdf.set_korean(11, bold=True)
                pdf.set_fill_color(220, 230, 255)
                pdf.cell(100, 7, label, border=1, fill=True, new_x="RIGHT")
                pdf.cell(60, 7, f"{amount:,}원", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.set_korean(10)
                color = (220, 255, 220) if amount >= 0 else (255, 235, 235)
                pdf.set_fill_color(*color)
                pdf.cell(100, 6, label, border=1, fill=True, new_x="RIGHT")
                pdf.cell(60, 6, f"{amount:,}원", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    # 면책 고지
    pdf.ln(8)
    pdf.set_text_color(130, 130, 130)
    pdf.set_korean(8)
    pdf.multi_cell(
        0, 5,
        "※ 이 보고서는 KIPRIS 공개 데이터 기반 자동 분석 결과이며, 법적 효력이 없습니다.\n"
        "   최종 등록 가능성 판단은 반드시 전문 변리사의 검토를 받으시기 바랍니다.",
        new_x="LMARGIN", new_y="NEXT"
    )

    return bytes(pdf.output())


# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
.risk-low    { background:#dcfce7; color:#166534; padding:3px 10px; border-radius:12px; font-weight:600; font-size:13px; }
.risk-medium { background:#fef9c3; color:#713f12; padding:3px 10px; border-radius:12px; font-weight:600; font-size:13px; }
.risk-high   { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:12px; font-weight:600; font-size:13px; }
.badge-real  { background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:8px; font-size:12px; font-weight:600; }
.badge-mock  { background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:8px; font-size:12px; font-weight:600; }
.prob-bar    { height:18px; border-radius:9px; background:linear-gradient(90deg,#3b82f6,#6366f1); }
</style>
""", unsafe_allow_html=True)


# ─── 사이드바 ────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ 상표 검토 도구")
    page = st.radio("메뉴", ["🔍 유사성 검토", "💰 비용 계산기", "📋 검토 이력"])
    st.divider()
    st.caption("데이터: KIPRIS 실시간 스크래핑")
    st.caption("특허청 공식 데이터 기준")


# ═══════════════════════════════════════════════════════════════
# 1. 유사성 검토 탭
# ═══════════════════════════════════════════════════════════════
if page == "🔍 유사성 검토":
    st.header("유사성 검토")
    st.caption("KIPRIS 실시간 검색으로 선행 상표를 조회합니다")

    # 입력 폼
    with st.form("search_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            word = st.text_input("검색할 상표명 *", placeholder="예: POOKIE").strip()
        with c2:
            max_pages = st.selectbox("최대 검색 페이지", [3, 5, 10], index=1,
                                      help="페이지당 10건. 5페이지=최대 50건")

        st.markdown("##### 유사군 코드 선택")
        code_cols = st.columns(5)
        selected_codes: list[str] = []
        for i, g in enumerate(SIMILAR_GROUP_CODES):
            col = code_cols[i % 5]
            label = f"{g['code']}\n{g['name']} ({g['class']}류)"
            if col.checkbox(label, key=f"code_{g['code']}"):
                selected_codes.append(g["code"])

        submitted = st.form_submit_button("🔍 KIPRIS 검색", use_container_width=True, type="primary")

    # 검색 실행
    if submitted:
        if not word:
            st.warning("상표명을 입력해주세요.")
        else:
            with st.spinner("KIPRIS에서 실시간 검색 중..."):
                time.sleep(0.3)  # 최소 스피너 표시
                search_result = kipris_search_with_retry(word, selected_codes, max_pages=max_pages)
                st.session_state["last_search"] = {
                    "word": word,
                    "codes": selected_codes,
                    "result": search_result,
                }

    # 결과 표시
    if "last_search" in st.session_state:
        sr = st.session_state["last_search"]
        word_disp   = sr["word"]
        codes_disp  = sr["codes"]
        res         = sr["result"]
        items       = res["items"]
        is_mock     = res["is_mock"]
        src_label   = res["source_label"]

        # 데이터 출처 배지
        badge_html = (
            f'<span class="badge-real">🟢 {src_label}</span>'
            if not is_mock else
            f'<span class="badge-mock">🔵 {src_label}</span>'
        )
        st.markdown(badge_html, unsafe_allow_html=True)
        st.markdown("")

        # 통계 카드
        prob, risk, opinion = calc_registration_probability(word_disp, items)
        risk_css = {"LOW": "risk-low", "MEDIUM": "risk-medium", "HIGH": "risk-high"}[risk]
        risk_label_ko = {"LOW": "저위험", "MEDIUM": "중위험", "HIGH": "고위험"}[risk]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("전체 검색 건수", f"{res['total_count']}건")
        m2.metric("필터 후 건수",   f"{res['filtered_count']}건",
                  help="선택한 유사군코드 류에 해당하는 건수" if codes_disp else "필터 미적용")
        m3.metric("등록 가능성",    f"{prob}%")
        with m4:
            st.markdown(f"위험도")
            st.markdown(f'<span class="{risk_css}">{risk_label_ko}</span>', unsafe_allow_html=True)

        # 등록 가능성 바
        bar_color = "#22c55e" if risk == "LOW" else "#eab308" if risk == "MEDIUM" else "#ef4444"
        st.markdown(
            f'<div style="background:#f0f0f0;border-radius:9px;height:18px;margin:8px 0">'
            f'<div style="width:{prob}%;height:18px;border-radius:9px;background:{bar_color};'
            f'transition:width 0.5s"></div></div>',
            unsafe_allow_html=True
        )

        # 검토 의견
        icon = "✅" if risk == "LOW" else "⚠️" if risk == "MEDIUM" else "🚫"
        st.info(f"{icon} {opinion}")

        st.divider()

        # 결과 테이블
        if not items:
            st.success("선행 유사 상표가 없습니다. 등록에 유리합니다.")
        else:
            st.subheader(f"선행 상표 {len(items)}건")
            df = pd.DataFrame(items)[
                ["applicationNumber", "trademarkName", "applicantName",
                 "applicationDate", "registerStatus", "classificationCode"]
            ]
            df.columns = ["출원번호", "상표명", "출원인", "출원일", "상태", "류"]

            def color_status(val):
                c = {"등록": "background-color:#d1fae5",
                     "출원": "background-color:#dbeafe",
                     "거절": "background-color:#fee2e2",
                     "포기": "background-color:#f3f4f6"}.get(val, "")
                return c

            st.dataframe(
                df.style.applymap(color_status, subset=["상태"]),
                use_container_width=True,
                height=min(400, 40 + len(df) * 35),
            )

        # PDF 다운로드
        st.divider()
        st.subheader("보고서 다운로드")
        dl_c1, dl_c2 = st.columns(2)

        with dl_c1:
            if st.button("PDF 생성", use_container_width=True):
                with st.spinner("PDF 생성 중..."):
                    pdf_bytes = generate_pdf(
                        word_disp, codes_disp, items, prob, risk, opinion
                    )
                st.download_button(
                    "⬇ PDF 다운로드",
                    data=pdf_bytes,
                    file_name=f"상표검토_{word_disp}_{datetime.date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        with dl_c2:
            if items:
                csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    "⬇ CSV 다운로드",
                    data=csv_bytes,
                    file_name=f"상표검토_{word_disp}_{datetime.date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        # 검토 이력에 저장
        if "history" not in st.session_state:
            st.session_state["history"] = []
        hist_entry = {
            "검색일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "상표명": word_disp,
            "유사군코드": ", ".join(codes_disp) if codes_disp else "-",
            "결과건수": res["filtered_count"],
            "등록가능성": f"{prob}%",
            "위험도": risk_label_ko,
        }
        # 중복 방지 (같은 상표명+코드)
        existing = [h for h in st.session_state["history"]
                    if h["상표명"] == word_disp and h["유사군코드"] == hist_entry["유사군코드"]]
        if not existing:
            st.session_state["history"].insert(0, hist_entry)


# ═══════════════════════════════════════════════════════════════
# 2. 비용 계산기 탭
# ═══════════════════════════════════════════════════════════════
elif page == "💰 비용 계산기":
    st.header("출원 비용 계산기")
    st.caption("특허청 공식 수수료 기준 (2024년 전자출원)")

    with st.form("cost_form"):
        c1, c2 = st.columns(2)
        with c1:
            applicant_type = st.selectbox("출원인 유형",
                ["개인", "소상공인", "중소기업", "대기업", "법인"])
            classes = st.number_input("출원 류 수", 1, 10, 1)
            reg_term = st.radio("등록료 납부", [10, 5], format_func=lambda x: f"{x}년")
        with c2:
            is_online = st.checkbox("전자출원 (권장)", value=True)
            include_atty = st.checkbox("변리사 수임료 포함")
            custom_atty = 0
            if include_atty:
                custom_atty = st.number_input("류당 수임료 (0=기본 33만원)", 0, 2_000_000, 0, 10_000)

        goods_list = []
        st.markdown("##### 류별 지정상품 수")
        gcols = st.columns(min(classes, 5))
        for i in range(classes):
            col = gcols[i % 5]
            goods_list.append(col.number_input(f"{i+1}류", 1, 100, 6, key=f"g{i}"))

        calc_submitted = st.form_submit_button("비용 계산", use_container_width=True, type="primary")

    if calc_submitted:
        result = calculate_cost(
            classes, goods_list, applicant_type, reg_term,
            is_online, include_atty, custom_atty
        )
        st.session_state["last_cost"] = result

    if "last_cost" in st.session_state:
        cost = st.session_state["last_cost"]
        ca, cb, cc, cd = st.columns(4)
        ca.metric("출원료", f"{cost['app']:,}원")
        cb.metric("등록료", f"{cost['reg']:,}원")
        cc.metric("변리사", f"{cost['atty']:,}원")
        cd.metric("합계",   f"{cost['total']:,}원")

        df_cost = pd.DataFrame(cost["rows"])
        st.dataframe(df_cost, use_container_width=True, hide_index=True)

        # 마지막 검색과 합쳐서 PDF
        if "last_search" in st.session_state:
            sr = st.session_state["last_search"]
            if st.button("검토보고서 + 비용 PDF 생성"):
                items = sr["result"]["items"]
                prob, risk, opinion = calc_registration_probability(sr["word"], items)
                with st.spinner("PDF 생성 중..."):
                    pdf_bytes = generate_pdf(
                        sr["word"], sr["codes"], items,
                        prob, risk, opinion,
                        cost_rows=cost["rows"]
                    )
                st.download_button(
                    "⬇ 통합 PDF 다운로드",
                    data=pdf_bytes,
                    file_name=f"상표검토_{sr['word']}_{datetime.date.today()}.pdf",
                    mime="application/pdf",
                )


# ═══════════════════════════════════════════════════════════════
# 3. 검토 이력 탭
# ═══════════════════════════════════════════════════════════════
elif page == "📋 검토 이력":
    st.header("검토 이력")

    history = st.session_state.get("history", [])
    if not history:
        st.info("아직 검색 이력이 없습니다. 유사성 검토 탭에서 검색해주세요.")
    else:
        df_hist = pd.DataFrame(history)

        def color_risk(val):
            return {
                "저위험": "color:#166534;font-weight:600",
                "중위험": "color:#713f12;font-weight:600",
                "고위험": "color:#991b1b;font-weight:600",
            }.get(val, "")

        st.dataframe(
            df_hist.style.applymap(color_risk, subset=["위험도"]),
            use_container_width=True,
        )

        if st.button("이력 초기화"):
            st.session_state["history"] = []
            st.rerun()
