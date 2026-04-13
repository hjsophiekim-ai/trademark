import re
import time

import pandas as pd
import streamlit as st

from improvement import get_improvements
from kipris_api import search_all_pages
from scoring import calculate_score, similarity_percent, strip_html
from search_mapper import get_category_suggestions
from similarity_code_db import get_all_codes_by_class, get_similarity_codes


def reset_session() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_result_style(score: int) -> tuple[str, str, str]:
    if score >= 90:
        return "result-90", "", "등록 가능성 매우 높음"
    if score >= 70:
        return "result-70", "", "등록 가능성 높음"
    if score >= 50:
        return "result-50", "", "주의 필요 - 전문가 상담 권장"
    if score >= 30:
        return "result-30", "", "등록 어려움 - 변리사 상담 필요"
    return "result-0", "⛔", "등록 불가 가능성 높음"


def normalize_result(item: dict, trademark_name: str) -> dict:
    name = strip_html(item.get("trademarkName", item.get("trademark_name", "알 수 없음")))
    similarity = similarity_percent(trademark_name, name)
    return {
        "trademarkName": name,
        "applicationNumber": item.get("applicationNumber", item.get("application_number", "-")),
        "applicationDate": item.get("applicationDate", item.get("application_date", "-")),
        "registerStatus": item.get("registerStatus", item.get("registrationStatus", item.get("status", "-"))),
        "applicantName": strip_html(item.get("applicantName", item.get("applicant", "-"))),
        "classificationCode": item.get("classificationCode", item.get("class", "-")),
        "similarity": similarity,
    }


def deduplicate_results(items: list[dict], trademark_name: str) -> list[dict]:
    seen = set()
    results = []
    for item in items:
        normalized = normalize_result(item, trademark_name)
        key = (normalized["applicationNumber"], normalized["trademarkName"])
        if key in seen:
            continue
        seen.add(key)
        results.append(normalized)
    results.sort(key=lambda row: row["similarity"], reverse=True)
    return results


def similarity_cell_style(value) -> str:
    try:
        numeric = int(str(value).replace("%", ""))
    except ValueError:
        return ""
    if numeric >= 70:
        return "background-color: #FFEBEE; color: #B71C1C; font-weight: bold;"
    if numeric >= 50:
        return "background-color: #FFF3E0; color: #E65100; font-weight: bold;"
    return "background-color: #E8F5E9; color: #2E7D32;"


