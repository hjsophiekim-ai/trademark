"""
상표 유사성 검토 시스템 (Streamlit)
실행: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import datetime
import os
import io

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.trademark_data import (
    CLASS_DATABASE, GOODS_LIST,
    get_goods_by_query, get_classes_for_goods, get_similar_codes_for_goods,
)
from utils.search_formula import generate_search_formula, generate_variants, analyze_trademark_name
from utils.kipris_api import search_similar_trademarks, search_with_breakdown, get_risk_level

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="상표 유사성 검토 시스템",
    page_icon="™",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* 전체 폰트 */
html, body, [class*="css"] { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; }

/* 위저드 스텝 */
.step-bar { display:flex; gap:0; margin-bottom:24px; }
.step-item { flex:1; text-align:center; padding:10px 4px; border-radius:8px;
             font-size:12px; font-weight:600; }
.step-done  { background:#dcfce7; color:#16a34a; }
.step-active{ background:#dbeafe; color:#1d4ed8; border:2px solid #3b82f6; }
.step-todo  { background:#f3f4f6; color:#9ca3af; }

/* 위험도 배지 */
.risk-high   { background:#fee2e2; color:#dc2626; padding:4px 12px; border-radius:99px; font-weight:700; }
.risk-medium { background:#fef3c7; color:#d97706; padding:4px 12px; border-radius:99px; font-weight:700; }
.risk-low    { background:#dcfce7; color:#16a34a; padding:4px 12px; border-radius:99px; font-weight:700; }

/* 결과 카드 */
.result-card { border:1px solid #e5e7eb; border-radius:10px; padding:14px;
               margin-bottom:10px; background:white; }
.result-card:hover { border-color:#3b82f6; }

/* 상표명 분석 박스 */
.analysis-box { background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px;
                padding:12px 16px; margin-top:8px; }

/* 사이드바 버튼 간격 */
section[data-testid="stSidebar"] .stButton { margin-bottom:4px; }

/* 섹션 헤더 */
.section-header { font-size:18px; font-weight:700; color:#1e3a5f;
                  border-left:4px solid #3b82f6; padding-left:10px; margin:16px 0 10px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 세션 초기화
# ─────────────────────────────────────────────
def init_session():
    defaults = {
        "page": "home",
        "step": 1,
        "trademark_name": "",
        "selected_goods": [],        # list[dict]
        "search_formula": "",
        "search_results": [],
        "search_breakdown": {},      # {"G": N, "S": M, "total": T, "source": "API"|"MOCK"}
        "risk_level": "LOW",
        "opinion": "",
        "history": [],               # list[dict]
        "cases": [],                 # list[dict] - 저장된 케이스
        "editing_opinion": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

OFFICE_NAME = os.getenv("OFFICE_NAME", "상표 관리 시스템")


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"### ™ {OFFICE_NAME}")
        st.divider()

        nav = [
            ("🏠", "홈 (새 검토)", "home"),
            ("📋", f"검색 히스토리 ({len(st.session_state.history)})", "history"),
            ("📊", f"케이스 관리 ({len(st.session_state.cases)})", "cases"),
            ("📄", "보고서 관리", "reports"),
            ("⚙️", "설정", "settings"),
            ("❓", "사용 가이드", "guide"),
        ]
        for icon, label, page_id in nav:
            is_active = st.session_state.page == page_id
            if st.button(
                f"{icon}  {label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                key=f"nav_{page_id}",
            ):
                st.session_state.page = page_id
                st.rerun()

        # 현재 검토 중인 상표명 표시
        if st.session_state.trademark_name and st.session_state.page == "home":
            st.divider()
            st.caption("현재 검토 중")
            st.info(f"**{st.session_state.trademark_name}**\n\n"
                    f"단계 {st.session_state.step}/5")

render_sidebar()


# ─────────────────────────────────────────────
# 위저드 단계 표시
# ─────────────────────────────────────────────
STEPS = ["1. 상표명", "2. 상품 선택", "3. 검색식", "4. 검색 결과", "5. 보고서"]

def render_step_bar(current: int):
    cols = st.columns(len(STEPS))
    for i, (col, label) in enumerate(zip(cols, STEPS)):
        sno = i + 1
        if sno < current:
            cls = "step-done"
            txt = "✓ " + label
        elif sno == current:
            cls = "step-active"
            txt = label
        else:
            cls = "step-todo"
            txt = label
        with col:
            st.markdown(f'<div class="step-item {cls}">{txt}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# STEP 1 - 상표명 입력
# ─────────────────────────────────────────────
def render_step1():
    st.markdown('<div class="section-header">STEP 1 — 상표명 입력</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input(
            "검토할 상표명을 입력하세요",
            value=st.session_state.trademark_name,
            placeholder="예: POOKIE  /  미래패션  /  MiraeFashion",
            help="영문·한글·혼합 모두 가능합니다.",
        )

        if name:
            analysis = analyze_trademark_name(name)
            st.markdown(f"""
