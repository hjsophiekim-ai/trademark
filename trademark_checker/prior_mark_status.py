"""선행상표 상태와 거절이유 정규화."""

from __future__ import annotations

import re
from typing import Callable, Iterable


STATUS_PROFILES = (
    {
        "keywords": ("등록",),
        "normalized": "등록",
        "category": "live_blockers",
        "survival_label": "실질 장애물",
        "counts_toward_final_score": True,
        "confusion_weight": 1.0,
        "score_weight": 1.0,
    },
    {
        "keywords": ("출원",),
        "normalized": "출원",
        "category": "live_blockers",
        "survival_label": "실질 장애물",
        "counts_toward_final_score": True,
        "confusion_weight": 0.96,
        "score_weight": 0.92,
    },
    {
        "keywords": ("심사",),
        "normalized": "심사중",
        "category": "live_blockers",
        "survival_label": "실질 장애물",
        "counts_toward_final_score": True,
        "confusion_weight": 0.93,
        "score_weight": 0.86,
    },
    {
        "keywords": ("공고",),
        "normalized": "공고",
        "category": "live_blockers",
        "survival_label": "실질 장애물",
        "counts_toward_final_score": True,
        "confusion_weight": 0.94,
        "score_weight": 0.88,
    },
    {
        "keywords": ("거절",),
        "normalized": "거절",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.48,
        "score_weight": 0.0,
    },
    {
        "keywords": ("포기",),
        "normalized": "포기",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.42,
        "score_weight": 0.0,
    },
    {
        "keywords": ("취하",),
        "normalized": "취하",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.4,
        "score_weight": 0.0,
    },
    {
        "keywords": ("소멸", "만료", "말소"),
        "normalized": "소멸",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.38,
        "score_weight": 0.0,
    },
    {
        "keywords": ("무효",),
        "normalized": "무효",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.38,
        "score_weight": 0.0,
    },
)

