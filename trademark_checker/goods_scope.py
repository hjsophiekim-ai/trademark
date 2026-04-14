"""니스분류/유사군코드 기반 지정상품 범위 정규화와 필터."""

from __future__ import annotations

import re
from typing import Iterable

from legal_scope import SCOPE_GROUP_LABELS, cross_kind_exception, infer_kind_from_classes
from nice_catalog import dedupe_ints, dedupe_strings
from similarity_code_db import get_code_metadata


def _split_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parts = re.split(r"[,/;|·\n]+", text)
        return [part.strip(" []()\"'") for part in parts if part.strip(" []()\"'")]
    if isinstance(value, Iterable):
        merged: list[str] = []
        for item in value:
            merged.extend(_split_values(item))
        return dedupe_strings(merged)
    return [str(value).strip()]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", str(text or "").lower())


def _clean_class_text(value: object) -> int | None:
    digits = re.findall(r"\d+", str(value or ""))
    if not digits:
        return None
    return int(digits[0])


def _extract_classes(value: object) -> list[int]:
    if isinstance(value, str):
        raw = value.split(",")
    else:
        raw = list(value or [])
    classes = []
    for item in raw:
        class_no = _clean_class_text(item)
        if class_no is None or class_no in classes:
            continue
        classes.append(class_no)
    return classes


def _item_code_tokens(code: str) -> set[str]:
    if not code:
        return set()
    row = get_code_metadata(code)
    if not row:
        return set()
    fragments = [row.get("name", ""), row.get("description", ""), row.get("기준상품", "")]
    return {token for fragment in fragments for token in _tokenize(fragment) if len(token) >= 2}


def normalize_selected_input(
    selected_kind: str | None,
    selected_classes: Iterable[int | str],
    selected_codes: Iterable[str],
    selected_fields: Iterable[dict] | None,
    specific_product_text: str = "",
) -> dict:
    selected_fields = list(selected_fields or [])
    nice_classes = _extract_classes(selected_classes)
    subgroup_ids = []
    subgroup_labels = []
    group_ids = []
    group_labels = []
    keywords = []
    contextual_similarity_codes = []

    for field in selected_fields:
        nice_classes.extend(_extract_classes(field.get("nice_classes", [])))
        maybe_class = _clean_class_text(field.get("class_no", field.get("류", "")))
        if maybe_class is not None:
            nice_classes.append(maybe_class)
        if field.get("field_id"):
            subgroup_ids.append(field["field_id"])
        if field.get("description"):
            subgroup_labels.append(field["description"])
        if field.get("group_id"):
            group_ids.append(field["group_id"])
        if field.get("group_label"):
            group_labels.append(field["group_label"])
        keywords.extend(_split_values(field.get("keywords", [])))
        contextual_similarity_codes.extend(_split_values(field.get("similarity_codes", [])))

    nice_classes = dedupe_ints(nice_classes)
    explicit_similarity_codes = dedupe_strings(selected_codes)
    contextual_similarity_codes = dedupe_strings(contextual_similarity_codes)
    keywords = dedupe_strings(keywords)

    if not selected_kind:
        selected_kind = infer_kind_from_classes(nice_classes)

    text_fragments = [specific_product_text]
    text_fragments.extend(subgroup_labels)
    text_fragments.extend(group_labels)
    text_fragments.extend(keywords)
    for code in contextual_similarity_codes + explicit_similarity_codes:
        metadata = get_code_metadata(code)
        if not metadata:
            continue
        text_fragments.extend([metadata.get("name", ""), metadata.get("description", "")])

    return {
        "selected_kind": selected_kind,
        "selected_groups": dedupe_strings(group_labels),
        "selected_group_ids": dedupe_strings(group_ids),
        "selected_subgroups": dedupe_strings(subgroup_labels),
        "selected_subgroup_ids": dedupe_strings(subgroup_ids),
        "selected_nice_classes": nice_classes,
        "selected_similarity_codes": explicit_similarity_codes,
        "contextual_similarity_codes": contextual_similarity_codes,
        "selected_keywords": keywords,
        "specific_product_text": specific_product_text,
        "tokens": {token for fragment in text_fragments for token in _tokenize(fragment) if len(token) >= 2},
    }