<div class="analysis-box">
  <b>상표명 분석</b><br>
  유형: <b>{analysis['type']}</b> &nbsp;|&nbsp;
  글자 수: <b>{analysis['char_count']}</b> &nbsp;|&nbsp;
  단어 수: <b>{analysis['word_count']}</b>
  {'&nbsp;|&nbsp; ⚠️ 숫자 포함' if analysis['has_number'] else ''}
</div>
""", unsafe_allow_html=True)

            # 검색 변형 미리보기
            if analysis["words"]:
                variants = generate_variants(analysis["words"][0])[:8]
                st.caption("자동 생성 변형어: " + "  |  ".join(variants))

    with col2:
        st.markdown("**입력 예시**")
        examples = ["POOKIE", "미래패션", "TechVision", "준호베이커리", "HANJI"]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                st.session_state.trademark_name = ex
                st.rerun()

    # 다음 버튼
    st.divider()
    col_a, col_b = st.columns([4, 1])
    with col_b:
        if st.button("다음 →", type="primary", use_container_width=True, disabled=not name.strip()):
            st.session_state.trademark_name = name.strip()
            st.session_state.step = 2
            st.rerun()


# ─────────────────────────────────────────────
# STEP 2 - 상품 선택 (자동완성)
# ─────────────────────────────────────────────
def render_step2():
    st.markdown('<div class="section-header">STEP 2 — 지정상품 선택</div>', unsafe_allow_html=True)
    st.caption("상품명이나 류 번호를 검색하세요. 복수 선택 가능합니다.")

    col1, col2 = st.columns([3, 2])

    with col1:
        query = st.text_input("상품 검색", placeholder="예: 티셔츠 / 화장품 / 25류 / 소프트웨어")
        filtered = get_goods_by_query(query)
        labels = [g["label"] for g in filtered]

        selected_labels = st.multiselect(
            "상품 선택 (복수 선택 가능)",
            options=labels,
            default=[g["label"] for g in st.session_state.selected_goods
                     if g["label"] in labels],
            help="선택하면 유사군 코드가 자동으로 세팅됩니다.",
        )

        # 선택된 label → dict 로 변환
        label_map = {g["label"]: g for g in GOODS_LIST}
        st.session_state.selected_goods = [
            label_map[lb] for lb in selected_labels if lb in label_map
        ]

    with col2:
        if st.session_state.selected_goods:
            st.markdown("**선택된 상품**")
            classes = get_classes_for_goods(st.session_state.selected_goods)
            codes = get_similar_codes_for_goods(st.session_state.selected_goods)

            for g in st.session_state.selected_goods:
                st.markdown(f"- {g['goods']} `{g['class_no']}`")

            st.divider()
            st.markdown(f"**지정 류:** {', '.join(classes)}")
            st.markdown(f"**유사군 코드:** {', '.join(codes)}")
        else:
            # 빠른 선택 - 자주 쓰는 류
            st.markdown("**자주 선택하는 상품군**")
            quick = {
                "👕 의류 (25류)": "티셔츠",
                "💄 화장품 (3류)": "화장품",
                "🍰 제과 (30류)": "케이크",
                "📱 소프트웨어 (9류)": "소프트웨어",
                "🍽️ 음식점 (43류)": "식당",
                "💍 장신구 (14류)": "반지",
            }
            for label, q in quick.items():
                if st.button(label, use_container_width=True, key=f"quick_{q}"):
                    matches = get_goods_by_query(q)
                    if matches:
                        st.session_state.selected_goods = [matches[0]]
                    st.rerun()

    st.divider()
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← 이전", use_container_width=True):
            st.session_state.step = 1; st.rerun()
    with c3:
        disabled = len(st.session_state.selected_goods) == 0
        if st.button("다음 →", type="primary", use_container_width=True, disabled=disabled):
            codes = get_similar_codes_for_goods(st.session_state.selected_goods)
            st.session_state.search_formula = generate_search_formula(
                st.session_state.trademark_name, codes
            )
            st.session_state.step = 3
            st.rerun()


# ─────────────────────────────────────────────
# STEP 3 - 검색식 확인 & 편집
# ─────────────────────────────────────────────
def render_step3():
    st.markdown('<div class="section-header">STEP 3 — 키프리스 검색식 확인</div>', unsafe_allow_html=True)

    codes = get_similar_codes_for_goods(st.session_state.selected_goods)
    classes = get_classes_for_goods(st.session_state.selected_goods)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**검색식 (직접 수정 가능)**")
        formula = st.text_area(
            label="검색식",
            value=st.session_state.search_formula,
            height=100,
            label_visibility="collapsed",
        )
        st.session_state.search_formula = formula

        if st.button("🔄 검색식 재생성", use_container_width=False):
            st.session_state.search_formula = generate_search_formula(
                st.session_state.trademark_name, codes
            )
            st.rerun()

    with col2:
        st.markdown("**검토 요약**")
        st.info(
            f"**상표명:** {st.session_state.trademark_name}\n\n"
            f"**상품:** {', '.join(g['goods'] for g in st.session_state.selected_goods)}\n\n"
            f"**지정류:** {', '.join(classes)}\n\n"
            f"**유사군:** {', '.join(codes)}"
        )
        st.markdown("[🔗 키프리스 열기](https://www.kipris.or.kr/khome/main.do)", unsafe_allow_html=False)

    # 변형어 목록 표시
    with st.expander("📋 자동 생성 검색 변형어 보기"):
        for word in st.session_state.trademark_name.split():
            variants = generate_variants(word)
            st.markdown(f"**{word}** → " + " | ".join(variants))

    st.divider()
    c1, _, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← 이전", use_container_width=True): st.session_state.step = 2; st.rerun()
    with c3:
        if st.button("🔍 검색 실행 →", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()


# ─────────────────────────────────────────────
# STEP 4 - 검색 결과
# ─────────────────────────────────────────────
def render_step4():
    st.markdown('<div class="section-header">STEP 4 — 검색 결과</div>', unsafe_allow_html=True)

    codes = get_similar_codes_for_goods(st.session_state.selected_goods)

    # 처음 방문 시 자동 검색
    if not st.session_state.search_results:
        g_codes = [c for c in codes if c.upper().startswith("G")]
        s_codes = [c for c in codes if c.upper().startswith("S")]
        spinner_msg = (f"유사 상표 검색 중… "
                       f"G코드 {len(g_codes)}개 + S코드 {len(s_codes)}개 분리 검색")
        with st.spinner(spinner_msg):
            results, breakdown = search_with_breakdown(st.session_state.trademark_name, codes)
            st.session_state.search_results = results
            st.session_state.search_breakdown = breakdown
            risk_level, _ = get_risk_level(results)
            st.session_state.risk_level = risk_level

    results   = st.session_state.search_results
    breakdown = st.session_state.get("search_breakdown", {})
    risk_level = st.session_state.risk_level
    risk_labels = {"HIGH": ("고위험", "🔴"), "MEDIUM": ("중위험", "🟡"), "LOW": ("저위험", "🟢")}
    risk_text, risk_icon = risk_labels[risk_level]

    # ── G/S 코드 분리 검색 결과 건수 배너 ──
    if breakdown:
        source_badge = "🟢 실제 KIPRIS" if breakdown.get("source") == "API" else "🟡 Mock 데이터"
        g_codes_used = [c for c in codes if c.upper().startswith("G")]
        s_codes_used = [c for c in codes if c.upper().startswith("S")]
        st.markdown(f"""