st.set_page_config(
    page_title="상표등록 가능성 검토",
    page_icon="",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { background-color: #F0F8FF; }
    .main-header {
        background: linear-gradient(135deg, #1565C0, #2196F3);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
    }
    .step-bar {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 16px 0;
        flex-wrap: wrap;
    }
    .step-active {
        background: #2196F3;
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .step-done {
        background: #4CAF50;
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
    }
    .step-todo {
        background: #B0BEC5;
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
    }
    .card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(33,150,243,0.1);
        border-left: 4px solid #2196F3;
        margin-bottom: 16px;
    }
    .category-card {
        background: #E3F2FD;
        border: 2px solid #90CAF9;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .code-card {
        background: #F8FBFF;
        border: 1px solid #90CAF9;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .code-recommended {
        border-color: #2196F3;
        border-width: 2px;
        background: #E3F2FD;
    }
    .code-sales {
        border-color: #66BB6A;
        background: #F1F8E9;
    }
    .result-90 { background:#E8F5E9; border:3px solid #4CAF50; border-radius:12px; padding:20px; text-align:center; }
    .result-70 { background:#E3F2FD; border:3px solid #2196F3; border-radius:12px; padding:20px; text-align:center; }
    .result-50 { background:#FFF3E0; border:3px solid #FF9800; border-radius:12px; padding:20px; text-align:center; }
    .result-30 { background:#FFEBEE; border:3px solid #F44336; border-radius:12px; padding:20px; text-align:center; }
    .result-0  { background:#B71C1C; border:3px solid #7F0000; border-radius:12px; padding:20px; text-align:center; color:white; }
    .trademark-high { background:#FFEBEE; border-left:4px solid #F44336; border-radius:8px; padding:14px; margin:8px 0; }
    .trademark-medium { background:#FFF3E0; border-left:4px solid #FF9800; border-radius:8px; padding:14px; margin:8px 0; }
    .trademark-low { background:#E8F5E9; border-left:4px solid #4CAF50; border-radius:8px; padding:14px; margin:8px 0; }
    .stButton>button {
        background: linear-gradient(135deg, #1976D2, #2196F3);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 16px;
        font-weight: bold;
        white-space: pre-wrap;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #1565C0, #1976D2);
        color: white;
    }
    .tip-box {
        background: #E8F4FD;
        border: 1px solid #90CAF9;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        color: #1565C0;
        margin: 8px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

if "step" not in st.session_state:
    st.session_state.step = 1
if "trademark_name" not in st.session_state:
    st.session_state.trademark_name = ""
if "trademark_type" not in st.session_state:
    st.session_state.trademark_type = "문자만"
if "is_coined" not in st.session_state:
    st.session_state.is_coined = False
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "specific_keyword" not in st.session_state:
    st.session_state.specific_keyword = ""
if "selected_codes" not in st.session_state:
    st.session_state.selected_codes = []
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "score" not in st.session_state:
    st.session_state.score = None

st.markdown(
    """
<div class="main-header">
    <h1 style="margin:0; font-size:28px;">상표등록 가능성 검토</h1>
    <p style="margin:4px 0 0 0; opacity:0.9;">내 브랜드를 법적으로 보호하세요</p>
</div>
""",
    unsafe_allow_html=True,
)


def render_steps(current: int) -> None:
    steps = ["① 상표명", "② 상품선택", "③ 유사군코드", "④ 검토결과", "⑤ 개선방안"]
    html = '<div class="step-bar">'
    for index, label in enumerate(steps, 1):
        if index < current:
            html += f'<span class="step-done">✓ {label}</span>'
        elif index == current:
            html += f'<span class="step-active">{label}</span>'
        else:
            html += f'<span class="step-todo">{label}</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


render_steps(st.session_state.step)
st.markdown("---")


if st.session_state.step == 1:
    st.markdown("## 안녕하세요!")
    st.markdown("### 등록하고 싶은 상표명을 알려주세요")

    st.markdown(
        """
    <div class="tip-box">
    <b>상표란?</b> 내 브랜드·회사명·제품명을 법적으로 보호하는 권리예요.<br>
    상표를 등록하면 다른 사람이 같은 이름을 쓰지 못하게 막을 수 있어요!
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input(
            "상표명 입력",
            placeholder="예) POOKIE, 사랑해, BRAND ONE, 달빛커피...",
            value=st.session_state.trademark_name,
            label_visibility="collapsed",
        )

    st.markdown("#### 상표 유형을 선택해주세요")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("문자만\n(텍스트 상표)", use_container_width=True):
            st.session_state.trademark_type = "문자만"
    with col2:
        if st.button("문자 + 로고\n(결합 상표)", use_container_width=True):
            st.session_state.trademark_type = "문자+로고"
    with col3:
        if st.button("로고만\n(도형 상표)", use_container_width=True):
            st.session_state.trademark_type = "로고만"

    st.markdown(f"선택됨: **{st.session_state.trademark_type}**")

    st.markdown("#### 새로 만든 단어인가요?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 네, 새로 만든 단어예요\n(조어상표 - 등록에 유리!)", use_container_width=True):
            st.session_state.is_coined = True
    with col2:
        if st.button("아니요, 기존 단어예요\n(일반단어)", use_container_width=True):
            st.session_state.is_coined = False

    st.markdown(
        """
    <div class="tip-box">
    <b>조어상표란?</b> 기존에 없던 새로운 단어로 만든 상표예요.<br>
    예) KAKAO, NAVER, COUPANG → 등록 가능성이 높아져요!
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button("다음 단계로 → 상품 선택", use_container_width=True, type="primary"):
        if name.strip():
            st.session_state.trademark_name = name.strip()
            st.session_state.step = 2
            st.rerun()
        st.error("상표명을 입력해주세요!")

elif st.session_state.step == 2:
    st.markdown(f"## '{st.session_state.trademark_name}' 상표를")
    st.markdown("### 어떤 분야에 사용하실 예정인가요?")

    st.markdown(
        """
    <div class="tip-box">
    상표는 반드시 <b>사용할 상품/서비스 분야</b>를 지정해서 등록해야 해요.<br>
    아래에서 업종을 검색하거나 직접 선택해주세요.
    </div>
    """,
        unsafe_allow_html=True,
    )

    search_keyword = st.text_input(
        "업종/상품 검색",
        placeholder="예) 가구, 커피, 옷, 화장품, 앱개발, 음식점...",
        label_visibility="collapsed",
    )

    if search_keyword:
        suggestions = get_category_suggestions(search_keyword, limit=6)
        if suggestions:
            st.markdown("#### 추천 상품/서비스 분야")
            for index, sug in enumerate(suggestions):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(
                        f"""
                    <div class="category-card">
                        <b>{sug['아이콘']} {sug['설명']} ({sug['류']})</b><br>
                        <small style="color:#546E7A">예시: {sug['예시']}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("선택", key=f"sel_{index}_{sug['류']}"):
                        st.session_state.selected_category = sug
                        st.session_state.step = 3
                        st.rerun()
        else:
            st.warning("검색 결과가 없어요. 아래 전체 목록에서 선택해주세요.")

    st.markdown("---")
    st.markdown("#### 전체 목록에서 직접 선택")

    all_categories = {
        "상품": [
            {"류": "3류", "설명": "화장품/향수/세제", "예시": "스킨케어, 향수, 샴푸", "아이콘": "💄"},
            {"류": "5류", "설명": "의약품/건강기능식품", "예시": "영양제, 건강식품", "아이콘": "💊"},
            {"류": "9류", "설명": "전자기기/소프트웨어", "예시": "스마트폰, 앱, 컴퓨터", "아이콘": "📱"},
            {"류": "14류", "설명": "귀금속/시계/보석", "예시": "반지, 목걸이, 시계", "아이콘": "⌚"},
            {"류": "16류", "설명": "종이/문구/출판물", "예시": "노트, 책, 달력", "아이콘": "📚"},
            {"류": "18류", "설명": "가방/지갑/가죽제품", "예시": "핸드백, 백팩, 지갑", "아이콘": "👜"},
            {"류": "20류", "설명": "가구/인테리어", "예시": "소파, 침대, 책상", "아이콘": "🪑"},
            {"류": "21류", "설명": "주방용품/생활용품", "예시": "컵, 냄비, 칫솔", "아이콘": "🍽️"},
            {"류": "25류", "설명": "의류/신발/모자", "예시": "티셔츠, 운동화, 모자", "아이콘": "👕"},
            {"류": "28류", "설명": "완구/스포츠용품", "예시": "장난감, 게임기, 운동용품", "아이콘": "🎮"},
            {"류": "29류", "설명": "가공식품", "예시": "육류, 유제품, 김치", "아이콘": "🥩"},
            {"류": "30류", "설명": "커피/빵/과자/음료", "예시": "커피, 빵, 과자, 라면", "아이콘": "☕"},
            {"류": "32류", "설명": "음료/맥주", "예시": "탄산음료, 주스, 맥주", "아이콘": "🥤"},
            {"류": "33류", "설명": "주류(소주/와인)", "예시": "소주, 와인, 위스키", "아이콘": "🍷"},
        ],
        "서비스": [
            {"류": "35류", "설명": "광고/소매업/쇼핑몰", "예시": "온라인쇼핑몰, 편의점", "아이콘": "🛍️"},
            {"류": "36류", "설명": "금융/보험/부동산", "예시": "은행, 보험, 증권", "아이콘": "🏢"},
            {"류": "37류", "설명": "건설/수리/인테리어", "예시": "건설, 인테리어, 수리", "아이콘": "🏠"},
            {"류": "38류", "설명": "통신/인터넷/방송", "예시": "통신서비스, SNS", "아이콘": "📡"},
            {"류": "39류", "설명": "운송/여행/물류", "예시": "택배, 여행사, 항공", "아이콘": "✈️"},
            {"류": "41류", "설명": "교육/엔터테인먼트", "예시": "학원, 게임, 공연", "아이콘": "📘"},
            {"류": "42류", "설명": "IT/개발/디자인", "예시": "앱개발, 클라우드", "아이콘": "💻"},
            {"류": "43류", "설명": "음식점/카페/숙박", "예시": "식당, 카페, 호텔", "아이콘": "🍽️"},
            {"류": "44류", "설명": "의료/미용/헬스케어", "예시": "병원, 미용실", "아이콘": "🩺"},
            {"류": "45류", "설명": "법률/보안/개인서비스", "예시": "법률, 변리사", "아이콘": "⚖️"},
        ],
    }

    tab1, tab2 = st.tabs(["상품류 (1~34류)", "서비스류 (35~45류)"])
    with tab1:
        cols = st.columns(2)
        for index, cat in enumerate(all_categories["상품"]):
            with cols[index % 2]:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(
                        f"""
                    <div class="category-card">
                        <b>{cat['아이콘']} {cat['설명']}</b> <small>({cat['류']})</small><br>
                        <small style="color:#546E7A">{cat['예시']}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col_b:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("선택", key=f"goods_{cat['류']}"):
                        st.session_state.selected_category = cat
                        st.session_state.step = 3
                        st.rerun()

    with tab2:
        cols = st.columns(2)
        for index, cat in enumerate(all_categories["서비스"]):
            with cols[index % 2]:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(
                        f"""
                    <div class="category-card">
                        <b>{cat['아이콘']} {cat['설명']}</b> <small>({cat['류']})</small><br>
                        <small style="color:#546E7A">{cat['예시']}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col_b:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("선택", key=f"service_{cat['류']}"):
                        st.session_state.selected_category = cat
                        st.session_state.step = 3
                        st.rerun()

    if st.button("← 이전 단계로"):
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 3:
    category = st.session_state.selected_category
    st.markdown(f"## **{category['설명']} ({category['류']})** 중에서")
    st.markdown("### 구체적으로 어떤 상품/서비스인가요?")

    st.markdown(
        """
    <div class="tip-box">
    <b>유사군코드란?</b> 비슷한 상품끼리 묶은 분류 코드예요.<br>
    코드가 같은 상표끼리 서로 충돌할 수 있어요. 정확히 선택할수록 검토가 정확해져요!
    </div>
    """,
        unsafe_allow_html=True,
    )

    specific_keyword = st.text_input(
        "구체적인 상품명 입력",
        placeholder=f"예) {category['예시'].split(',')[0].strip()}...",
        value=st.session_state.specific_keyword,
        label_visibility="collapsed",
    )
    st.session_state.specific_keyword = specific_keyword

    if specific_keyword:
        codes = get_similarity_codes(specific_keyword, category["류"])
        if codes:
            st.markdown("#### 추천 유사군코드")
            selected = st.session_state.selected_codes.copy()
            for code_info in codes:
                col1, col2 = st.columns([5, 1])
                badge = ""
                card_class = "code-card"
                if code_info.get("추천"):
                    badge = "⭐ 추천"
                    card_class = "code-card code-recommended"
                if code_info.get("판매업"):
                    badge = "판매업 코드"
                    card_class = "code-card code-sales"

                with col1:
                    st.markdown(
                        f"""
                    <div class="{card_class}">
                        <b>{badge} {code_info['code']}</b> - {code_info['name']}<br>
                        <small style="color:#546E7A">{code_info['설명']}</small>
                        {"<br><small style='color:#2E7D32'>판매업도 함께 보호받으려면 이 코드도 선택하세요!</small>" if code_info.get("판매업") else ""}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    is_selected = code_info["code"] in selected
                    label = "✓ 선택됨" if is_selected else "선택"
                    if st.button(label, key=f"code_{code_info['code']}"):
                        if is_selected:
                            selected.remove(code_info["code"])
                        else:
                            selected.append(code_info["code"])
                        st.session_state.selected_codes = selected
                        st.rerun()
        else:
            st.info("직접 유사군코드를 선택해주세요.")

        if not codes:
            all_codes = get_all_codes_by_class(category["류"])
            selected = st.session_state.selected_codes.copy()
            for code_info in all_codes:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(
                        f"""
                    <div class="code-card">
                        <b>{code_info['code']}</b> - {code_info['name']}<br>
                        <small>{code_info['설명']}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("선택", key=f"all_code_{code_info['code']}"):
                        if code_info["code"] not in selected:
                            selected.append(code_info["code"])
                        st.session_state.selected_codes = selected
                        st.rerun()

        if st.session_state.selected_codes:
            st.markdown("#### 선택된 유사군코드")
            st.markdown(" ".join([f"**{code}**" for code in st.session_state.selected_codes]))
            if st.button("검토 시작하기!", use_container_width=True, type="primary"):
                st.session_state.step = 4
                st.rerun()

    if st.button("← 이전 단계로"):
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 4:
    if st.session_state.search_results is None:
        st.markdown("## 검토 중입니다...")
        progress = st.progress(0)
        status = st.empty()

        status.markdown("✅ 식별력 검토 중...")
        progress.progress(25)
        time.sleep(0.4)

        status.markdown("✅ 유사군코드 매핑 완료...")
        progress.progress(50)
        time.sleep(0.4)

        status.markdown("🔎 KIPRIS 선행상표 검색 중...")
        all_results = []
        for code in st.session_state.selected_codes:
            result = search_all_pages(st.session_state.trademark_name, similar_goods_code=code, max_pages=3)
            if result and result.get("items"):
                all_results.extend(result["items"])

        if not all_results:
            fallback = search_all_pages(st.session_state.trademark_name, max_pages=3)
            if fallback and fallback.get("items"):
                all_results.extend(fallback["items"])

        progress.progress(75)
        status.markdown("✅ 유사도 분석 중...")
        unique_results = deduplicate_results(all_results, st.session_state.trademark_name)
        st.session_state.search_results = unique_results
        st.session_state.score = calculate_score(
            st.session_state.trademark_name,
            unique_results,
            st.session_state.is_coined,
            st.session_state.trademark_type,
        )

        progress.progress(100)
        status.markdown("✅ 검토 완료!")
        time.sleep(0.5)
        st.rerun()

    score = st.session_state.score
    results = st.session_state.search_results or []
    css_class, emoji, label = get_result_style(score)
    color = "#FFFFFF" if score < 30 else "#2E7D32" if score >= 90 else "#1565C0" if score >= 70 else "#E65100" if score >= 50 else "#B71C1C"

    st.markdown(f"## **'{st.session_state.trademark_name}'** 등록 가능성 검토 결과")
    st.markdown(
        f"""
        <div class="{css_class}">
            <h1 style="font-size:64px; margin:0; color:{color};">{score}%</h1>
            <h2 style="margin:8px 0; color:{color};">{emoji} {label}</h2>
            <p style="color:{color}; margin:0;">상표명: <b>{st.session_state.trademark_name}</b> |
            상품: <b>{st.session_state.selected_category['설명']}</b> |
            코드: <b>{', '.join(st.session_state.selected_codes)}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 검색 건수", f"{len(results)}건")
    with col2:
        high_risk = sum(1 for row in results if row.get("similarity", 0) >= 70)
        st.metric("주의 선행상표", f"{high_risk}건")
    with col3:
        st.metric("조어상표 여부", "예" if st.session_state.is_coined else "아니오")
    with col4:
        st.metric("검색된 유사군코드", f"{len(st.session_state.selected_codes)}개")

    if results:
        st.markdown("---")
        st.markdown("### 주요 선행상표 목록")
        for index, item in enumerate(results[:10]):
            similarity = item["similarity"]
            if similarity >= 70:
                card_class = "trademark-high"
                risk_label = "높은 위험"
                bar_color = "#F44336"
            elif similarity >= 50:
                card_class = "trademark-medium"
                risk_label = "주의"
                bar_color = "#FF9800"
            else:
                card_class = "trademark-low"
                risk_label = "낮은 위험"
                bar_color = "#4CAF50"

            st.markdown(
                f"""
                <div class="{card_class}">
                    <table style="width:100%; border:none;">
                    <tr>
                        <td style="width:60%">
                            <b>{index + 1}. {item['trademarkName']}</b> &nbsp; {risk_label}<br>
                            <small>출원번호: {item['applicationNumber']} | 출원일: {item['applicationDate']}</small><br>
                            <small>상태: {item['registerStatus']} | 류: {item['classificationCode']} | 출원인: {item['applicantName']}</small>
                        </td>
                        <td style="width:40%; text-align:right; vertical-align:top;">
                            <b style="font-size:20px;">유사도 {similarity}%</b><br>
                            <div style="background:#ddd; border-radius:4px; height:8px; margin-top:4px;">
                                <div style="background:{bar_color}; width:{similarity}%; height:8px; border-radius:4px;"></div>
                            </div>
                            <br>
                            <a href="https://www.kipris.or.kr" target="_blank" style="color:#2196F3; font-size:12px;">KIPRIS에서 보기 →</a>
                        </td>
                    </tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### 데이터 표 보기")
        result_df = pd.DataFrame(
            [
                {
                    "상표명": row["trademarkName"],
                    "유사도": f'{row["similarity"]}%',
                    "상태": row["registerStatus"],
                    "류": row["classificationCode"],
                    "출원인": row["applicantName"],
                }
                for row in results[:10]
            ]
        )
        styled_df = result_df.style.map(similarity_cell_style, subset=["유사도"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            """
            <div style="background:#E8F5E9; border:2px solid #4CAF50; border-radius:12px; padding:20px; text-align:center;">
                <h3 style="color:#2E7D32;">유사한 선행상표가 없어요!</h3>
                <p style="color:#388E3C;">선택한 상품군에서 유사한 상표가 발견되지 않았어요.<br>
                등록 가능성이 매우 높습니다!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="tip-box" style="margin-top:16px;">
        ⚠️ 본 결과는 AI 자동 분석 참고용이며, 최종 판단은 반드시 <b>변리사와 상담</b>하세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("등록 가능성 높이기", use_container_width=True, type="primary"):
            st.session_state.step = 5
            st.rerun()
    with col2:
        if st.button("PDF 보고서 받기", use_container_width=True):
            st.info("PDF 생성 기능은 준비 중이에요!")
    with col3:
        if st.button("처음부터 다시", use_container_width=True):
            reset_session()
            st.rerun()

elif st.session_state.step == 5:
    st.markdown("## 등록 가능성을 높이는 방법")
    st.markdown(f"현재: **{st.session_state.trademark_name}** - {st.session_state.score}%")

    improvements = get_improvements(
        st.session_state.trademark_name,
        st.session_state.selected_codes,
        st.session_state.search_results or [],
        st.session_state.score or 0,
    )

    st.markdown("---")
    st.markdown("### 방법 1: 상표명 변경")
    st.markdown(
        """
    <div class="tip-box">
    현재 상표명과 발음이 다른 새로운 이름을 사용하면 등록 가능성이 높아져요.
    </div>
    """,
        unsafe_allow_html=True,
    )

    for suggestion in improvements.get("name_suggestions", []):
        score_value = suggestion.get("score", 0)
        if score_value >= 90:
            color, bg = "#2E7D32", "#E8F5E9"
        elif score_value >= 70:
            color, bg = "#1565C0", "#E3F2FD"
        else:
            color, bg = "#E65100", "#FFF3E0"

        st.markdown(
            f"""
            <div style="background:{bg}; border-radius:8px; padding:12px 16px; margin:6px 0; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <b style="font-size:18px;">{suggestion['name']}</b><br>
                    <small style="color:#546E7A">{suggestion.get('reason', '')}</small>
                </div>
                <div style="text-align:right;">
                    <b style="font-size:22px; color:{color};">예상 {score_value}%</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 방법 2: 상품 범위 조정")
    st.markdown(
        """
    <div class="tip-box">
    충돌하는 유사군코드를 제거하면 등록 가능성이 높아질 수 있어요.
    </div>
    """,
        unsafe_allow_html=True,
    )

    for suggestion in improvements.get("code_suggestions", []):
        st.markdown(
            f"""
            <div style="background:#E3F2FD; border-radius:8px; padding:12px 16px; margin:6px 0;">
                <b>{suggestion['description']}</b><br>
                <small style="color:#546E7A">{suggestion.get('reason', '')}</small><br>
                <b style="color:#1565C0;">→ 예상 {suggestion.get('expected_score', 0)}%로 향상</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 방법 3: 다른 상품군 검토")
    for suggestion in improvements.get("class_suggestions", []):
        st.markdown(
            f"""
            <div style="background:#F1F8E9; border-radius:8px; padding:12px 16px; margin:6px 0;">
                <b>{suggestion['description']}</b><br>
                <small style="color:#546E7A">{suggestion.get('reason', '')}</small><br>
                <b style="color:#2E7D32;">→ 예상 {suggestion.get('expected_score', 0)}%로 향상</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
    <div class="tip-box" style="margin-top:24px;">
    ⚠️ 위 제안은 AI 참고용 분석이에요. 최종 결정은 반드시 <b>변리사와 상담</b>하세요.
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 결과로 돌아가기", use_container_width=True):
            st.session_state.step = 4
            st.rerun()
    with col2:
        if st.button("처음부터 다시", use_container_width=True):
            reset_session()
            st.rerun()
