"""상품 범위와 상품-서비스업 예외 판단에 쓰는 법리 헬퍼."""

from __future__ import annotations

from typing import Iterable


GOODS_CLASS_RANGE = set(range(1, 35))
SERVICES_CLASS_RANGE = set(range(35, 46))
SOFTWARE_CODES = {"G390802", "G0901", "G0903"}
SOFTWARE_SERVICE_CLASSES = {35, 38, 42}

ECONOMIC_LINKS = {
    frozenset({3, 35}),
    frozenset({5, 35}),
    frozenset({5, 44}),
    frozenset({9, 42}),
    frozenset({10, 44}),
    frozenset({14, 35}),
    frozenset({16, 41}),
    frozenset({18, 35}),
    frozenset({20, 35}),
    frozenset({25, 35}),
    frozenset({30, 43}),
    frozenset({31, 35}),
    frozenset({31, 44}),
    frozenset({39, 43}),
}

SCOPE_GROUP_LABELS = {
    "exact_scope_candidates": "실질 충돌 후보",
    "same_class_candidates": "동일 니스류 보조 검토군",
    "related_market_candidates": "상품-서비스업 예외 검토군",
    "irrelevant_candidates": "제외 후보",
}


def infer_kind_from_classes(classes: Iterable[int | str]) -> str | None:
    normalized = []
    for value in classes:
        try:
            normalized.append(int(value))
        except (TypeError, ValueError):
            continue
    if not normalized:
        return None
    if all(value in GOODS_CLASS_RANGE for value in normalized):
        return "goods"
    if all(value in SERVICES_CLASS_RANGE for value in normalized):
        return "services"
    return None


def build_scope_counts(bucket_counts: dict[str, int]) -> dict[str, int]:
    return {
        "exact_scope_candidates": bucket_counts.get("same_code", 0),
        "same_class_candidates": bucket_counts.get("same_class", 0),
        "related_market_candidates": bucket_counts.get("exception", 0),
        "irrelevant_candidates": bucket_counts.get("excluded", 0),
    }


def has_economic_link(selected_classes: Iterable[int], item_classes: Iterable[int]) -> bool:
    for selected in selected_classes:
        for item_class in item_classes:
            if frozenset({int(selected), int(item_class)}) in ECONOMIC_LINKS:
                return True
    return False


def software_service_exception(
    selected_classes: Iterable[int],
    item_classes: Iterable[int],
    selected_codes: Iterable[str],
    item_code: str,
    selected_keywords: Iterable[str],
    item_kind: str | None,
    similarity_hint: int,
    mark_identity: str,
) -> dict:
    selected_classes = {int(value) for value in selected_classes}
    item_classes = {int(value) for value in item_classes}
    selected_codes = {str(code or "").strip().upper() for code in selected_codes if str(code or "").strip()}
    selected_keywords = {str(keyword or "").strip().lower() for keyword in selected_keywords if str(keyword or "").strip()}
    item_code = str(item_code or "").strip().upper()

    selected_has_software = bool(selected_classes & {9}) or bool(selected_codes & SOFTWARE_CODES)
    keyword_has_software = any(token in selected_keywords for token in {"소프트웨어", "앱", "saas", "플랫폼", "ai"})
    item_has_software = bool(item_classes & {9}) or item_code in SOFTWARE_CODES
    service_has_software = bool(item_classes & SOFTWARE_SERVICE_CLASSES) or bool(selected_classes & SOFTWARE_SERVICE_CLASSES)

    if not (selected_has_software or item_has_software or keyword_has_software):
        return {"applies": False}
    if not service_has_software:
        return {"applies": False}
    if item_kind not in {"goods", "services", None}:
        return {"applies": False}
    if mark_identity != "exact" and similarity_hint < 85:
        return {"applies": False}

    return {
        "applies": True,
        "score": 58,
        "penalty_weight": 0.52,
        "reason": "소프트웨어(G390802 포함)와 제42류 SaaS/플랫폼, 제35류 플랫폼 판매중개, 제38류 통신 플랫폼 서비스는 예외적으로 연계 가능성이 있어 검토군에 포함합니다.",
    }


def cross_kind_exception(
    selected_kind: str | None,
    item_kind: str | None,
    selected_classes: Iterable[int],
    item_classes: Iterable[int],
    selected_codes: Iterable[str],
    item_code: str,
    selected_keywords: Iterable[str],
    similarity_hint: int,
    mark_identity: str,
) -> dict:
    software_exception = software_service_exception(
        selected_classes=selected_classes,
        item_classes=item_classes,
        selected_codes=selected_codes,
        item_code=item_code,
        selected_keywords=selected_keywords,
        item_kind=item_kind,
        similarity_hint=similarity_hint,
        mark_identity=mark_identity,
    )
    if software_exception.get("applies"):
        return software_exception

    if selected_kind and item_kind and selected_kind != item_kind:
        if mark_identity != "exact" and similarity_hint < 88:
            return {"applies": False}
        if has_economic_link(selected_classes, item_classes):
            return {
                "applies": True,
                "score": 32,
                "penalty_weight": 0.24,
                "reason": "상품과 서비스업은 원칙적으로 유사도가 낮지만, 판매장소·수요자·사업 주체가 맞닿는 예외군으로 보조 검토합니다.",
            }
        return {"applies": False}

    if has_economic_link(selected_classes, item_classes):
        return {
            "applies": True,
            "score": 28,
            "penalty_weight": 0.22,
            "reason": "타 류이지만 경제적 견련성이 있어 관련 시장 예외군으로 남깁니다.",
        }

    return {"applies": False}