<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;
            padding:10px 16px;margin-bottom:12px;font-size:14px;">
  <b>🔍 복수 코드 검색 결과</b> &nbsp;|&nbsp; {source_badge}<br>
  G코드 검색 ({', '.join(g_codes_used) or '없음'}): <b>{breakdown.get('G', 0)}건</b>
  &nbsp;+&nbsp;
  S코드 검색 ({', '.join(s_codes_used) or '없음'}): <b>{breakdown.get('S', 0)}건</b>
  &nbsp;→&nbsp; 중복 제거 후 <b style="color:#1d4ed8;">총 {breakdown.get('total', len(results))}건</b>
</div>
""", unsafe_allow_html=True)

    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("선행상표 수 (합산)", f"{len(results)}건")
    col2.metric("최고 유사도", f"{max((r['유사도'] for r in results), default=0)}%")
    col3.metric("위험도", f"{risk_icon} {risk_text}")
    col4.metric("검색 상표명", st.session_state.trademark_name)

    st.divider()

    # 재검색 버튼
    c_left, c_right = st.columns([5, 1])
    with c_right:
        if st.button("🔄 재검색", use_container_width=True):
            st.session_state.search_results = []
            st.session_state.search_breakdown = {}
            st.rerun()

    # 결과 테이블
    if results:
        df = pd.DataFrame(results)
        df["유사도"] = df["유사도"].astype(str) + "%"

        def color_score(val):
            v = int(val.replace("%", ""))
            if v >= 70: return "background-color:#fee2e2; color:#dc2626; font-weight:bold"
            if v >= 50: return "background-color:#fef3c7; color:#d97706; font-weight:bold"
            return "background-color:#dcfce7; color:#16a34a; font-weight:bold"

        styled = df.style.applymap(color_score, subset=["유사도"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # 상세 카드
        with st.expander("📋 상세 보기"):
            for r in results:
                score = r["유사도"]
                color = "🔴" if score >= 70 else ("🟡" if score >= 50 else "🟢")
                st.markdown(f"""
