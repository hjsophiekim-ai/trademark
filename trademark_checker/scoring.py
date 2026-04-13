"""상표 등록 가능성 점수를 계산한다."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, List


COMMON_WORDS = {
    "사랑",
    "사랑해",
    "브랜드",
    "맛있는",
    "행복",
    "좋은",
    "예쁜",
    "최고",
}


def _normalize(text: str) -> str:
    return "".join(ch for ch in text.lower().strip() if ch.isalnum() or ("가" <= ch <= "힣"))


def _classes_from_item(item: dict) -> List[int]:
    result: List[int] = []
    for chunk in str(item.get("classificationCode", "")).split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            result.append(int(chunk))
    return result


def _status_weight(status: str) -> float:
    if "등록" in status:
        return 1.0
    if "출원" in status or "심사" in status:
        return 0.82
    if "거절" in status:
        return 0.5
    if "만료" in status or "소멸" in status:
        return 0.35
    return 0.65


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


def _distinctiveness_label(name: str, is_coined: bool) -> str:
    normalized = _normalize(name)
    if is_coined:
        return "조어상표 ✅"
    if normalized in COMMON_WORDS or len(normalized) <= 2:
        return "식별력 약함 ⚠️"
    return "보통 수준"


def evaluate_registration(
    trademark_name: str,
    trademark_type: str,
    is_coined: bool,
    selected_classes: Iterable[int],
    selected_codes: Iterable[str],
    prior_items: List[dict],
) -> dict:
    selected_classes = list(selected_classes)
    selected_codes = list(selected_codes)
    normalized_name = _normalize(trademark_name)

    score = 72
    signals: List[str] = []

    if is_coined:
        score += 18
        signals.append("새로 만든 이름이라 식별력이 높게 평가됩니다.")
    else:
        score -= 10
        signals.append("일반 단어에 가까워 식별력 측면에서 불리할 수 있습니다.")

    if trademark_type == "문자+로고":
        score += 4
        signals.append("문자와 로고를 함께 쓰면 시각적 구별력이 조금 좋아질 수 있습니다.")
    elif trademark_type == "로고만":
        score += 1

    if len(normalized_name) >= 6:
        score += 3
    elif len(normalized_name) <= 2:
        score -= 12

    if " " in trademark_name.strip():
        score -= 4

    if not is_coined and normalized_name in COMMON_WORDS:
        score -= 12
        signals.append("일상적으로 많이 쓰이는 표현이라 등록 난도가 높아질 수 있습니다.")

    prior_summaries = []
    for item in prior_items:
        candidate_name = item.get("trademarkName", "")
        similarity = similarity_percent(trademark_name, candidate_name)
        if similarity < 30:
            continue

        item_classes = _classes_from_item(item)
        class_overlap = bool(set(selected_classes) & set(item_classes))
        overlap_weight = 1.0 if class_overlap else 0.55
        status_weight = _status_weight(item.get("registerStatus", ""))

        if similarity >= 90:
            base_penalty = 34
        elif similarity >= 80:
            base_penalty = 24
        elif similarity >= 70:
            base_penalty = 16
        elif similarity >= 60:
            base_penalty = 10
        elif similarity >= 45:
            base_penalty = 5
        else:
            base_penalty = 2

        deduction = round(base_penalty * overlap_weight * status_weight)
        score -= deduction
        prior_summaries.append(
            {
                **item,
                "similarity": similarity,
                "class_overlap": class_overlap,
                "deduction": deduction,
            }
        )

    prior_summaries.sort(key=lambda item: (-item["similarity"], not item["class_overlap"], -item["deduction"]))
    top_prior = prior_summaries[:3]

    if any(code.startswith("S") for code in selected_codes):
        score -= 2
        signals.append("판매업 코드를 함께 선택하면 보호범위는 넓어지지만 충돌 가능성도 조금 올라갑니다.")

    if not top_prior:
        score += 4
        signals.append("검색된 범위 안에서는 직접 충돌하는 선행상표가 많지 않습니다.")
    else:
        strongest = top_prior[0]
        if strongest["similarity"] >= 85:
            signals.append("매우 유사한 선행상표가 있어 그대로는 충돌 위험이 큽니다.")
        elif strongest["similarity"] >= 70:
            signals.append("유사한 선행상표가 있어 이름 또는 지정상품 조정이 필요할 수 있습니다.")
        else:
            signals.append("일부 유사 상표가 있지만 조정 여지는 있습니다.")

    score = max(0, min(100, int(round(score))))
    return {
        "score": score,
        "band": get_score_band(score),
        "signals": signals,
        "top_prior": top_prior,
        "prior_count": len(prior_summaries),
        "distinctiveness": _distinctiveness_label(trademark_name, is_coined),
    }
