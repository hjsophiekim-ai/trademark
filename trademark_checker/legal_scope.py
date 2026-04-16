"""상품 범위와 상품-서비스업 예외 판단을 다루는 헬퍼."""

from __future__ import annotations

from typing import Iterable


GOODS_CLASS_RANGE = set(range(1, 35))
SERVICES_CLASS_RANGE = set(range(35, 46))

SOFTWARE_PRIMARY_CODES = {"G390802"}
SOFTWARE_SECONDARY_CODES: set[str] = set()
SOFTWARE_SERVICE_CLASSES = {35, 38, 42}
SOFTWARE_KEYWORDS = {
    "소프트웨어",
    "앱",
    "애플리케이션",
    "응용프로그램",
    "프로그램",
    "saas",
    "플랫폼",
    "클라우드",
    "호스팅",
    "ai",
}

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


def _normalize_codes(values: Iterable[str]) -> set[str]:
    return {
        str(code or "").strip().upper()
        for code in values
        if str(code or "").strip()
    }


def _normalize_keywords(values: Iterable[str]) -> set[str]:
    normalized = set()
    for value in values:
        text = str(value or "").strip().lower()
        if not text:
            continue
        normalized.add(text)
    return normalized


def _has_software_keyword(keywords: set[str]) -> bool:
    for keyword in keywords:
        if any(token in keyword for token in SOFTWARE_KEYWORDS):
            return True
    return False


def _has_software_goods_signal(codes: set[str], keywords: set[str], *, require_keyword_for_secondary: bool) -> bool:
    if codes & SOFTWARE_PRIMARY_CODES:
        return True

    keyword_match = _has_software_keyword(keywords)
    if keyword_match and (codes & SOFTWARE_SECONDARY_CODES):
        return True

    if keyword_match and not codes:
        return True

    if not require_keyword_for_secondary and codes & SOFTWARE_SECONDARY_CODES:
        return True

    return False


def software_service_exception(
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
    selected_classes = {int(value) for value in selected_classes}
    item_classes = {int(value) for value in item_classes}
    selected_codes = _normalize_codes(selected_codes)
    item_code = str(item_code or "").strip().upper()
    selected_keywords = _normalize_keywords(selected_keywords)

    # 소프트웨어 예외는 9류 상품과 35/38/42류 서비스의 교차 상황에서만 강하게 적용한다.
    if {selected_kind, item_kind} != {"goods", "services"}:
        return {"applies": False}

    selected_has_software = _has_software_goods_signal(
        selected_codes,
        selected_keywords,
        require_keyword_for_secondary=True,
    )
    item_has_software = _has_software_goods_signal(
        {item_code} if item_code else set(),
        set(),
        require_keyword_for_secondary=False,
    )
    service_has_software = bool(selected_classes & SOFTWARE_SERVICE_CLASSES) or bool(item_classes & SOFTWARE_SERVICE_CLASSES)

    if not service_has_software:
        return {"applies": False}
    if not (selected_has_software or item_has_software):
        return {"applies": False}
    if mark_identity != "exact" and similarity_hint < 85:
        return {"applies": False}

    return {
        "applies": True,
        "score": 58,
        "penalty_weight": 0.52,
        "reason": (
            "소프트웨어(G390802 포함)와 제35·38·42류 서비스는 예외 검토 대상이지만, "
            "양 표장이 전체적으로 동일하거나 극히 유사한 경우에만 강한 예외 검토군으로 반영했습니다."
        ),
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
        selected_kind=selected_kind,
        item_kind=item_kind,
        selected_classes=selected_classes,
        item_classes=item_classes,
        selected_codes=selected_codes,
        item_code=item_code,
        selected_keywords=selected_keywords,
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
                "reason": (
                    "상품과 서비스업은 원칙적으로 비유사로 보되, 동일 사업자 제공 가능성과 "
                    "용도·장소·수요자 중첩이 있는 조합이라 보조 예외 검토군으로만 포함했습니다."
                ),
            }
        return {"applies": False}

    if has_economic_link(selected_classes, item_classes):
        return {
            "applies": True,
            "score": 28,
            "penalty_weight": 0.22,
            "reason": "타 류이지만 거래상 밀접한 관련성이 있어 관련 시장 예외 검토군으로만 포함했습니다.",
        }

    return {"applies": False}