**{color} {r['상표명']}** — 유사도 {score}%
- 출원번호: `{r['출원번호']}` | 출원인: {r['출원인']} | 상태: {r['상태']} | 출원일: {r['출원일']}
- 유사 이유: *{r['유사이유']}*
---""")
    else:
        st.success("✅ 유사 상표가 검색되지 않았습니다. 등록 가능성이 높습니다.")

    # CSV 다운로드
    if results:
        df_plain = pd.DataFrame(results)
        csv_buf = io.StringIO()
        df_plain.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ 결과 CSV 다운로드",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"상표검색_{st.session_state.trademark_name}_{datetime.date.today()}.csv",
            mime="text/csv",
        )

    st.divider()
    c1, _, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← 이전", use_container_width=True):
            st.session_state.step = 3; st.rerun()
    with c3:
        if st.button("📄 보고서 작성 →", type="primary", use_container_width=True):
            st.session_state.step = 5; st.rerun()


# ─────────────────────────────────────────────
# STEP 5 - 보고서 작성 & 저장
# ─────────────────────────────────────────────
def render_step5():
    st.markdown('<div class="section-header">STEP 5 — 검토 의견 & 보고서</div>', unsafe_allow_html=True)

    results = st.session_state.search_results
    risk_level = st.session_state.risk_level
    risk_labels = {"HIGH": "고위험 🔴", "MEDIUM": "중위험 🟡", "LOW": "저위험 🟢"}

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("**검토 의견 작성**")

        # 자동 의견 초안 생성
        if not st.session_state.opinion:
            goods_str = ", ".join(g["goods"] for g in st.session_state.selected_goods)
            classes_str = ", ".join(get_classes_for_goods(st.session_state.selected_goods))
            if risk_level == "HIGH":
                draft = (f"'{st.session_state.trademark_name}'은(는) {classes_str} 지정상품({goods_str})에 대해 "
                         f"선행 유사상표와의 유사도가 높아 등록 가능성이 낮습니다. "
                         f"상표명 변경 또는 지정상품 축소를 검토하시기 바랍니다.")
            elif risk_level == "MEDIUM":
                draft = (f"'{st.session_state.trademark_name}'은(는) {classes_str}류 지정상품({goods_str})에 대해 "
                         f"일부 선행 상표와 유사성이 인정될 수 있으나, 전체적인 관념·칭호·외관을 종합하면 "
                         f"등록 가능성이 있습니다. 의견 제출 준비를 권장합니다.")
            else:
                draft = (f"'{st.session_state.trademark_name}'은(는) {classes_str}류 지정상품({goods_str})에 대해 "
                         f"선행 유사상표와의 유사도가 낮아 등록 가능성이 높습니다.")
            st.session_state.opinion = draft

        opinion = st.text_area(
            "검토 의견",
            value=st.session_state.opinion,
            height=180,
            label_visibility="collapsed",
        )
        st.session_state.opinion = opinion

    with col2:
        st.markdown("**보고서 요약**")
        st.markdown(f"""