REFUSAL_BASIS_KEYWORDS = {
    "외관": "외관",
    "호칭": "호칭",
    "칭호": "호칭",
    "관념": "관념",
    "식별력": "식별력",
    "기술": "기술적 표장 여부",
    "성질표시": "기술적 표장 여부",
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _normalize(text: str) -> str:
    cleaned = _strip_html(text).lower().strip()
    return "".join(ch for ch in cleaned if ch.isalnum() or ("가" <= ch <= "힣"))


def _split_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = _strip_html(value)
        if not text:
            return []
        parts = re.split(r"[,/;|·\n]+", text)
        return [part.strip(" []()\"'") for part in parts if part.strip(" []()\"'")]
    if isinstance(value, Iterable):
        merged: list[str] = []
        for item in value:
            merged.extend(_split_values(item))
        return _dedupe_preserve(merged)
    return [_strip_html(str(value))]


def _dedupe_preserve(values: Iterable[str]) -> list[str]:
    seen = set()
    items: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return items


def _extract_basis_from_text(text: str) -> list[str]:
    found = []
    for keyword, label in REFUSAL_BASIS_KEYWORDS.items():
        if keyword in text:
            found.append(label)
    return _dedupe_preserve(found)


def status_profile(status: str) -> dict:
    text = _strip_html(status)
    for profile in STATUS_PROFILES:
        if any(keyword in text for keyword in profile["keywords"]):
            return {**profile, "raw": text}
    return {
        "raw": text,
        "normalized": text or "기타",
        "category": "historical_references",
        "survival_label": "역사적 참고자료",
        "counts_toward_final_score": False,
        "confusion_weight": 0.4,
        "score_weight": 0.0,
    }


def _similarity_against_marks(
    trademark_name: str,
    marks: Iterable[str],
    similarity_percent: Callable[[str, str], int],
) -> int:
    current = _strip_html(trademark_name)
    scores = [similarity_percent(current, mark) for mark in marks if _strip_html(mark)]
    return max(scores) if scores else 0


def _infer_relevance(
    trademark_name: str,
    refusal_core: str,
    cited_marks: list[str],
    weak_elements: list[str],
    text: str,
    similarity_percent: Callable[[str, str], int],
    phonetic_similarity_percent: Callable[[str, str], int],
) -> str:
    current = _strip_html(trademark_name)
    direct_candidates = [refusal_core] if refusal_core else []
    direct_candidates.extend(cited_marks)
    direct_score = _similarity_against_marks(current, direct_candidates, similarity_percent)

    if refusal_core:
        direct_score = max(
            direct_score,
            similarity_percent(current, refusal_core),
            phonetic_similarity_percent(current, refusal_core),
        )

    if direct_score >= 85:
        return "high"
    if direct_score >= 70:
        return "medium"

    weak_overlap = any(_normalize(element) and _normalize(element) in _normalize(current) for element in weak_elements)
    if weak_overlap and not refusal_core:
        return "medium"
    if weak_overlap:
        return "low"
    if text and _normalize(current) and _normalize(current) in _normalize(text):
        return "medium"
    return "low"


def normalize_refusal_analysis(
    item: dict,
    trademark_name: str,
    similarity_percent: Callable[[str, str], int],
    phonetic_similarity_percent: Callable[[str, str], int],
) -> dict:
    reason_summary = _strip_html(
        item.get("reason_summary")
        or item.get("reasonSummary")
        or item.get("refusalSummary")
        or item.get("refusal_summary")
        or ""
    )
    refusal_text = _strip_html(
        item.get("refusal_text")
        or item.get("refusalText")
        or item.get("decisionText")
        or item.get("decision_text")
        or item.get("refusalReason")
        or item.get("refusal_reason")
        or ""
    )
    cited_marks = _dedupe_preserve(
        _split_values(item.get("cited_marks"))
        + _split_values(item.get("citedMarks"))
        + _split_values(item.get("cited_mark"))
    )
    weak_elements = _dedupe_preserve(
        _split_values(item.get("weak_elements")) + _split_values(item.get("weakElements"))
    )
    refusal_basis = _dedupe_preserve(
        _split_values(item.get("refusal_basis")) + _split_values(item.get("refusalBasis"))
    )
    refusal_core = _strip_html(item.get("refusal_core") or item.get("refusalCore") or "")
    current_mark_relevance = _strip_html(
        item.get("current_mark_relevance") or item.get("currentMarkRelevance") or ""
    ).lower()

    combined_text = " ".join(part for part in [reason_summary, refusal_text] if part)
    if not refusal_basis and combined_text:
        refusal_basis = _extract_basis_from_text(combined_text)

    if not reason_summary:
        summary_parts = []
        if refusal_core:
            summary_parts.append(f"핵심 요부: {refusal_core}")
        if cited_marks:
            summary_parts.append(f"인용상표: {', '.join(cited_marks)}")
        if refusal_basis:
            summary_parts.append(f"판단축: {', '.join(refusal_basis)}")
        reason_summary = " / ".join(summary_parts)

    if current_mark_relevance not in {"high", "medium", "low"}:
        current_mark_relevance = _infer_relevance(
            trademark_name=trademark_name,
            refusal_core=refusal_core,
            cited_marks=cited_marks,
            weak_elements=weak_elements,
            text=combined_text,
            similarity_percent=similarity_percent,
            phonetic_similarity_percent=phonetic_similarity_percent,
        )

    directly_relevant = current_mark_relevance in {"high", "medium"}
    if current_mark_relevance == "high":
        relevance_label = "높음"
    elif current_mark_relevance == "medium":
        relevance_label = "중간"
    else:
        relevance_label = "낮음"

    return {
        "reason_summary": reason_summary,
        "cited_marks": cited_marks,
        "refusal_core": refusal_core,
        "refusal_basis": refusal_basis,
        "weak_elements": weak_elements,
        "current_mark_relevance": current_mark_relevance,
        "current_mark_relevance_label": relevance_label,
        "directly_relevant": directly_relevant,
        "raw_text": refusal_text,
    }


def merge_refusal_analysis(current: dict, new: dict) -> dict:
    if not current:
        return new
    merged = {
        "reason_summary": current.get("reason_summary") or new.get("reason_summary", ""),
        "cited_marks": _dedupe_preserve(current.get("cited_marks", []) + new.get("cited_marks", [])),
        "refusal_core": current.get("refusal_core") or new.get("refusal_core", ""),
        "refusal_basis": _dedupe_preserve(current.get("refusal_basis", []) + new.get("refusal_basis", [])),
        "weak_elements": _dedupe_preserve(current.get("weak_elements", []) + new.get("weak_elements", [])),
        "current_mark_relevance": current.get("current_mark_relevance", "low"),
        "current_mark_relevance_label": current.get("current_mark_relevance_label", "낮음"),
        "directly_relevant": current.get("directly_relevant", False),
        "raw_text": current.get("raw_text") or new.get("raw_text", ""),
    }
    if not merged["reason_summary"]:
        merged["reason_summary"] = new.get("reason_summary", "")
    if not merged["refusal_core"]:
        merged["refusal_core"] = new.get("refusal_core", "")

    current_rank = {"low": 0, "medium": 1, "high": 2}.get(current.get("current_mark_relevance", "low"), 0)
    new_rank = {"low": 0, "medium": 1, "high": 2}.get(new.get("current_mark_relevance", "low"), 0)
    if new_rank > current_rank:
        merged["current_mark_relevance"] = new.get("current_mark_relevance", "low")
        merged["current_mark_relevance_label"] = new.get("current_mark_relevance_label", "낮음")
        merged["directly_relevant"] = new.get("directly_relevant", False)

    return merged
