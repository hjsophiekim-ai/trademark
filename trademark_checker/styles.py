"""Streamlit 스타일과 공통 헤더."""

from __future__ import annotations

import streamlit as st


def get_score_style(score: int) -> dict:
    if score >= 90:
        return {"bg": "#E8F5E9", "border": "#4CAF50", "text": "#2E7D32", "label": "등록 가능성 매우 높음"}
    if score >= 70:
        return {"bg": "#E3F2FD", "border": "#2196F3", "text": "#1565C0", "label": "등록 가능성 높음"}
    if score >= 50:
        return {"bg": "#FFF3E0", "border": "#FF9800", "text": "#E65100", "label": "주의 필요"}
    if score >= 30:
        return {"bg": "#FFEBEE", "border": "#F44336", "text": "#B71C1C", "label": "등록 어려움"}
    return {"bg": "#B71C1C", "border": "#7F0000", "text": "#FFFFFF", "label": "등록 불가 ⛔"}


def apply_styles() -> None:
    st.markdown(
        """
<style>
.stApp {
    background: #F0F8FF;
    color: #1A237E;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stSidebar"] {
    display: none;
}
.app-shell {
    max-width: 1100px;
    margin: 0 auto;
}
.top-header {
    background: #E8F4FD;
    border: 1px solid #B9DDF7;
    border-radius: 24px;
    padding: 26px 28px 20px;
    margin-bottom: 22px;
}
.top-title {
    margin: 0;
    color: #1565C0;
    font-size: 2rem;
    font-weight: 800;
}
.top-subtitle {
    color: #0D47A1;
    margin-top: 8px;
    font-size: 1rem;
}
.step-track {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 18px;
}
.step-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: white;
    color: #1565C0;
    border: 1px solid #90CAF9;
    border-radius: 999px;
    padding: 8px 14px;
    font-weight: 700;
    font-size: 0.92rem;
}
.step-pill.active {
    background: #2196F3;
    color: white;
    border-color: #2196F3;
}
.step-arrow {
    color: #1565C0;
    font-size: 1rem;
    font-weight: 800;
}
.wizard-card {
    background: white;
    border: 1px solid #D7ECFB;
    border-radius: 20px;
    padding: 26px;
    box-shadow: 0 8px 24px rgba(33, 150, 243, 0.08);
    margin-bottom: 18px;
}
.intro-text {
    color: #0D47A1;
    font-size: 1.02rem;
    margin-bottom: 14px;
}
.hint-card {
    background: #F7FBFF;
    border: 1px dashed #90CAF9;
    border-radius: 16px;
    padding: 16px 18px;
    margin: 12px 0 18px;
}
.soft-card {
    background: #E8F4FD;
    border: 1px solid #C9E6FB;
    border-left: 4px solid #2196F3;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 10px;
}
.soft-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1565C0;
}
.small-muted {
    color: #54749D;
    font-size: 0.92rem;
}
.pick-chip {
    display: inline-block;
    background: #E3F2FD;
    color: #1565C0;
    border: 1px solid #90CAF9;
    border-radius: 999px;
    padding: 6px 12px;
    margin: 4px 6px 0 0;
    font-weight: 700;
    font-size: 0.88rem;
}
.recommend-pill {
    display: inline-block;
    background: #E8F5E9;
    color: #2E7D32;
    border-radius: 999px;
    padding: 3px 10px;
    margin-right: 6px;
    font-size: 0.76rem;
    font-weight: 700;
}
.sale-pill {
    display: inline-block;
    background: #E3F2FD;
    color: #1565C0;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.76rem;
    font-weight: 700;
}
.score-card {
    border-radius: 20px;
    padding: 24px;
    text-align: center;
    border: 2px solid;
    margin-bottom: 18px;
}
.score-number {
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    margin-top: 10px;
    font-size: 1.1rem;
    font-weight: 700;
}
.score-bar {
    width: 100%;
    height: 16px;
    margin-top: 16px;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 999px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 999px;
}
.progress-shell {
    background: #DCEFFD;
    border-radius: 999px;
    height: 18px;
    overflow: hidden;
    margin: 10px 0 18px;
}
.progress-fill {
    height: 18px;
    background: #2196F3;
}
.status-list {
    margin-top: 12px;
    line-height: 1.9;
}
.prior-card {
    background: white;
    border: 1px solid #D7ECFB;
    border-left: 5px solid #2196F3;
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 10px;
}
.prior-card.high {
    border-left-color: #F44336;
}
.prior-card.medium {
    border-left-color: #FF9800;
}
.prior-card.low {
    border-left-color: #4CAF50;
}
.improve-card {
    background: white;
    border: 1px solid #D7ECFB;
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 12px;
}
.method-tag {
    display: inline-block;
    background: #E3F2FD;
    color: #1565C0;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 8px;
}
.disclaimer {
    background: #FFF8E1;
    border: 1px solid #FFE082;
    color: #6D4C41;
    border-radius: 14px;
    padding: 16px 18px;
}
.catalog-note {
    color: #0D47A1;
    font-size: 0.95rem;
    margin: 8px 0 12px;
}
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    font-weight: 700;
}
div.stButton > button[kind="primary"] {
    background: #2196F3;
    color: white;
    border: none;
}
div.stButton > button[kind="primary"]:hover {
    background: #1976D2;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_header(current_step: int) -> None:
    labels = ["상표명", "상품선택", "유사군", "검토결과", "개선방안"]
    parts = []
    for index, label in enumerate(labels, start=1):
        active_class = "step-pill active" if index == current_step else "step-pill"
        parts.append(f'<div class="{active_class}">{index} {label}</div>')
        if index < len(labels):
            parts.append('<div class="step-arrow">→</div>')

    st.markdown(
        f"""
<div class="app-shell">
  <div class="top-header">
    <div class="top-title">상표등록 가능성 검토</div>
    <div class="top-subtitle">내 브랜드를 법적으로 보호하세요</div>
    <div class="step-track">{''.join(parts)}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