| 항목 | 내용 |
|------|------|
| 상표명 | **{st.session_state.trademark_name}** |
| 지정류 | {', '.join(get_classes_for_goods(st.session_state.selected_goods))} |
| 상품 | {', '.join(g['goods'] for g in st.session_state.selected_goods)} |
| 선행상표 | {len(results)}건 |
| 위험도 | {risk_labels[risk_level]} |
| 작성일 | {datetime.date.today()} |
""")

    st.divider()

    # 버튼 행
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        if st.button("← 이전", use_container_width=True):
            st.session_state.step = 4; st.rerun()
    with c2:
        if st.button("💾 케이스 저장", use_container_width=True):
            case = {
                "id": f"case_{len(st.session_state.cases)+1:03d}",
                "상표명": st.session_state.trademark_name,
                "상품": [g["goods"] for g in st.session_state.selected_goods],
                "지정류": get_classes_for_goods(st.session_state.selected_goods),
                "유사군": get_similar_codes_for_goods(st.session_state.selected_goods),
                "검색식": st.session_state.search_formula,
                "위험도": risk_level,
                "선행상표수": len(results),
                "의견": opinion,
                "작성일": str(datetime.date.today()),
                "결과": results,
            }
            st.session_state.cases.append(case)
            st.session_state.history.append(case)
            st.success(f"✅ 케이스 '{case['id']}' 저장 완료!")
    with c3:
        # TXT 보고서 다운로드
        report_txt = _build_report_text()
        st.download_button(
            "📄 TXT 다운로드",
            data=report_txt.encode("utf-8"),
            file_name=f"보고서_{st.session_state.trademark_name}_{datetime.date.today()}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with c4:
        if st.button("🏠 새 검토 시작", type="primary", use_container_width=True):
            _reset_wizard()
            st.rerun()


def _build_report_text() -> str:
    results = st.session_state.search_results
    risk_labels = {"HIGH": "고위험", "MEDIUM": "중위험", "LOW": "저위험"}
    lines = [
        "=" * 60,
        "       상표 유사성 검토 보고서",
        "=" * 60,
        f"검토 상표명 : {st.session_state.trademark_name}",
        f"지정 류     : {', '.join(get_classes_for_goods(st.session_state.selected_goods))}",
        f"지정 상품   : {', '.join(g['goods'] for g in st.session_state.selected_goods)}",
        f"위험도      : {risk_labels.get(st.session_state.risk_level, '-')}",
        f"작성일      : {datetime.date.today()}",
        "",
        "[키프리스 검색식]",
        st.session_state.search_formula,
        "",
        f"[선행 유사상표 ({len(results)}건)]",
    ]
    for r in results:
        lines += [
            f"  ▸ {r['상표명']} | 유사도: {r['유사도']}% | {r['상태']} | {r['출원일']}",
            f"    출원인: {r['출원인']} | 출원번호: {r['출원번호']}",
            f"    유사 이유: {r['유사이유']}",
        ]
    lines += [
        "",
        "[검토 의견]",
        st.session_state.opinion,
        "",
        "=" * 60,
        f"({OFFICE_NAME})",
    ]
    return "\n".join(lines)


def _reset_wizard():
    for k in ["step", "trademark_name", "selected_goods", "search_formula",
              "search_results", "search_breakdown", "risk_level", "opinion"]:
        if k == "step":
            st.session_state[k] = 1
        elif k in ["selected_goods", "search_results"]:
            st.session_state[k] = []
        elif k == "search_breakdown":
            st.session_state[k] = {}
        elif k == "risk_level":
            st.session_state[k] = "LOW"
        else:
            st.session_state[k] = ""


# ─────────────────────────────────────────────
# 히스토리 페이지
# ─────────────────────────────────────────────
def render_history():
    st.title("📋 검색 히스토리")
    history = st.session_state.history
    if not history:
        st.info("이번 세션에 검토한 기록이 없습니다.")
        return

    risk_labels = {"HIGH": "🔴 고위험", "MEDIUM": "🟡 중위험", "LOW": "🟢 저위험"}
    for i, h in enumerate(reversed(history)):
        with st.expander(f"{h['상표명']}  —  {h['작성일']}  |  {risk_labels.get(h['위험도'],'-')}"):
            st.markdown(f"**지정류:** {', '.join(h['지정류'])}")
            st.markdown(f"**상품:** {', '.join(h['상품'])}")
            st.markdown(f"**선행상표:** {h['선행상표수']}건")
            st.text_area("검토 의견", value=h["의견"], height=80, key=f"hist_op_{i}", disabled=True)
            if st.button("이 검토로 이동", key=f"hist_go_{i}"):
                # 해당 케이스 상태 복원
                st.session_state.trademark_name = h["상표명"]
                st.session_state.search_results = h["결과"]
                st.session_state.opinion = h["의견"]
                st.session_state.risk_level = h["위험도"]
                st.session_state.step = 5
                st.session_state.page = "home"
                st.rerun()

    if st.button("🗑️ 히스토리 전체 삭제", type="secondary"):
        st.session_state.history = []
        st.rerun()


# ─────────────────────────────────────────────
# 케이스 관리 페이지
# ─────────────────────────────────────────────
def render_cases():
    st.title("📊 케이스 관리")
    cases = st.session_state.cases
    if not cases:
        st.info("저장된 케이스가 없습니다. STEP 5에서 케이스를 저장하세요.")
        return

    risk_labels = {"HIGH": "🔴 고위험", "MEDIUM": "🟡 중위험", "LOW": "🟢 저위험"}
    df = pd.DataFrame([{
        "ID": c["id"], "상표명": c["상표명"],
        "지정류": ", ".join(c["지정류"]),
        "위험도": risk_labels.get(c["위험도"], "-"),
        "선행상표": f"{c['선행상표수']}건",
        "작성일": c["작성일"],
    } for c in cases])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 전체 CSV 내보내기
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ 전체 케이스 CSV",
        data=csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"케이스목록_{datetime.date.today()}.csv",
        mime="text/csv",
    )

    if st.button("🗑️ 전체 삭제", type="secondary"):
        st.session_state.cases = []
        st.rerun()


# ─────────────────────────────────────────────
# 보고서 관리 페이지
# ─────────────────────────────────────────────
def render_reports():
    st.title("📄 보고서 관리")
    cases = st.session_state.cases
    if not cases:
        st.info("저장된 케이스가 없습니다. 케이스를 먼저 저장하세요.")
        return

    selected_id = st.selectbox(
        "보고서 생성할 케이스 선택",
        options=[c["id"] for c in cases],
        format_func=lambda x: next(f"{c['상표명']} ({c['작성일']})" for c in cases if c["id"] == x),
    )
    case = next(c for c in cases if c["id"] == selected_id)

    # 보고서 미리보기
    st.divider()
    risk_labels = {"HIGH": "고위험 🔴", "MEDIUM": "중위험 🟡", "LOW": "저위험 🟢"}
    st.markdown(f"## 유사성 검토 보고서")
    st.markdown(f"""
