"""상표 등록 가능성 점수 계산."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List


COMMON_WORDS = {"사랑", "사랑해", "브랜드", "맛있는", "행복", "좋은", "예쁜", "최고"}


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _normalize(text: str) -> str:
    cleaned = strip_html(text).lower().strip()
    return "".join(ch for ch in cleaned if ch.isalnum() or ("가" <= ch <= "힣"))


def similarity_percent(source: str, target: str) -> int:
    left = _normalize(source)
    right = _normalize(target)
    if not left or not right:
        return 0
    ratio = SequenceMatcher(None, left, right).ratio()
    if left == right:
        ratio = 1.0
    elif left in right or right in left:
        ratio = max(ratio, 0.86)
    return int(round(ratio * 100))


def calculate_score(
    trademark_name: str,
    results: List[dict],
    is_coined: bool,
    trademark_type: str,
) -> int:
    """간단한 초보자용 등록 가능성 점수."""
    score = 72
    normalized = _normalize(trademark_name)

    if is_coined:
        score += 18
    else:
        score -= 10

    if trademark_type == "문자+로고":
        score += 4
    elif trademark_type == "로고만":
        score += 1

    if len(normalized) >= 6:
        score += 3
    elif len(normalized) <= 2:
        score -= 12

    if " " in trademark_name.strip():
        score -= 4

    if not is_coined and normalized in COMMON_WORDS:
        score -= 14

    for item in results:
        similarity = item.get("similarity", 0)
        status = item.get("registerStatus") or item.get("registrationStatus") or item.get("status") or ""
        if similarity >= 90:
            penalty = 34
        elif similarity >= 80:
            penalty = 24
        elif similarity >= 70:
            penalty = 16
        elif similarity >= 60:
            penalty = 10
        elif similarity >= 45:
            penalty = 5
        else:
            penalty = 2

        if "등록" in status:
            penalty = int(round(penalty * 1.0))
        elif "출원" in status or "심사" in status:
            penalty = int(round(penalty * 0.82))
        elif "거절" in status:
            penalty = int(round(penalty * 0.5))
        else:
            penalty = int(round(penalty * 0.65))

        score -= penalty

    return max(0, min(100, int(round(score))))


def get_score_band(score: int) -> dict:
    if score >= 90:
        return {"label": "등록 가능성 매우 높음", "color": "#4CAF50"}
    if score >= 70:
        return {"label": "등록 가능성 높음", "color": "#2196F3"}
    if score >= 50:
        return {"label": "주의 필요", "color": "#FF9800"}
    if score >= 30:
        return {"label": "등록 어려움", "color": "#F44336"}
    return {"label": "등록 불가 ⛔", "color": "#B71C1C"}


def evaluate_registration(
    trademark_name: str,
    trademark_type: str,
    is_coined: bool,
    selected_classes: Iterable[int],
    selected_codes: Iterable[str],
    prior_items: List[dict],
) -> dict:
    enriched = []
    for item in prior_items:
        similarity = similarity_percent(trademark_name, item.get("trademarkName", ""))
        if similarity < 30:
            continue
        enriched.append({**item, "similarity": similarity})

    enriched.sort(key=lambda item: item["similarity"], reverse=True)
    score = calculate_score(trademark_name, enriched, is_coined, trademark_type)
    distinctiveness = "조어상표 ✅" if is_coined else "식별력 약함 ⚠️" if _normalize(trademark_name) in COMMON_WORDS else "보통 수준"
    signals = []
    if is_coined:
        signals.append("새로 만든 이름이라 식별력이 높게 평가됩니다.")
    else:
        signals.append("일반 단어에 가까워 식별력 측면에서 불리할 수 있습니다.")
    if enriched:
        if enriched[0]["similarity"] >= 85:
            signals.append("매우 유사한 선행상표가 있어 그대로는 충돌 위험이 큽니다.")
        elif enriched[0]["similarity"] >= 70:
            signals.append("유사한 선행상표가 있어 이름 또는 지정상품 조정이 필요할 수 있습니다.")
    else:
        signals.append("검색된 범위 안에서는 직접 충돌하는 선행상표가 많지 않습니다.")

    return {
        "score": score,
        "band": get_score_band(score),
        "signals": signals,
        "top_prior": enriched[:3],
        "prior_count": len(enriched),
        "distinctiveness": distinctiveness,
    }
