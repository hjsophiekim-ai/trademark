"""하늘색/블루 테마 CSS 스타일 모음"""

import streamlit as st

# 등록가능성 구간별 색상
PROB_COLORS = {
    (90, 101): {"bg": "#E8F5E9", "border": "#4CAF50", "text": "#2E7D32", "label": "등록 가능성 매우 높음 🟢"},
    (70,  90): {"bg": "#E3F2FD", "border": "#2196F3", "text": "#1565C0", "label": "등록 가능성 높음 🔵"},
    (50,  70): {"bg": "#FFF3E0", "border": "#FF9800", "text": "#E65100", "label": "주의 필요 🟠"},
    (30,  50): {"bg": "#FFEBEE", "border": "#F44336", "text": "#B71C1C", "label": "등록 어려움 🔴"},
    ( 0,  30): {"bg": "#B71C1C", "border": "#7F0000", "text": "#FFFFFF", "label": "등록 불가 ⛔"},
}

def get_prob_style(score: float) -> dict:
    for (lo, hi), style in PROB_COLORS.items():
        if lo <= score < hi:
            return style
    return PROB_COLORS[(0, 30)]


MAIN_CSS = """
<style>
/* ── 전체 배경 ── */
.stApp { background-color: #F0F8FF; }
[data-testid="stAppViewContainer"] { background-color: #F0F8FF; }

/* ── 헤더 ── */
.tm-header {
    background: linear-gradient(135deg, #1565C0 0%, #2196F3 100%);
    color: white;
    padding: 20px 30px 16px;
    border-radius: 16px;
    margin-bottom: 24px;
    box-shadow: 0 4px 16px rgba(33,150,243,0.3);
}
.tm-header h1 { color: white; margin: 0 0 4px; font-size: 1.6rem; }
.tm-header p  { color: #BBDEFB; margin: 0; font-size: 0.9rem; }

/* ── 진행 단계 표시바 ── */
.step-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin-top: 14px;
    flex-wrap: nowrap;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
}
.step-circle {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
    background: rgba(255,255,255,0.25);
    color: white;
    border: 2px solid rgba(255,255,255,0.4);
    transition: all 0.2s;
}
.step-circle.active {
    background: white;
    color: #1565C0;
    border-color: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.step-circle.done {
    background: #43A047;
    border-color: #43A047;
    color: white;
}
.step-label {
    font-size: 0.65rem;
    color: rgba(255,255,255,0.7);
    white-space: nowrap;
}
.step-label.active { color: white; font-weight: 600; }
.step-arrow {
    color: rgba(255,255,255,0.5);
    font-size: 1rem;
    padding: 0 6px;
    margin-bottom: 16px;
}

/* ── 카드 ── */
.tm-card {
    background: white;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
    border: 1px solid #BBDEFB;
    box-shadow: 0 2px 8px rgba(33,150,243,0.08);
}
.tm-card-blue {
    background: #E8F4FD;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border-left: 4px solid #2196F3;
}
.tm-card-tip {
    background: #FFF8E1;
    border-radius: 10px;
    padding: 12px 16px;
    border-left: 4px solid #FFC107;
    font-size: 0.88rem;
    color: #5D4037;
    margin: 8px 0;
}

/* ── 등록가능성 큰 카드 ── */
.prob-card {
    border-radius: 16px;
    padding: 28px;
    text-align: center;
    margin: 16px 0;
    border: 2px solid;
}
.prob-number {
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.1;
}
.prob-label {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 6px;
}

/* ── 진행바 ── */
.prob-bar-wrap {
    background: #E3F2FD;
    border-radius: 10px;
    height: 20px;
    margin: 10px 0;
    overflow: hidden;
}
.prob-bar-fill {
    height: 20px;
    border-radius: 10px;
    transition: width 0.6s ease;
}

/* ── 선행상표 아이템 ── */
.prior-item {
    border: 1px solid #E3F2FD;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    background: white;
    border-left: 4px solid #2196F3;
}
.prior-item.high { border-left-color: #F44336; }
.prior-item.medium { border-left-color: #FF9800; }
.prior-item.low { border-left-color: #4CAF50; }

/* ── 개선방안 카드 ── */
.improve-card {
    background: white;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    border: 1px solid #E3F2FD;
}
.improve-tag {
    display: inline-block;
    background: #E3F2FD;
    color: #1565C0;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 8px;
}

/* ── 버튼 스타일 ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2196F3, #1565C0) !important;
    border: none !important;
    color: white !important;
    padding: 10px 24px !important;
    font-size: 1rem !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1976D2, #0D47A1) !important;
    box-shadow: 0 4px 12px rgba(33,150,243,0.4) !important;
}

/* ── 추천 태그 ── */
.tag-rec {
    background: #E8F5E9; color: #2E7D32;
    border-radius: 12px; padding: 2px 8px;
    font-size: 0.75rem; font-weight: 600;
    display: inline-block; margin-left: 6px;
}
.tag-sale {
    background: #E3F2FD; color: #1565C0;
    border-radius: 12px; padding: 2px 8px;
    font-size: 0.75rem; font-weight: 600;
    display: inline-block; margin-left: 6px;
}

/* ── 선택 클래스/코드 뱃지 ── */
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    background: #E3F2FD; color: #1565C0;
    border-radius: 20px; padding: 4px 12px;
    font-size: 0.82rem; font-weight: 600;
    margin: 3px; border: 1px solid #90CAF9;
}

/* ── 입력 필드 ── */
.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 2px solid #BBDEFB !important;
    font-size: 1rem !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2196F3 !important;
    box-shadow: 0 0 0 3px rgba(33,150,243,0.15) !important;
}

/* 사이드바 숨기기 */
[data-testid="stSidebar"] { display: none; }
section[data-testid="stSidebar"] { display: none; }
.stDeployButton { display: none; }
#MainMenu { display: none; }
footer { display: none; }
header { display: none; }

/* 메인 패딩 */
.main .block-container { padding-top: 1rem; max-width: 780px; }
</style>
"""