| | |
|--|--|
| **상표명** | {case['상표명']} |
| **지정류** | {', '.join(case['지정류'])} |
| **지정상품** | {', '.join(case['상품'])} |
| **위험도** | {risk_labels.get(case['위험도'], '-')} |
| **작성일** | {case['작성일']} |
""")

    if case["결과"]:
        st.markdown(f"### 선행 유사상표 ({len(case['결과'])}건)")
        st.dataframe(pd.DataFrame(case["결과"]), use_container_width=True, hide_index=True)

    st.markdown("### 검토 의견")
    st.info(case["의견"])

    # 다운로드
    report_lines = [
        "=" * 60, "       상표 유사성 검토 보고서", "=" * 60,
        f"검토 상표명 : {case['상표명']}",
        f"지정 류     : {', '.join(case['지정류'])}",
        f"위험도      : {case['위험도']}",
        f"작성일      : {case['작성일']}", "",
        "[검색식]", case["검색식"], "",
        f"[선행상표 ({len(case['결과'])}건)]",
    ]
    for r in case["결과"]:
        report_lines.append(f"  - {r['상표명']} ({r['유사도']}%) {r['출원인']} {r['상태']}")
    report_lines += ["", "[검토 의견]", case["의견"], "", f"({OFFICE_NAME})"]

    st.download_button(
        "📄 TXT 다운로드",
        data="\n".join(report_lines).encode("utf-8"),
        file_name=f"보고서_{case['상표명']}_{case['작성일']}.txt",
        mime="text/plain",
    )


# ─────────────────────────────────────────────
# 설정 페이지
# ─────────────────────────────────────────────
def render_settings():
    st.title("⚙️ 설정")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("사무소 정보")
        office = st.text_input("사무소명", value=os.getenv("OFFICE_NAME", ""))
        st.text_input("KIPRIS API 키", value=os.getenv("KIPRIS_API_KEY", ""),
                      type="password", help=".env 파일에서 설정하세요")

        if st.button("저장 (재시작 필요)"):
            try:
                with open(".env", "w", encoding="utf-8") as f:
                    f.write(f"KIPRIS_API_KEY={os.getenv('KIPRIS_API_KEY','')}\n")
                    f.write(f"OFFICE_NAME={office}\n")
                st.success(".env 파일이 업데이트되었습니다. 앱을 재시작하세요.")
            except Exception as e:
                st.error(f"저장 실패: {e}")

    with col2:
        st.subheader("API 연결 상태")
        api_key = os.getenv("KIPRIS_API_KEY", "").strip()
        if api_key:
            st.success("✅ KIPRIS API 키가 설정되어 있습니다 (실제 검색 모드)")
        else:
            st.warning("⚠️ API 키 없음 — Mock 데이터 모드로 동작 중\n\n.env 파일에 KIPRIS_API_KEY를 설정하세요.")

        st.subheader("현재 세션")
        st.metric("검색 히스토리", f"{len(st.session_state.history)}건")
        st.metric("저장된 케이스", f"{len(st.session_state.cases)}건")


# ─────────────────────────────────────────────
# 사용 가이드 페이지
# ─────────────────────────────────────────────
def render_guide():
    st.title("❓ 사용 가이드")
    st.markdown("""