def classify_product_similarity(item: dict, context: dict) -> dict:
    selected_classes = context["selected_nice_classes"]
    selected_codes = context["selected_similarity_codes"]
    context_codes = set(selected_codes) | set(context.get("contextual_similarity_codes", []))
    selected_keywords = context["selected_keywords"]
    selected_kind = context.get("selected_kind")
    item_classes = [int(value) for value in item.get("classes", []) if str(value).strip()]
    shared_classes = [class_no for class_no in item_classes if class_no in selected_classes]
    explicit_code = str(item.get("similarityGroupCode", "") or "").strip()
    similarity_hint = int(item.get("similarity", 0))
    mark_identity = item.get("mark_identity", "similar")
    item_kind = infer_kind_from_classes(item_classes)
    code_match = bool(explicit_code) and explicit_code in context_codes

    if code_match:
        return {
            "bucket": "same_code",
            "scope_bucket": "exact_scope_candidates",
            "scope_bucket_label": SCOPE_GROUP_LABELS["exact_scope_candidates"],
            "label": "동일 유사군코드",
            "score": 96,
            "penalty_weight": 1.72,
            "strict_same_code": True,
            "include": True,
            "reason": f"선택한 유사군코드 {explicit_code}와 직접 일치해 권리범위가 가장 가깝습니다.",
        }

    if shared_classes:
        item_tokens = _item_code_tokens(explicit_code)
        overlap_tokens = sorted(context["tokens"] & item_tokens)
        if explicit_code and overlap_tokens:
            return {
                "bucket": "same_class",
                "scope_bucket": "same_class_candidates",
                "scope_bucket_label": SCOPE_GROUP_LABELS["same_class_candidates"],
                "label": "동일 니스류 + 인접 상품군",
                "score": 56,
                "penalty_weight": 0.94,
                "strict_same_code": False,
                "include": True,
                "reason": "동일 니스류이고 상품 문맥이 겹쳐 보조 검토군에 포함합니다: " + ", ".join(overlap_tokens[:3]),
            }
        return {
            "bucket": "same_class",
            "scope_bucket": "same_class_candidates",
            "scope_bucket_label": SCOPE_GROUP_LABELS["same_class_candidates"],
            "label": "동일 니스류 검토군",
            "score": 42,
            "penalty_weight": 0.7,
            "strict_same_code": False,
            "include": True,
            "reason": "동일 니스류이지만 유사군코드는 다르므로 보조 검토군으로만 반영합니다.",
        }

    cross_kind = cross_kind_exception(
        selected_kind=selected_kind,
        item_kind=item_kind,
        selected_classes=selected_classes,
        item_classes=item_classes,
        selected_codes=context_codes,
        item_code=explicit_code,
        selected_keywords=selected_keywords,
        similarity_hint=similarity_hint,
        mark_identity=mark_identity,
    )
    if cross_kind.get("applies"):
        return {
            "bucket": "exception",
            "scope_bucket": "related_market_candidates",
            "scope_bucket_label": SCOPE_GROUP_LABELS["related_market_candidates"],
            "label": "관련 시장 예외군",
            "score": cross_kind["score"],
            "penalty_weight": cross_kind["penalty_weight"],
            "strict_same_code": False,
            "include": True,
            "reason": cross_kind["reason"],
        }

    return {
        "bucket": "excluded",
        "scope_bucket": "irrelevant_candidates",
        "scope_bucket_label": SCOPE_GROUP_LABELS["irrelevant_candidates"],
        "label": "검토 제외",
        "score": 0,
        "penalty_weight": 0.0,
        "strict_same_code": False,
        "include": False,
        "reason": "선택한 니스류·상품군·유사군코드와 실질 관련성이 낮아 최종 점수에서는 제외합니다.",
    }