def inject():
    st.markdown(MAIN_CSS, unsafe_allow_html=True)


def header(current_step: int):
    steps = ["상표명", "상품선택", "유사군", "검토결과", "개선방안"]
    circles_html = ""
    for i, label in enumerate(steps, 1):
        if i < current_step:
            cls = "done"
            icon = "✓"
        elif i == current_step:
            cls = "active"
            icon = str(i)
        else:
            cls = ""
            icon = str(i)
        label_cls = "active" if i == current_step else ""
        circles_html += f"""
        <div class="step-item">
            <div class="step-circle {cls}">{icon}</div>
            <div class="step-label {label_cls}">{label}</div>
        </div>
        """
        if i < len(steps):
            circles_html += '<div class="step-arrow">›</div>'

    st.markdown(f"""
    <div class="tm-header">
        <h1>📋 상표등록 가능성 검토</h1>
        <p>내 브랜드를 법적으로 보호하세요</p>
        <div class="step-bar">{circles_html}</div>
    </div>
    """, unsafe_allow_html=True)


def prob_card(score: float):
    style = get_prob_style(score)
    bar_color = style["border"]
    st.markdown(f"""
    <div class="prob-card" style="background:{style['bg']};border-color:{style['border']}">
        <div class="prob-number" style="color:{style['text']}">{score:.0f}%</div>
        <div class="prob-label" style="color:{style['text']}">{style['label']}</div>
        <div class="prob-bar-wrap" style="margin-top:14px">
            <div class="prob-bar-fill" style="width:{score}%;background:{bar_color}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def prior_item_card(rank: int, name: str, status: str, class_code: str,
                    similarity: int, applicant: str, app_number: str):
    if similarity >= 80:
        level_cls, level_color = "high",   "#F44336"
    elif similarity >= 60:
        level_cls, level_color = "medium", "#FF9800"
    else:
        level_cls, level_color = "low",    "#4CAF50"

    status_color = {"등록": "#2E7D32", "출원": "#1565C0",
                    "거절": "#9E9E9E", "포기": "#9E9E9E"}.get(status, "#555")

    kipris_url = f"https://www.kipris.or.kr/ktm/tradeMarkInfoa.do?method=getTMInfo&applno={app_number}"

    st.markdown(f"""
    <div class="prior-item {level_cls}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:700;font-size:1rem;color:#1A237E">{rank}. {name}</span>
            <span style="font-weight:700;font-size:0.9rem;color:{level_color}">유사도 {similarity}%</span>
        </div>
        <div style="font-size:0.82rem;color:#555;display:flex;gap:12px;flex-wrap:wrap">
            <span style="color:{status_color};font-weight:600">{status}</span>
            <span>제{class_code}류</span>
            <span>출원인: {applicant[:20]}</span>
            <a href="{kipris_url}" target="_blank" style="color:#2196F3;text-decoration:none;font-size:0.78rem">KIPRIS에서 보기 →</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
