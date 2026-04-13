"""등록 가능성 점수 계산."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, List


def _normalize(text: str) -> str:
    return "".join(ch for ch in text.lower().strip() if ch.isalnum() or ("가" <= ch <= "힣"))


def _classes_from_items(item: dict) -> List[int]:
    result = []
    for chunk in str(item.get("classificationCode", "")).split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            result.append(int(chunk))
    return result


def _status_weight(status: str) -> float:
    if "등록" in status:
        return 1.0
    if "출원" in status or "심사" in status:
        return 0.8
    if "거절" in status:
        return 0.45
    if "소멸" in status or "만료" in status:
        return 0.35
    return 0.6


def similarity_percent(source: str, target: str) -> int:
    a = _normalize(source)
    b = _normalize(target)
    if not a or not b:
        return 0
    ratio = SequenceMatcher(None, a, b).ratio()
    if a == b:
        ratio = 1.0
    elif a in b or b in a:
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
    score = 68
    signals = []

    if is_coined:
        score += 18
        signals.append("새로 만든 단어라서 식별력이 높습니다.")
    else:
        score -= 8
        signals.append("일반 단어나 익숙한 표현은 식별력이 낮아질 수 있습니다.")

    clean_name = _normalize(trademark_name)
    if len(clean_name) >= 6:
        score += 4
    elif len(clean_name) <= 2:
        score -= 10

    if " " in trademark_name.strip():
        score -= 4
    if trademark_type == "문자+로고":
        score += 3
    elif trademark_type == "로고만":
        score += 1

    prior_summaries = []
    for item in prior_items:
        similarity = similarity_percent(trademark_name, item.get("trademarkName", ""))
        if similarity < 35:
            continue
        item_classes = _classes_from_items(item)
        class_overlap = bool(set(selected_classes) & set(item_classes))
        overlap_weight = 1.0 if class_overlap else 0.55
        status_weight = _status_weight(item.get("registerStatus", ""))

        if similarity >= 90:
            penalty = 30
        elif similarity >= 75:
            penalty = 20
        elif similarity >= 60:
            penalty = 11
        elif similarity >= 45:
            penalty = 5
        else:
            penalty = 2

        deduction = round(penalty * overlap_weight * status_weight)
        score -= deduction
        prior_summaries.append(
            {**item, "similarity": similarity, "class_overlap": class_overlap, "deduction": deduction}
        )

    prior_summaries.sort(
        key=lambda row: (-row["similarity"], not row["class_overlap"], -row["deduction"])
    )
    top_prior = prior_summaries[:3]

    if not top_prior:
        signals.append("직접 충돌하는 선행상표가 거의 보이지 않습니다.")
    else:
        strongest = top_prior[0]
        if strongest["similarity"] >= 85:
            signals.append("매우 유사한 선행상표가 있어 충돌 위험이 큽니다.")
        elif strongest["similarity"] >= 70:
            signals.append("유사한 선행상표가 있어 범위 조정이 필요할 수 있습니다.")
        else:
            signals.append("일부 유사 상표가 있지만 조정 여지는 있습니다.")

    if any(code.startswith("S") for code in selected_codes):
        signals.append("판매업 코드를 포함해 보호 범위는 넓지만 충돌 가능성도 함께 올라갑니다.")

    score = max(0, min(100, int(round(score))))
    band = get_score_band(score)

    return {
        "score": score,
        "band": band,
        "signals": signals,
        "top_prior": top_prior,
        "prior_count": len(prior_summaries),
        "distinctiveness": "조어상표" if is_coined else "일반어/관용어 가능성",
    }
