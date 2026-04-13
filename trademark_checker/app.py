from __future__ import annotations

import time
from typing import List

import streamlit as st

import kipris_api
from improvement import build_improvement_plan
from report_generator import generate_report_pdf
from scoring import evaluate_registration
from search_mapper import get_catalog, search_products
from similarity_code_db import suggest_similarity_codes
from styles import apply_styles, get_score_style, render_header


st.set_page_config(
    page_title="상표등록 가능성 검토 서비스",
    page_icon="🛡️",
    layout="wide",
)


def init_state() -> None:
    defaults = {
        "step": 1,
        "trademark_name": "",
        "trademark_type": "문자만",
        "is_coined": True,
        "selected_fields": [],
        "goods_query": "",
        "specific_product": "",
        "selected_codes": [],
        "analysis": None,
        "improvements": None,
        "top_prior": [],
        "search_source": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all() -> None:
    st.session_state.step = 1
    st.session_state.trademark_name = ""
    st.session_state.trademark_type = "문자만"
    st.session_state.is_coined = True
    st.session_state.selected_fields = []
    st.session_state.goods_query = ""
    st.session_state.specific_product = ""
    st.session_state.selected_codes = []
    st.session_state.analysis = None
    st.session_state.improvements = None
    st.session_state.top_prior = []
    st.session_state.search_source = ""


def selected_classes() -> List[int]:
    classes = []
    for item in st.session_state.selected_fields:
        try:
            classes.append(int(str(item["류"]).replace("류", "")))
        except ValueError:
            continue
    return sorted(set(classes))


def add_field(item: dict) -> None:
    key = (item["류"], item["설명"])
    current_keys = {(row["류"], row["설명"]) for row in st.session_state.selected_fields}
    if key not in current_keys:
        st.session_state.selected_fields.append(item)


def add_code(code: str) -> None:
    if code not in st.session_state.selected_codes:
        st.session_state.selected_codes.append(code)


def remove_code(code: str) -> None:
    st.session_state.selected_codes = [item for item in st.session_state.selected_codes if item != code]


def kipris_link(keyword: str) -> str:
    return f"https://www.kipris.or.kr/kportal/search/search_trademark.do?queryText={keyword}"


def render_step1() -> None:
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("### 안녕하세요!")
    st.markdown("등록하고 싶은 상표명을 알려주세요.")

    st.session_state.trademark_name = st.text_input(
        "상표명",
        value=st.session_state.trademark_name,
        placeholder="예) POOKIE, 사랑해, BRAND one",
    )

    st.markdown(
        """
<div class="hint-card">
  <strong>상표란?</strong><br>
  내 브랜드·회사명·제품명을 법적으로 보호하는 권리예요.
</div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.trademark_type = st.radio(
        "상표 유형",
        ["문자만", "문자+로고", "로고만"],
        index=["문자만", "문자+로고", "로고만"].index(st.session_state.trademark_type),
        horizontal=True,
    )

    coined_answer = st.radio(
        "새로 만든 단어인가요? (조어상표)",
        ["네, 새로 만든 단어예요", "아니요, 기존 단어예요"],
        index=0 if st.session_state.is_coined else 1,
    )
    st.session_state.is_coined = coined_answer.startswith("네")

    if st.button("다음 단계로 →", type="primary", disabled=not st.session_state.trademark_name.strip()):
        st.session_state.step = 2
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_step2() -> None:
    name = st.session_state.trademark_name or "입력한 상표"
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown(f'### "{name}" 상표를 어떤 분야에 사용하실 예정인가요?')

    st.session_state.goods_query = st.text_input(
        "업종/상품 검색",
        value=st.session_state.goods_query,
        placeholder="예) 가구, 커피, 옷, 앱개발",
    )

    if st.session_state.goods_query.strip():
        st.markdown("#### 추천 분야")
        for item in search_products(st.session_state.goods_query, limit=6):
            left, right = st.columns([6, 1])
            with left:
                st.markdown(
                    f"""
<div class="soft-card">
  <strong>{item["아이콘"]} {item["설명"]} ({item["류"]})</strong><br>
  <span class="small-muted">{item["예시"]}</span>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("선택", key=f'field_{item["류"]}_{item["설명"]}'):
                    add_field(item)
                    st.rerun()

    catalog = get_catalog()
    goods_tab, services_tab = st.tabs(["상품 1~34류", "서비스 35~45류"])
    with goods_tab:
        for item in catalog["goods"][:12]:
            if st.button(f'{item["설명"]} ({item["류"]})', key=f'goods_{item["류"]}_{item["설명"]}'):
                add_field(item)
                st.rerun()
    with services_tab:
        for item in catalog["services"][:12]:
            if st.button(f'{item["설명"]} ({item["류"]})', key=f'services_{item["류"]}_{item["설명"]}'):
                add_field(item)
                st.rerun()

    if st.session_state.selected_fields:
        st.markdown("#### 선택됨")
        for index, item in enumerate(st.session_state.selected_fields):
            col1, col2 = st.columns([8, 1])
            with col1:
                st.markdown(f'<span class="pick-chip">{item["설명"]} ({item["류"]})</span>', unsafe_allow_html=True)
            with col2:
                if st.button("✕", key=f"remove_field_{index}"):
                    st.session_state.selected_fields.pop(index)
                    st.rerun()

    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← 이전"):
            st.session_state.step = 1
            st.rerun()
    with next_col:
        if st.button("다음 단계로 →", type="primary", disabled=not st.session_state.selected_fields):
            st.session_state.step = 3
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_step3() -> None:
    classes = selected_classes()
    title = ", ".join(f"{cls}류" for cls in classes) if classes else "선택한 류"
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown(f"### {title} 중에서 어떤 상품인가요?")

    st.session_state.specific_product = st.text_input(
        "구체적인 상품명 입력",
        value=st.session_state.specific_product,
        placeholder="예) 책상, 소파, 스킨케어, 카페",
    )

    if st.session_state.specific_product.strip():
        st.markdown("#### 유사군 코드 추천")
        for row in suggest_similarity_codes(st.session_state.specific_product, limit=8):
            tags = []
            if row.get("추천"):
                tags.append("추천")
            if row.get("판매업"):
                tags.append("판매업")
            st.markdown(
                f"""
<div class="soft-card">
  <strong>{'✅' if row.get("추천") else '☑️'} {row["code"]} - {row["name"]}</strong><br>
  <span class="small-muted">{row["설명"]}</span><br>
  <span class="small-muted">기준 상품: {row["기준상품"]} / 매칭 {int(row["매칭점수"] * 100)}%</span><br>
  <span class="small-muted">{' · '.join(tags)}</span>
</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f'{row["code"]} 선택', key=f'code_{row["code"]}'):
                add_code(row["code"])
                st.rerun()

    st.markdown(
        """
<div class="hint-card">
  <strong>판매업 코드란?</strong><br>
  상품을 판매하는 가게·쇼핑몰도 같이 보호받을 수 있어요. 함께 선택하면 보호 범위가 넓어집니다.
</div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.selected_codes:
        st.markdown("#### 선택된 코드")
        for code in list(st.session_state.selected_codes):
            col1, col2 = st.columns([8, 1])
            with col1:
                st.markdown(f'<span class="pick-chip">{code}</span>', unsafe_allow_html=True)
            with col2:
                if st.button("✕", key=f"remove_code_{code}"):
                    remove_code(code)
                    st.rerun()

    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← 이전"):
            st.session_state.step = 2
            st.rerun()
    with next_col:
        if st.button("검토 시작하기 →", type="primary", disabled=not st.session_state.selected_codes):
            st.session_state.analysis = None
            st.session_state.improvements = None
            st.session_state.step = 4
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def run_analysis() -> None:
    progress = st.progress(0)
    status = st.empty()

    status.markdown("검토 중... 식별력 검토를 시작합니다.")
    time.sleep(0.2)
    progress.progress(25)

    status.markdown("유사군 코드 매핑을 확인하고 있습니다.")
    time.sleep(0.2)
    progress.progress(50)

    status.markdown("KIPRIS 선행상표 검색 중입니다.")
    search_result = kipris_api.search_all_pages(
        st.session_state.trademark_name,
        max_pages=3,
        rows_per_page=10,
    )
    progress.progress(80)

    prior_items = search_result.get("items", []) if search_result.get("success", False) else []
    score_result = evaluate_registration(
        trademark_name=st.session_state.trademark_name,
        trademark_type=st.session_state.trademark_type,
        is_coined=st.session_state.is_coined,
        selected_classes=selected_classes(),
        selected_codes=st.session_state.selected_codes,
        prior_items=prior_items,
    )
    improvements = build_improvement_plan(
        trademark_name=st.session_state.trademark_name,
        current_score=score_result["score"],
        selected_codes=st.session_state.selected_codes,
        prior_items=score_result["top_prior"],
    )

    progress.progress(100)
    status.markdown("검토가 완료되었습니다.")

    st.session_state.analysis = {**score_result, "prior_items": prior_items}
    st.session_state.improvements = improvements
    st.session_state.top_prior = score_result["top_prior"]
    st.session_state.search_source = "실제 KIPRIS" if not search_result.get("mock") else "Mock 데이터"
    time.sleep(0.3)
    progress.empty()
    status.empty()


def build_report_payload() -> dict:
    analysis = st.session_state.analysis or {}
    improvements = st.session_state.improvements or {"name_options": [], "scope_options": []}
    return {
        "trademark_name": st.session_state.trademark_name,
        "trademark_type": st.session_state.trademark_type,
        "selected_classes": [item["류"] for item in st.session_state.selected_fields],
        "selected_codes": st.session_state.selected_codes,
        "score": analysis.get("score", 0),
        "score_label": analysis.get("band", {}).get("label", "-"),
        "distinctiveness": analysis.get("distinctiveness", "-"),
        "prior_count": analysis.get("prior_count", 0),
        "top_prior": analysis.get("top_prior", []),
        "name_options": improvements.get("name_options", []),
        "scope_options": improvements.get("scope_options", []),
    }


def render_step4() -> None:
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    if st.session_state.analysis is None:
        run_analysis()

    analysis = st.session_state.analysis
    style = get_score_style(analysis["score"])
    st.markdown(f'### "{st.session_state.trademark_name}" 등록 가능성 검토 결과')
    st.markdown(
        f"""
<div class="score-card" style="background:{style['bg']}; border-color:{style['border']}; color:{style['text']};">
  <div class="score-number">{analysis["score"]}%</div>
  <div class="score-label">{analysis["band"]["label"]}</div>
  <div class="score-bar"><div class="score-bar-fill" style="width:{analysis["score"]}%; background:{style["border"]};"></div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    summary_classes = ", ".join(item["류"] for item in st.session_state.selected_fields)
    st.markdown(
        f"""
<div class="soft-card">
  <strong>검토 요약</strong><br>
  상표명: {st.session_state.trademark_name}<br>
  상품군: {summary_classes}<br>
  유사군코드: {', '.join(st.session_state.selected_codes)}<br>
  선행상표: {analysis["prior_count"]}건 발견<br>
  식별력: {analysis["distinctiveness"]}<br>
  검색출처: {st.session_state.search_source}
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 주요 선행상표")
    if not analysis["top_prior"]:
        st.success("확인된 주요 선행상표가 없습니다.")
    else:
        for idx, item in enumerate(analysis["top_prior"], start=1):
            level = "high" if item["similarity"] >= 80 else "medium" if item["similarity"] >= 60 else "low"
            st.markdown(
                f"""
<div class="prior-card {level}">
  <strong>{idx}. {item.get("trademarkName", "-")}</strong><br>
  {item.get("registerStatus", "-")} │ {item.get("classificationCode", "-")} │ 유사도 {item["similarity"]}%<br>
  출원인: {item.get("applicantName", "-")}
</div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("KIPRIS에서 보기 →", kipris_link(item.get("trademarkName", "")))

    next_col, pdf_col, reset_col = st.columns(3)
    with next_col:
        if st.button("등록 가능성 높이기 →", type="primary"):
            st.session_state.step = 5
            st.rerun()
    with pdf_col:
        st.download_button(
            "PDF 보고서 받기",
            data=generate_report_pdf(build_report_payload()),
            file_name=f"상표검토_{st.session_state.trademark_name}.pdf",
            mime="application/pdf",
        )
    with reset_col:
        if st.button("처음부터 다시"):
            reset_all()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_step5() -> None:
    analysis = st.session_state.analysis or {}
    improvements = st.session_state.improvements or {"name_options": [], "scope_options": []}
    current_score = analysis.get("score", 0)

    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("### 등록 가능성을 높이는 방법")

    st.markdown('<div class="improve-card"><div class="method-tag">방법 1</div>', unsafe_allow_html=True)
    st.markdown(f"**현재:** {st.session_state.trademark_name} ({current_score}%)")
    for item in improvements["name_options"]:
        st.markdown(f"- {item['name']} → 예상 {item['expected_score']}%")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="improve-card"><div class="method-tag">방법 2</div>', unsafe_allow_html=True)
    st.markdown(f"**현재 코드:** {', '.join(st.session_state.selected_codes)} ({current_score}%)")
    if improvements["scope_options"]:
        for item in improvements["scope_options"]:
            st.markdown(f"- {item['title']} → 예상 {item['expected_score']}%")
            st.caption(item["description"])
    else:
        st.markdown("- 현재 선택 범위가 비교적 안정적입니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="improve-card"><div class="method-tag">방법 3</div>', unsafe_allow_html=True)
    st.markdown("- 판매업 코드와 상품 코드를 분리해 우선 출원 대상을 좁혀 보세요.")
    st.markdown("- 로고 결합 또는 새 조어 조합으로 식별력을 올려 보세요.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="disclaimer">
  <strong>면책조항</strong><br>
  본 결과는 AI 분석 참고용이며 최종 판단은 변리사와 상담하세요.
</div>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns(3)
    with left:
        st.download_button(
            "전체 보고서 PDF 받기",
            data=generate_report_pdf(build_report_payload()),
            file_name=f"상표검토_{st.session_state.trademark_name}_전체.pdf",
            mime="application/pdf",
        )
    with middle:
        if st.button("검토 결과로 돌아가기"):
            st.session_state.step = 4
            st.rerun()
    with right:
        if st.button("처음부터 다시", type="primary"):
            reset_all()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    init_state()
    apply_styles()
    render_header(st.session_state.step)

    if st.session_state.step == 1:
        render_step1()
    elif st.session_state.step == 2:
        render_step2()
    elif st.session_state.step == 3:
        render_step3()
    elif st.session_state.step == 4:
        render_step4()
    else:
        render_step5()


if __name__ == "__main__":
    main()