## 5단계 검토 프로세스

| 단계 | 내용 | 핵심 |
|------|------|------|
| **STEP 1** | 상표명 입력 | 영문/한글/혼합 가능 |
| **STEP 2** | 지정상품 선택 | 검색창에 상품명 입력 → 자동완성 |
| **STEP 3** | 검색식 확인 | 키프리스 검색식 자동 생성 / 직접 수정 가능 |
| **STEP 4** | 유사상표 검색 결과 | 유사도 점수 및 위험도 자동 판단 |
| **STEP 5** | 보고서 작성 | 의견 자동 초안 + TXT 다운로드 |

## 위험도 기준

| 위험도 | 최고 유사도 | 의미 |
|--------|-----------|------|
| 🔴 고위험 | 70% 이상 | 거절 가능성 높음, 상표명 변경 검토 |
| 🟡 중위험 | 50~69% | 의견 제출 준비 권장 |
| 🟢 저위험 | 50% 미만 | 등록 가능성 높음 |

## 테스트 케이스
- **POOKIE + 티셔츠 (25류)** → 중·고위험 결과 확인 가능

## KIPRIS API 연동
1. [키프리스 API 서비스](https://www.kipris.or.kr) 회원가입 후 API 키 발급
2. `.env` 파일에 `KIPRIS_API_KEY=발급받은키` 입력
3. 앱 재시작 → 실제 검색 모드로 전환
""")


# ─────────────────────────────────────────────
# 메인 라우터
# ─────────────────────────────────────────────
page = st.session_state.page

if page == "home":
    render_step_bar(st.session_state.step)
    step = st.session_state.step
    if step == 1:   render_step1()
    elif step == 2: render_step2()
    elif step == 3: render_step3()
    elif step == 4: render_step4()
    elif step == 5: render_step5()

elif page == "history": render_history()
elif page == "cases":   render_cases()
elif page == "reports": render_reports()
elif page == "settings": render_settings()
elif page == "guide":   render_guide()
