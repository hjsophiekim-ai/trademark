from __future__ import annotations

import time
from typing import Iterable, List

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
    page_icon="상",
    layout="wide",
)


DEFAULT_STATE = {
    "step": 1,
    "trademark_name": "",
    "trademark_type": "문자만",
    "is_coined": True,
    "goods_query": "",
    "selected_fields": [],
    "specific_product": "",
    "selected_codes": [],
    "analysis": None,
    "improvements": None,
    "search_source": "",
}


def init_state() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value


def selected_class_numbers() -> List[int]:
    values = []
    for item in st.session_state.selected_fields:
        try:
            values.append(int(str(item["class_no"]).replace("류", "")))
        except ValueError:
            continue
    return sorted(set(values))


def add_field(item: dict) -> None:
    key = (item["class_no"], item["description"])
    current = {(field["class_no"], field["description"]) for field in st.session_state.selected_fields}
    if key not in current:
        st.session_state.selected_fields.append(item)


def remove_field(index: int) -> None:
    st.session_state.selected_fields.pop(index)


def add_code(item: dict) -> None:
    current = {code["code"] for code in st.session_state.selected_codes}
    if item["code"] not in current:
        st.session_state.selected_codes.append(item)


def remove_code(code: str) -> None:
    st.session_state.selected_codes = [item for item in st.session_state.selected_codes if item["code"] != code]


def selected_code_values() -> List[str]:
    return [item["code"] for item in st.session_state.selected_codes]


def selected_field_summary(fields: Iterable[dict]) -> str:
    return ", ".join(f'{field["description"]} ({field["class_no"]})' for field in fields) or "-"


def selected_code_summary(codes: Iterable[dict]) -> str:
    return ", ".join(code["code"] for code in codes) or "-"


def kipris_link(keyword: str) -> str:
    return f"https://www.kipris.or.kr/kportal/search/search_trademark.do?queryText={keyword}"


def render_step1() -> None:
    st.markdown('<div class="app-shell"><div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("### 안녕하세요!")
    st.markdown('<div class="intro-text">등록하고 싶은 상표명을 알려주세요.</div>', unsafe_allow_html=True)

    st.session_state.trademark_name = st.text_input(
        "상표명",
        value=st.session_state.trademark_name,
        placeholder="예) POOKIE, 사랑해, BRAND one",
    )

    st.markdown(
        """
<div class="hint-card">
  <strong>상표란?</strong><br>
  내 브랜드, 회사명, 제품명을 법적으로 보호하는 권리예요.
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

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_catalog_buttons(items: List[dict], prefix: str) -> None:
    for offset in range(0, len(items), 3):
        columns = st.columns(3)
        for index, item in enumerate(items[offset : offset + 3]):
            with columns[index]:
                if st.button(
                    f'{item["description"]} ({item["class_no"]})',
                    key=f'{prefix}_{item["class_no"]}_{item["description"]}',
                ):
                    add_field(item)
                    st.rerun()


def render_step2() -> None:
    name = st.session_state.trademark_name or "입력한 상표"
    st.markdown('<div class="app-shell"><div class="wizard-card">', unsafe_allow_html=True)
    st.markdown(f'### "{name}" 상표를 어떤 분야에 사용하실 예정인가요?')

    st.session_state.goods_query = st.text_input(
        "업종/상품 검색",
        value=st.session_state.goods_query,
        placeholder="예) 가구, 커피, 옷, 앱개발",
    )

    if st.session_state.goods_query.strip():
        st.markdown("#### 입력 즉시 추천되는 분야")
        for item in search_products(st.session_state.goods_query, limit=6):
            left, right = st.columns([7, 1])
            with left:
                st.markdown(
                    f"""
<div class="soft-card">
  <div class="soft-card-title">{item["icon"]} {item["description"]} ({item["class_no"]})</div>
  <div class="small-muted">{item["example"]}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("선택", key=f'search_{item["class_no"]}_{item["description"]}'):
                    add_field(item)
                    st.rerun()

    catalog = get_catalog()
    st.markdown('<div class="catalog-note">또는 전체 목록에서 선택해도 됩니다.</div>', unsafe_allow_html=True)
    goods_tab, services_tab = st.tabs(["상품 1~34류", "서비스 35~45류"])
    with goods_tab:
        render_catalog_buttons(catalog["goods"], "goods")
    with services_tab:
        render_catalog_buttons(catalog["services"], "services")

    if st.session_state.selected_fields:
        st.markdown("#### 선택됨")
        for index, item in enumerate(st.session_state.selected_fields):
            left, right = st.columns([8, 1])
            with left:
                st.markdown(
                    f'<span class="pick-chip">{item["description"]} ({item["class_no"]})</span>',
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("✕", key=f"remove_field_{index}"):
                    remove_field(index)
                    st.rerun()

    left, right = st.columns(2)
    with left:
        if st.button("← 이전"):
            st.session_state.step = 1
            st.rerun()
    with right:
        if st.button("다음 단계로 →", type="primary", disabled=not st.session_state.selected_fields):
            st.session_state.step = 3
            st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_step3() -> None:
    selected_fields = st.session_state.selected_fields
    header = selected_fields[0] if selected_fields else None
    title = f'{header["class_no"]}({header["description"]}) 중에서 어떤 상품인가요?' if header else "어떤 상품인가요?"

    st.markdown('<div class="app-shell"><div class="wizard-card">', unsafe_allow_html=True)
    st.markdown(f"### {title}")

    st.session_state.specific_product = st.text_input(
        "구체적인 상품명 입력",
        value=st.session_state.specific_product,
        placeholder="예) 책상, 소파, 침대, 스킨케어, 카페",
    )

    if st.session_state.specific_product.strip():
        st.markdown("#### 유사군 코드 추천")
        for row in suggest_similarity_codes(st.session_state.specific_product, limit=8):
            badges = []
            if row.get("recommended"):
                badges.append('<span class="recommend-pill">추천</span>')
            if row.get("is_sales"):
                badges.append('<span class="sale-pill">판매업</span>')
            left, right = st.columns([7, 1])
            with left:
                st.markdown(
                    f"""
<div class="soft-card">
  <div class="soft-card-title">{"✅" if row.get("recommended") else "☑️"} {row["code"]} - {row["name"]}</div>
  <div class="small-muted">{row["description"]}</div>
  <div class="small-muted">기준 상품: {row["base_product"]} / 매칭 {int(row["match_score"] * 100)}%</div>
  <div>{''.join(badges)}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("선택", key=f'code_{row["code"]}'):
                    add_code(row)
                    st.rerun()

    st.markdown(
        """
<div class="hint-card">
  <strong>판매업 코드란?</strong><br>
  상품을 판매하는 가게나 쇼핑몰도 같이 보호받을 수 있어요.<br>
  함께 선택하면 보호 범위가 넓어질 수 있습니다.
</div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.selected_codes:
        st.markdown("#### 선택된 코드")
        for row in st.session_state.selected_codes:
            left, right = st.columns([8, 1])
            with left:
                st.markdown(
                    f'<span class="pick-chip">{row["code"]} ({row["name"]})</span>',
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("✕", key=f'remove_code_{row["code"]}'):
                    remove_code(row["code"])
                    st.rerun()

    left, right = st.columns(2)
    with left:
        if st.button("← 이전"):
            st.session_state.step = 2
            st.rerun()
    with right:
        if st.button("검토 시작하기 →", type="primary", disabled=not st.session_state.selected_codes):
            st.session_state.analysis = None
            st.session_state.improvements = None
            st.session_state.step = 4
            st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_analysis_progress(percent: int, lines: List[str]) -> None:
    st.markdown(
        f"""
<div class="soft-card">
  <div class="soft-card-title">검토 중...</div>
  <div class="progress-shell"><div class="progress-fill" style="width:{percent}%;"></div></div>
  <div class="status-list">{'<br>'.join(lines)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def build_report_payload() -> dict:
    analysis = st.session_state.analysis or {}
    improvements = st.session_state.improvements or {"name_options": [], "scope_options": [], "class_options": []}
    return {
        "trademark_name": st.session_state.trademark_name,
        "trademark_type": st.session_state.trademark_type,
        "selected_classes": [f'{field["description"]} ({field["class_no"]})' for field in st.session_state.selected_fields],
        "selected_codes": selected_code_values(),
        "score": analysis.get("score", 0),
        "score_label": analysis.get("band", {}).get("label", "-"),
        "distinctiveness": analysis.get("distinctiveness", "-"),
        "prior_count": analysis.get("prior_count", 0),
        "top_prior": analysis.get("top_prior", []),
        "name_options": improvements.get("name_options", []),
        "scope_options": improvements.get("scope_options", []),
        "class_options": improvements.get("class_options", []),
    }


def run_analysis() -> None:
    progress_placeholder = st.empty()

    with progress_placeholder.container():
        render_analysis_progress(25, ["✅ 식별력 검토 완료", "⏳ 유사군코드 매핑 중", "⏳ KIPRIS 선행상표 검색 대기"])
    time.sleep(0.2)

    with progress_placeholder.container():
        render_analysis_progress(50, ["✅ 식별력 검토 완료", "✅ 유사군코드 매핑 완료", "⏳ KIPRIS 선행상표 검색 중"])
    search_result = kipris_api.search_all_pages(
        st.session_state.trademark_name,
        max_pages=3,
        rows_per_page=10,
    )
    time.sleep(0.2)

    prior_items = search_result.get("items", []) if search_result.get("success") else []
    score_result = evaluate_registration(
        trademark_name=st.session_state.trademark_name,
        trademark_type=st.session_state.trademark_type,
        is_coined=st.session_state.is_coined,
        selected_classes=selected_class_numbers(),
        selected_codes=selected_code_values(),
        prior_items=prior_items,
    )
    improvements = build_improvement_plan(
        trademark_name=st.session_state.trademark_name,
        current_score=score_result["score"],
        selected_codes=selected_code_values(),
        prior_items=score_result["top_prior"],
        selected_fields=st.session_state.selected_fields,
    )

    with progress_placeholder.container():
        render_analysis_progress(100, ["✅ 식별력 검토 완료", "✅ 유사군코드 매핑 완료", "✅ KIPRIS 선행상표 검색 완료"])
    time.sleep(0.25)
    progress_placeholder.empty()

    st.session_state.analysis = {
        **score_result,
        "search_success": bool(search_result.get("success")),
        "search_message": search_result.get("result_msg", ""),
    }
    st.session_state.improvements = improvements
    st.session_state.search_source = "실제 KIPRIS" if not search_result.get("mock") else "Mock 데이터"


def render_step4() -> None:
    st.markdown('<div class="app-shell"><div class="wizard-card">', unsafe_allow_html=True)
    if st.session_state.analysis is None:
        run_analysis()

    analysis = st.session_state.analysis or {}
    style = get_score_style(analysis.get("score", 0))
    st.markdown(f'### "{st.session_state.trademark_name}" 등록 가능성 검토 결과')

    st.markdown(
        f"""
<div class="score-card" style="background:{style["bg"]}; border-color:{style["border"]}; color:{style["text"]};">
  <div class="score-number">{analysis.get("score", 0)}%</div>
  <div class="score-label">{style["label"]}</div>
  <div class="score-bar">
    <div class="score-bar-fill" style="width:{analysis.get("score", 0)}%; background:{style["border"]};"></div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="soft-card">
  <div class="soft-card-title">검토 요약</div>
  <div class="small-muted">상표명: {st.session_state.trademark_name}</div>
  <div class="small-muted">상품군: {selected_field_summary(st.session_state.selected_fields)}</div>
  <div class="small-muted">유사군코드: {selected_code_summary(st.session_state.selected_codes)}</div>
  <div class="small-muted">선행상표: {analysis.get("prior_count", 0)}건 발견</div>
  <div class="small-muted">식별력: {analysis.get("distinctiveness", "-")}</div>
  <div class="small-muted">검색 출처: {st.session_state.search_source}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    if analysis.get("signals"):
        st.markdown("#### 분석 포인트")
        for signal in analysis["signals"]:
            st.markdown(f"- {signal}")

    st.markdown("#### 주요 선행상표")
    top_prior = analysis.get("top_prior", [])
    if not top_prior:
        st.success("직접 충돌 가능성이 높은 선행상표는 크게 보이지 않았습니다.")
    else:
        for index, item in enumerate(top_prior, start=1):
            similarity = item.get("similarity", 0)
            level = "high" if similarity >= 80 else "medium" if similarity >= 60 else "low"
            st.markdown(
                f"""
<div class="prior-card {level}">
  <strong>{index}. {item.get("trademarkName", "-")}</strong><br>
  {item.get("registerStatus", "-")} | {item.get("classificationCode", "-")}류 | 유사도 {similarity}%<br>
  출원인: {item.get("applicantName", "-")}
</div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("KIPRIS에서 보기 →", kipris_link(item.get("trademarkName", "")))

    if not analysis.get("search_success"):
        st.warning(f'KIPRIS 검색 오류: {analysis.get("search_message", "알 수 없는 오류")}')

    left, middle, right = st.columns(3)
    with left:
        if st.button("등록 가능성 높이기 →", type="primary"):
            st.session_state.step = 5
            st.rerun()
    with middle:
        st.download_button(
            "PDF 보고서 받기",
            data=generate_report_pdf(build_report_payload()),
            file_name=f'{st.session_state.trademark_name}_검토보고서.pdf',
            mime="application/pdf",
        )
    with right:
        if st.button("처음부터 다시"):
            reset_all()
            st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_step5() -> None:
    analysis = st.session_state.analysis or {}
    improvements = st.session_state.improvements or {"name_options": [], "scope_options": [], "class_options": []}
    current_score = analysis.get("score", 0)

    st.markdown('<div class="app-shell"><div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("### 등록 가능성을 높이는 방법")

    st.markdown('<div class="improve-card"><div class="method-tag">방법 1</div>', unsafe_allow_html=True)
    st.markdown(f"**현재:** {st.session_state.trademark_name} ({current_score}%)")
    for option in improvements["name_options"]:
        st.markdown(f"- {option['name']} → 예상 {option['expected_score']}%")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="improve-card"><div class="method-tag">방법 2</div>', unsafe_allow_html=True)
    st.markdown(f"**현재 코드:** {selected_code_summary(st.session_state.selected_codes)} ({current_score}%)")
    for option in improvements["scope_options"]:
        st.markdown(f"- {option['title']} → 예상 {option['expected_score']}%")
        st.caption(option["description"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="improve-card"><div class="method-tag">방법 3</div>', unsafe_allow_html=True)
    for option in improvements["class_options"]:
        st.markdown(f"- {option['title']} → 예상 {option['expected_score']}%")
        st.caption(option["description"])
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
            file_name=f'{st.session_state.trademark_name}_전체보고서.pdf',
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

    st.markdown("</div></div>", unsafe_allow_html=True)


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
