"""상표 등록 가능성 분석 로직."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List

from goods_scope import classify_product_similarity, normalize_selected_input
from legal_scope import SCOPE_GROUP_LABELS, build_scope_counts
from prior_mark_status import (
    merge_refusal_analysis as merge_refusal_analysis_payload,
    normalize_refusal_analysis as normalize_refusal_analysis_payload,
    status_profile as get_status_profile,
)
from similarity_code_db import get_code_metadata


COMMON_WORDS = {"사랑", "사랑해", "브랜드", "맛있는", "행복", "좋은", "예쁜", "최고"}
ECONOMIC_LINKS = {
    frozenset({"3", "35"}),
    frozenset({"5", "35"}),
    frozenset({"5", "44"}),
    frozenset({"9", "42"}),
    frozenset({"10", "44"}),
    frozenset({"14", "35"}),
    frozenset({"16", "41"}),
    frozenset({"18", "35"}),
    frozenset({"20", "35"}),
    frozenset({"25", "35"}),
    frozenset({"30", "43"}),
    frozenset({"31", "35"}),
    frozenset({"31", "44"}),
    frozenset({"39", "43"}),
}
GROUP_ALIAS = {
    "same_code": "group_exact_code",
    "same_class": "group_same_class",
    "exception": "group_related_market",
    "excluded": "group_irrelevant",
}
GROUP_LABEL = {
    "group_exact_code": "동일 유사군코드",
    "group_same_class": "동일 류",
    "group_related_market": "경제적 견련성 있는 타 류",
    "group_irrelevant": "무관한 타 류",
}
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
        "keywords": ("소멸", "만료"),
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


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _normalize(text: str) -> str:
    cleaned = strip_html(text).lower().strip()
    return "".join(ch for ch in cleaned if ch.isalnum() or ("가" <= ch <= "힣"))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", strip_html(text or "")).lower()


def _clean_class_text(value: str) -> str:
    digits = re.findall(r"\d+", str(value or ""))
    if not digits:
        return ""
    return str(int(digits[0]))


def _extract_classes(value: str | Iterable[int] | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        raw = value.split(",")
    else:
        raw = list(value)

    classes = []
    for item in raw:
        class_no = _clean_class_text(str(item))
        if class_no and class_no not in classes:
            classes.append(class_no)
    return classes


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[0-9A-Za-z가-힣]+", strip_html(text or "").lower())
    return [token for token in tokens if len(token) >= 2]


def _split_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = strip_html(value)
        if not text:
            return []
        parts = re.split(r"[,/;|·\n]+", text)
        return [part.strip(" []()\"'") for part in parts if part.strip(" []()\"'")]
    if isinstance(value, Iterable):
        merged: list[str] = []
        for item in value:
            merged.extend(_split_values(item))
        return _dedupe_preserve(merged)
    return [strip_html(str(value))]


def _dedupe_preserve(values: Iterable[str]) -> list[str]:
    seen = set()
    items: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return items


def _is_sales_code(code: str) -> bool:
    return str(code or "").upper().startswith("S")


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


def _phonetic_similar(a: str, b: str) -> bool:
    """기존 backup/app.py의 단순 발음 유사 규칙을 유지한다."""
    if len(a) < 3 or len(b) < 3:
        return False
    return a[:3] == b[:3] and abs(len(a) - len(b)) <= 2


def _phonetic_similarity_percent(source: str, target: str) -> int:
    left = _compact(source).upper()
    right = _compact(target).upper()
    if not left or not right:
        return 0
    base = similarity_percent(source, target)
    if left == right:
        return 100
    if _phonetic_similar(left, right):
        return max(base, 84)
    if left[:2] == right[:2]:
        return max(base, 72)
    return base


def _concept_similarity_percent(source: str, target: str) -> int:
    left = set(_tokenize(source))
    right = set(_tokenize(target))
    if not left or not right:
        return 0
    if left == right:
        return 100
    overlap = left & right
    if overlap:
        return min(95, 55 + len(overlap) * 15)
    left_text = _normalize(source)
    right_text = _normalize(target)
    if left_text and right_text and (left_text in right_text or right_text in left_text):
        return 70
    return 0


def _mark_similarity(appearance: int, phonetic: int, conceptual: int, trademark_type: str) -> int:
    if trademark_type == "로고만":
        score = appearance * 0.6 + phonetic * 0.2 + conceptual * 0.2
    elif trademark_type == "문자+로고":
        score = appearance * 0.4 + phonetic * 0.4 + conceptual * 0.2
    else:
        score = appearance * 0.25 + phonetic * 0.5 + conceptual * 0.25
    return int(round(score))


def _selected_classes(selected_classes: Iterable[int | str], selected_fields: Iterable[dict]) -> list[str]:
    classes = _extract_classes(selected_classes)
    for field in selected_fields:
        for class_no in _extract_classes(field.get("nice_classes", [])):
            if class_no not in classes:
                classes.append(class_no)
        class_no = _clean_class_text(field.get("class_no", field.get("류", "")))
        if class_no and class_no not in classes:
            classes.append(class_no)
    return classes


def _selected_context(
    selected_classes: Iterable[int | str],
    selected_codes: Iterable[str],
    selected_fields: Iterable[dict],
    specific_product: str,
) -> dict:
    selected_fields = list(selected_fields or [])
    selected_kind = selected_fields[0].get("kind") if selected_fields else None
    normalized = normalize_selected_input(
        selected_kind=selected_kind,
        selected_classes=selected_classes,
        selected_codes=selected_codes,
        selected_fields=selected_fields,
        specific_product_text=specific_product,
    )
    codes = normalized["selected_similarity_codes"]
    code_meta = [get_code_metadata(code) for code in codes]
    code_meta = [row for row in code_meta if row]
    normalized.update(
        {
            "classes": [str(class_no) for class_no in normalized["selected_nice_classes"]],
            "codes": codes,
            "goods_codes": [code for code in codes if not _is_sales_code(code)],
            "sales_codes": [code for code in codes if _is_sales_code(code)],
            "code_meta": code_meta,
            "specific_product": specific_product,
            "field_labels": [field.get("description", field.get("설명", "")) for field in selected_fields],
        }
    )
    return normalized


def _distinctiveness_analysis(
    trademark_name: str,
    is_coined: bool,
    trademark_type: str,
    specific_product: str,
    selected_fields: Iterable[dict],
) -> dict:
    normalized = _normalize(trademark_name)
    reasons: list[str] = []
    score_adjustment = 0

    if is_coined:
        score_adjustment += 18
        reasons.append("조어상표로 입력되어 식별력 측면에서 유리합니다.")
    else:
        score_adjustment -= 8
        reasons.append("일반 단어 계열로 입력되어 식별력은 조어상표보다 약하게 봅니다.")

    if len(normalized) <= 2:
        score_adjustment -= 12
        reasons.append("문자 수가 짧아 제33조 제1항 제6호(간단하고 흔한 표장) 위험이 있습니다.")
    elif len(normalized) >= 6:
        score_adjustment += 3

    if not is_coined and normalized in COMMON_WORDS:
        score_adjustment -= 14
        reasons.append("일상적 표현과 가까워 보통명칭·관용표장으로 보일 위험이 있습니다.")

    name_tokens = set(_tokenize(trademark_name))
    context_tokens = set(_tokenize(specific_product))
    for field in selected_fields:
        context_tokens.update(_tokenize(field.get("description", field.get("설명", ""))))
    descriptive_overlap = sorted(name_tokens & context_tokens)
    if descriptive_overlap and not is_coined:
        score_adjustment -= 10
        reasons.append(
            "지정상품과 직접 맞닿는 표현이 포함되어 성질표시(제33조) 쟁점이 생길 수 있습니다: "
            + ", ".join(descriptive_overlap[:3])
        )

    if trademark_type == "문자+로고":
        score_adjustment += 2
    elif trademark_type == "로고만":
        score_adjustment += 1

    if score_adjustment <= -20:
        label = "거절 가능성 큼"
        level = "high"
    elif score_adjustment < 0:
        label = "식별력 약함"
        level = "medium"
    elif is_coined:
        label = "식별력 문제 없음"
        level = "low"
    else:
        label = "보통 수준"
        level = "low"

    return {
        "label": label,
        "level": level,
        "score_adjustment": score_adjustment,
        "reasons": reasons,
        "summary": reasons[0] if reasons else "식별력상 특별한 약점은 크지 않습니다.",
    }

def _status_profile(status: str) -> dict:
    return get_status_profile(status)


def _mark_identity(source: str, target: str) -> str:
    return "exact" if _compact(source) == _compact(target) else "similar"


def _extract_basis_from_text(text: str) -> list[str]:
    found = []
    for keyword, label in REFUSAL_BASIS_KEYWORDS.items():
        if keyword in text:
            found.append(label)
    return _dedupe_preserve(found)


def _similarity_against_marks(trademark_name: str, marks: Iterable[str]) -> int:
    current = strip_html(trademark_name)
    scores = [similarity_percent(current, mark) for mark in marks if strip_html(mark)]
    return max(scores) if scores else 0


def _infer_relevance(
    trademark_name: str,
    refusal_core: str,
    cited_marks: list[str],
    weak_elements: list[str],
    text: str,
) -> str:
    current = strip_html(trademark_name)
    direct_candidates = [refusal_core] if refusal_core else []
    direct_candidates.extend(cited_marks)
    direct_score = _similarity_against_marks(current, direct_candidates)

    if refusal_core:
        direct_score = max(
            direct_score,
            similarity_percent(current, refusal_core),
            _phonetic_similarity_percent(current, refusal_core),
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


def _normalize_refusal_analysis(item: dict, trademark_name: str) -> dict:
    return normalize_refusal_analysis_payload(
        item=item,
        trademark_name=trademark_name,
        similarity_percent=similarity_percent,
        phonetic_similarity_percent=_phonetic_similarity_percent,
    )


def _merge_refusal_analysis(current: dict, new: dict) -> dict:
    return merge_refusal_analysis_payload(current, new)


def _normalize_prior_item(item: dict, trademark_name: str) -> dict:
    name = strip_html(item.get("trademarkName", item.get("trademark_name", "알 수 없음")))
    classes = _extract_classes(item.get("classificationCode", item.get("class", "")))
    queried_codes = [code for code in item.get("queried_codes", []) if str(code).strip()]
    status_profile = _status_profile(
        item.get("registerStatus", item.get("registrationStatus", item.get("status", "-")))
    )
    refusal_analysis = _normalize_refusal_analysis(item, trademark_name)
    return {
        "trademarkName": name,
        "applicationNumber": item.get("applicationNumber", item.get("application_number", "-")),
        "applicationDate": item.get("applicationDate", item.get("application_date", "-")),
        "registerStatus": status_profile["raw"] or item.get("registerStatus", item.get("registrationStatus", item.get("status", "-"))),
        "status_normalized": status_profile["normalized"],
        "survival_category": status_profile["category"],
        "survival_label": status_profile["survival_label"],
        "counts_toward_final_score": status_profile["counts_toward_final_score"],
        "status_confusion_weight": status_profile["confusion_weight"],
        "status_score_weight": status_profile["score_weight"],
        "applicantName": strip_html(item.get("applicantName", item.get("applicant", "-"))),
        "classificationCode": ",".join(classes) if classes else item.get("classificationCode", item.get("class", "-")),
        "classes": classes,
        "similarity": similarity_percent(trademark_name, name),
        "mark_identity": _mark_identity(trademark_name, name),
        "queried_codes": queried_codes,
        "similarityGroupCode": item.get("similarityGroupCode") or item.get("similarGoodsCode") or "",
        "reason_summary": refusal_analysis["reason_summary"],
        "refusal_analysis": refusal_analysis,
    }


def _status_rank(item: dict) -> tuple[int, float, float]:
    return (
        1 if item.get("counts_toward_final_score") else 0,
        float(item.get("status_score_weight", 0.0)),
        float(item.get("status_confusion_weight", 0.0)),
    )


def _merge_prior_items(items: List[dict], trademark_name: str) -> list[dict]:
    merged: dict[tuple[str, str], dict] = {}
    for item in items:
        normalized = _normalize_prior_item(item, trademark_name)
        key = (normalized["applicationNumber"], normalized["trademarkName"])
        current = merged.get(key)
        if current is None:
            merged[key] = normalized
            continue

        current_codes = set(current.get("queried_codes", []))
        current_codes.update(normalized.get("queried_codes", []))
        current["queried_codes"] = sorted(current_codes)

        current_classes = set(current.get("classes", []))
        current_classes.update(normalized.get("classes", []))
        current["classes"] = sorted(current_classes, key=int)
        current["classificationCode"] = ",".join(current["classes"]) if current["classes"] else current["classificationCode"]
        current["similarity"] = max(current["similarity"], normalized["similarity"])
        current["mark_identity"] = "exact" if "exact" in {current["mark_identity"], normalized["mark_identity"]} else "similar"
        current["refusal_analysis"] = _merge_refusal_analysis(current.get("refusal_analysis", {}), normalized["refusal_analysis"])
        current["reason_summary"] = current["refusal_analysis"].get("reason_summary", "")
        if not current.get("similarityGroupCode") and normalized.get("similarityGroupCode"):
            current["similarityGroupCode"] = normalized["similarityGroupCode"]
        if _status_rank(normalized) > _status_rank(current):
            for key_name in (
                "registerStatus",
                "status_normalized",
                "survival_category",
                "survival_label",
                "counts_toward_final_score",
                "status_confusion_weight",
                "status_score_weight",
            ):
                current[key_name] = normalized[key_name]
    return sorted(
        merged.values(),
        key=lambda row: (
            1 if row["counts_toward_final_score"] else 0,
            1 if row["mark_identity"] == "exact" else 0,
            row["similarity"],
        ),
        reverse=True,
    )


def _has_economic_link(selected_classes: list[str], item_classes: list[str]) -> bool:
    for selected in selected_classes:
        for item_class in item_classes:
            if frozenset({selected, item_class}) in ECONOMIC_LINKS:
                return True
    return False


def _item_code_tokens(code: str) -> set[str]:
    if not code:
        return set()
    row = get_code_metadata(code)
    if not row:
        return set()
    fragments = [row.get("name", ""), row.get("설명", ""), row.get("기준상품", "")]
    return {token for fragment in fragments for token in _tokenize(fragment)}

def _product_similarity(item: dict, context: dict) -> dict:
    product = classify_product_similarity(item, context)
    return {
        **product,
        "group": GROUP_ALIAS[product["bucket"]],
    }


def _enrich_mark_similarity(item: dict, trademark_name: str, trademark_type: str) -> dict:
    if item.get("mark_identity") == "exact":
        appearance = 100
        phonetic = 100
        conceptual = 100
        mark_similarity = 100
    else:
        appearance = item["similarity"]
        phonetic = _phonetic_similarity_percent(trademark_name, item["trademarkName"])
        conceptual = _concept_similarity_percent(trademark_name, item["trademarkName"])
        mark_similarity = _mark_similarity(appearance, phonetic, conceptual, trademark_type)
    return {
        **item,
        "appearance_similarity": appearance,
        "phonetic_similarity": phonetic,
        "conceptual_similarity": conceptual,
        "mark_similarity": mark_similarity,
        "mark_identity_label": "완전 동일" if item.get("mark_identity") == "exact" else "유사",
    }


def _score_reflection_note(item: dict) -> str:
    refusal = item.get("refusal_analysis", {})
    if item.get("counts_toward_final_score"):
        return "최종 점수 반영"
    if item.get("mark_identity") == "exact":
        return "동일 표장이나 현재 생존 장애물은 아님"
    if item.get("status_normalized") == "거절" and refusal.get("reason_summary"):
        if refusal.get("directly_relevant"):
            return "거절이유가 현재 상표와 직접 관련되어 보조 경고만 반영"
        return "거절이유 분석 결과 현재 상표와 직접 관련 낮음"
    return "참고만 하고 점수에는 직접 반영하지 않음"


def _confusion_metrics(item: dict) -> dict:
    product_score = item["product_similarity_score"]
    mark_score = item["mark_similarity"]
    base_confusion = int(round(mark_score * 0.62 + product_score * 0.38))

    if item.get("counts_toward_final_score"):
        confusion_score = int(round(base_confusion * (0.84 + item.get("status_confusion_weight", 0.0) * 0.16)))
    else:
        confusion_score = int(round(base_confusion * (0.48 + item.get("status_confusion_weight", 0.0) * 0.22)))

    if item.get("mark_identity") == "exact" and item.get("product_bucket") == "same_code":
        if item.get("counts_toward_final_score"):
            confusion_score = max(confusion_score, 95)
        else:
            confusion_score = min(max(confusion_score, 62), 74)
    elif item.get("mark_identity") == "exact" and item.get("counts_toward_final_score"):
        confusion_score = max(confusion_score, 88)

    if confusion_score >= 90:
        label = "매우 높음"
    elif confusion_score >= 75:
        label = "높음"
    elif confusion_score >= 60:
        label = "중간"
    else:
        label = "낮음"

    return {
        **item,
        "base_confusion_score": base_confusion,
        "confusion_score": max(0, min(100, confusion_score)),
        "confusion_label": label,
        "score_reflection_label": _score_reflection_note(item),
    }


def _score_from_analysis(
    trademark_name: str,
    candidates: list[dict],
    distinctiveness: dict,
    is_coined: bool,
    trademark_type: str,
) -> int:
    score = 72 + distinctiveness["score_adjustment"]
    normalized = _normalize(trademark_name)

    if trademark_type == "문자+로고":
        score += 2
    elif trademark_type == "로고만":
        score += 1

    if len(normalized) >= 6:
        score += 3
    elif len(normalized) <= 2:
        score -= 8

    if " " in trademark_name.strip():
        score -= 3

    if not is_coined and normalized in COMMON_WORDS:
        score -= 8

    live_candidates = [item for item in candidates if item.get("counts_toward_final_score")]
    for item in live_candidates:
        group_weight = item.get(
            "product_penalty_weight",
            {"same_code": 1.7, "same_class": 1.4, "exception": 0.22}.get(item["product_bucket"], 0.0),
        )
        identity_multiplier = 1.0
        if item.get("mark_identity") == "exact":
            identity_multiplier = 1.28
            if item.get("product_bucket") == "same_code":
                identity_multiplier = 1.42
        penalty = (
            item["mark_similarity"] / 100
            * item["product_similarity_score"] / 100
            * item.get("status_score_weight", 0.0)
            * 45
            * group_weight
            * identity_multiplier
        )
        score -= penalty

    severe_conflict = any(
        item.get("counts_toward_final_score")
        and item["product_similarity_score"] >= 85
        and item["mark_similarity"] >= 90
        and item["confusion_score"] >= 90
        for item in candidates
    )
    if not severe_conflict:
        score = max(score, 12)

    return max(0, min(100, int(round(score))))


def _group_counts(bucket_counts: dict) -> dict:
    scope_counts = build_scope_counts(bucket_counts)
    return {SCOPE_GROUP_LABELS[key]: scope_counts[key] for key in scope_counts}


def _grouped_priors(included: list[dict], excluded: list[dict]) -> dict:
    grouped = {alias: [] for alias in GROUP_LABEL}
    for item in included + excluded:
        grouped[item.get("group_name", GROUP_ALIAS.get(item.get("product_bucket", "excluded"), GROUP_ALIAS["excluded"]))].append(item)
    return grouped


def _build_exclusion_summary(excluded: list[dict]) -> str:
    if not excluded:
        return "상품 유사성 검토에서 제외된 후보가 없습니다."
    reasons = {}
    for item in excluded:
        reason = item.get("product_reason", "상품 관련성 부족")
        reasons[reason] = reasons.get(reason, 0) + 1
    summary = ", ".join(f"{reason} {count}건" for reason, count in list(reasons.items())[:3])
    return (
        f"검색 결과 {len(excluded)}건은 상품 유사성 필터에서 제외되어 최종 점수와 top_prior에는 반영하지 않았습니다. "
        f"주요 제외 사유: {summary}"
    )


def _build_reference_summary(historical_references: list[dict]) -> str:
    if not historical_references:
        return "역사적 참고자료는 확인되지 않았습니다."
    exact_historical = [
        item
        for item in historical_references
        if item.get("mark_identity") == "exact"
    ]
    directly_relevant = [
        item
        for item in historical_references
        if item.get("refusal_analysis", {}).get("directly_relevant")
    ]
    messages = [f"역사적 참고자료 {len(historical_references)}건은 후보 카드에 표시하되 최종 점수에는 직접 반영하지 않았습니다."]
    if exact_historical:
        messages.append("완전 동일한 선행상표가 있으나 현재 상태가 거절/취하/포기/소멸인 경우, 원칙적으로 직접 장애물로 보지 않고 참고자료로만 봅니다.")
    if directly_relevant:
        messages.append("거절 상표는 거절이유의 핵심이 현재 상표와 직접 관련되는 경우에만 보조 경고로 반영합니다.")
    return " ".join(messages)

def _calibrate_score(
    raw_score: int,
    included: list[dict],
    distinctiveness: dict,
    is_coined: bool,
) -> tuple[int, list[str]]:
    explanations = []
    live_blockers = [item for item in included if item.get("counts_toward_final_score")]
    historical_references = [item for item in included if not item.get("counts_toward_final_score")]
    actual_risk_count = sum(1 for item in live_blockers if item.get("confusion_score", 0) >= 65)
    exact_live_same_code = [
        item
        for item in live_blockers
        if item.get("product_bucket") == "same_code" and item.get("mark_identity") == "exact"
    ]
    same_code_high = [
        item
        for item in live_blockers
        if item.get("product_bucket") == "same_code"
        and max(item.get("mark_similarity", 0), item.get("phonetic_similarity", 0)) >= 85
    ]
    same_class_medium = [
        item
        for item in live_blockers
        if item.get("product_bucket") == "same_class"
        and item.get("product_similarity_score", 0) >= 40
        and item.get("mark_similarity", 0) >= 70
    ]
    related_only = bool(live_blockers) and all(item.get("product_bucket") == "exception" for item in live_blockers)

    calibrated = raw_score

    if not live_blockers:
        if distinctiveness["level"] == "high":
            low, high = 60, 72
            explanations.append("식별력 자체가 강하게 약해 실질 장애물이 없어도 60~72 구간에서 점수를 형성했습니다.")
        elif distinctiveness["level"] == "medium":
            low, high = 72, 82
            explanations.append("식별력 약함은 있으나 실질 장애물 선행상표가 없어 72~82 구간으로 보정했습니다.")
        elif is_coined:
            low, high = 88, 95
            explanations.append("조어상표이고 실질 장애물 선행상표가 0건이어서 88~95 구간으로 캘리브레이션했습니다.")
        else:
            low, high = 82, 90
            explanations.append("식별력 보통 이상이며 실질 장애물 선행상표가 0건이어서 82~90 구간으로 캘리브레이션했습니다.")
        calibrated = min(max(calibrated, low), high)
        if historical_references:
            explanations.append(_build_reference_summary(historical_references))
        return calibrated, explanations

    if exact_live_same_code:
        calibrated = min(calibrated, 18)
        explanations.append("등록 또는 출원 상태의 동일 표장이 동일 유사군코드에서 확인되어 최고 위험군으로 반영했습니다.")
    elif same_code_high:
        calibrated = min(calibrated, 45)
        explanations.append("동일 유사군코드에서 호칭/표장 유사도가 높은 실질 장애물이 있어 점수를 강하게 낮췄습니다.")
    elif same_class_medium:
        calibrated = min(max(calibrated, 40), 75)
        explanations.append("동일 류 보조 검토군에서 실질 장애물 후보의 표장 유사도가 중간 이상이라 40~75 구간의 리스크로 보정했습니다.")
    elif related_only:
        lower_bound = 60 if distinctiveness["level"] == "high" else 70
        calibrated = max(calibrated, lower_bound)
        explanations.append("타 류 예외군 실질 장애물만 존재해 과도한 감점을 막고 보조 경고 수준으로 유지했습니다.")

    explanations.append(
        f"상품 유사성 필터 통과 후보 {len(included)}건 중 최종 점수에 직접 반영한 실질 장애물은 {len(live_blockers)}건입니다."
    )
    if historical_references:
        explanations.append(_build_reference_summary(historical_references))
    if actual_risk_count:
        explanations.append(f"실질 장애물 {len(live_blockers)}건 중 실제 충돌 위험 후보는 {actual_risk_count}건입니다.")
    else:
        explanations.append("실질 장애물 후보는 있으나 실제 충돌 위험도는 제한적으로 평가했습니다.")

    return calibrated, explanations


def calculate_score(
    trademark_name: str,
    results: List[dict],
    is_coined: bool,
    trademark_type: str,
) -> int:
    """기존 호환용 점수 함수. 포함 후보만 주어졌다고 보고 계산한다."""
    distinctiveness = _distinctiveness_analysis(
        trademark_name=trademark_name,
        is_coined=is_coined,
        trademark_type=trademark_type,
        specific_product="",
        selected_fields=[],
    )
    candidates = []
    for item in results:
        if item.get("product_bucket") == "excluded":
            continue
        status_profile = _status_profile(item.get("registerStatus", ""))
        enriched = {
            **item,
            "counts_toward_final_score": item.get(
                "counts_toward_final_score", status_profile["counts_toward_final_score"]
            ),
            "status_score_weight": item.get("status_score_weight", status_profile["score_weight"]),
            "mark_similarity": item.get("mark_similarity", item.get("similarity", 0)),
            "product_similarity_score": item.get("product_similarity_score", 62),
            "confusion_score": item.get("confusion_score", item.get("similarity", 0)),
            "product_bucket": item.get("product_bucket", "same_class"),
            "mark_identity": item.get("mark_identity", "similar"),
        }
        candidates.append(enriched)
    return _score_from_analysis(trademark_name, candidates, distinctiveness, is_coined, trademark_type)


def get_score_band(score: int) -> dict:
    if score >= 90:
        return {"label": "등록 가능성 매우 높음", "color": "#4CAF50"}
    if score >= 70:
        return {"label": "등록 가능성 높음", "color": "#2196F3"}
    if score >= 50:
        return {"label": "주의 필요", "color": "#FF9800"}
    if score >= 30:
        return {"label": "등록 어려움", "color": "#F44336"}
    return {"label": "등록 불가 가능성 높음", "color": "#B71C1C"}


def evaluate_registration(
    trademark_name: str,
    trademark_type: str,
    is_coined: bool,
    selected_classes: Iterable[int | str],
    selected_codes: Iterable[str],
    prior_items: List[dict],
    selected_fields: Iterable[dict] | None = None,
    specific_product: str = "",
) -> dict:
    selected_fields = list(selected_fields or [])
    context = _selected_context(selected_classes, selected_codes, selected_fields, specific_product)
    distinctiveness = _distinctiveness_analysis(
        trademark_name=trademark_name,
        is_coined=is_coined,
        trademark_type=trademark_type,
        specific_product=specific_product,
        selected_fields=selected_fields,
    )

    normalized_priors = _merge_prior_items(prior_items, trademark_name)

    included: list[dict] = []
    excluded: list[dict] = []
    bucket_counts = {"same_code": 0, "same_class": 0, "exception": 0, "excluded": 0}

    for item in normalized_priors:
        product = _product_similarity(item, context)
        payload = {
            **item,
            "product_bucket": product["bucket"],
            "scope_bucket": product["scope_bucket"],
            "scope_bucket_label": product["scope_bucket_label"],
            "group_name": product["group"],
            "product_similarity_label": product["label"],
            "product_similarity_score": product["score"],
            "product_penalty_weight": product["penalty_weight"],
            "product_reason": product["reason"],
            "strict_same_code": product["strict_same_code"],
        }
        bucket_counts[product["bucket"]] += 1
        if not product["include"]:
            excluded.append(payload)
            continue
        enriched = _enrich_mark_similarity(payload, trademark_name, trademark_type)
        included.append(_confusion_metrics(enriched))

    included.sort(
        key=lambda row: (
            1 if row.get("counts_toward_final_score") else 0,
            1 if row.get("mark_identity") == "exact" else 0,
            row.get("confusion_score", 0),
            row.get("product_similarity_score", 0),
            1 if row.get("refusal_analysis", {}).get("directly_relevant") else 0,
            row.get("mark_similarity", 0),
            row.get("similarity", 0),
        ),
        reverse=True,
    )
    excluded.sort(
        key=lambda row: (
            1 if row.get("mark_identity") == "exact" else 0,
            row.get("similarity", 0),
        ),
        reverse=True,
    )

    live_blockers = [item for item in included if item.get("counts_toward_final_score")]
    historical_references = [item for item in included if not item.get("counts_toward_final_score")]
    reference_warnings = [
        item
        for item in historical_references
        if item.get("refusal_analysis", {}).get("directly_relevant")
    ]

    raw_score = _score_from_analysis(trademark_name, included, distinctiveness, is_coined, trademark_type)
    score, calibration_notes = _calibrate_score(raw_score, included, distinctiveness, is_coined)
    band = get_score_band(score)
    grouped_counts = _group_counts(bucket_counts)
    scope_counts = build_scope_counts(bucket_counts)
    actual_risk_count = sum(1 for item in live_blockers if item.get("confusion_score", 0) >= 65)
    exclusion_reason_summary = _build_exclusion_summary(excluded)
    reference_summary = _build_reference_summary(historical_references)

    if live_blockers:
        top = live_blockers[0]
        confusion_summary = (
            f"가장 주의할 선행상표는 '{top['trademarkName']}'이며 "
            f"{top['survival_label']}로서 표장 유사도 {top['mark_similarity']}%, "
            f"상품 유사도 {top['product_similarity_score']}%, 상태 반영 후 혼동위험 {top['confusion_score']}%입니다."
        )
    elif historical_references:
        top = historical_references[0]
        confusion_summary = (
            f"상품 유사성 필터를 통과한 후보는 있으나 현재는 '{top['trademarkName']}' 같은 "
            f"{top['survival_label']}만 확인되어 최종 점수에는 직접 반영하지 않았습니다."
        )
    else:
        confusion_summary = "상품 유사성 필터를 통과한 선행상표가 없어 상대적 거절사유 리스크는 낮게 평가됩니다."

    signals = [distinctiveness["summary"]]
    signals.append(
        "상품 유사성 필터 결과: "
        f"실질 충돌 후보 {scope_counts['exact_scope_candidates']}건, "
        f"동일 니스류 보조 검토군 {scope_counts['same_class_candidates']}건, "
        f"상품-서비스업 예외 검토군 {scope_counts['related_market_candidates']}건, "
        f"제외 후보 {scope_counts['irrelevant_candidates']}건"
    )
    signals.append(f"실질 장애물 {len(live_blockers)}건 / 역사적 참고자료 {len(historical_references)}건")
    if included:
        top = included[0]
        signals.append(
            f"상위 후보 '{top['trademarkName']}'는 표장 유사도 {top['mark_similarity']}%, "
            f"상품 유사도 {top['product_similarity_score']}%, 상태 반영 후 혼동위험 {top['confusion_score']}%입니다."
        )
    else:
        signals.append("상품 관련성이 없는 타 류 후보는 강한 감점에 반영하지 않았습니다.")
    signals.extend(calibration_notes)

    return {
        "score": score,
        "raw_score": raw_score,
        "band": band,
        "signals": signals,
        "top_prior": included[:5],
        "included_priors": included,
        "excluded_priors": excluded[:10],
        "live_blockers": live_blockers[:10],
        "historical_references": historical_references[:10],
        "reference_warnings": reference_warnings[:10],
        "prior_count": len(included),
        "filtered_prior_count": len(included),
        "direct_score_prior_count": len(live_blockers),
        "historical_reference_count": len(historical_references),
        "reference_warning_count": len(reference_warnings),
        "excluded_prior_count": len(excluded),
        "actual_risk_prior_count": actual_risk_count,
        "total_prior_count": len(normalized_priors),
        "selected_kind": context.get("selected_kind"),
        "selected_groups": context.get("selected_groups", []),
        "selected_subgroups": context.get("selected_subgroups", []),
        "selected_nice_classes": context.get("selected_nice_classes", []),
        "selected_similarity_codes": context.get("selected_similarity_codes", []),
        "selected_keywords": context.get("selected_keywords", []),
        "specific_product_text": context.get("specific_product_text", specific_product),
        "group_counts": grouped_counts,
        "scope_counts": scope_counts,
        "grouped_priors": _grouped_priors(included[:20], excluded[:20]),
        "exclusion_reason_summary": exclusion_reason_summary,
        "reference_summary": reference_summary,
        "distinctiveness": distinctiveness["label"],
        "distinctiveness_analysis": distinctiveness,
        "product_similarity_analysis": {
            "summary": (
                f"선행상표 {len(normalized_priors)}건 중 "
                f"실질 충돌 후보 {scope_counts['exact_scope_candidates']}건, "
                f"동일 니스류 보조 검토군 {scope_counts['same_class_candidates']}건, "
                f"상품-서비스업 예외 검토군 {scope_counts['related_market_candidates']}건만 본격 검토했고 "
                f"제외 후보 {scope_counts['irrelevant_candidates']}건은 감점에서 제외했습니다. "
                f"이 중 실질 장애물 {len(live_blockers)}건, 역사적 참고자료 {len(historical_references)}건입니다."
            ),
            "bucket_counts": bucket_counts,
            "scope_counts": scope_counts,
            "group_counts": grouped_counts,
            "filtered_prior_count": len(included),
            "direct_score_prior_count": len(live_blockers),
            "historical_reference_count": len(historical_references),
            "excluded_prior_count": len(excluded),
            "exclusion_reason_summary": exclusion_reason_summary,
            "reference_summary": reference_summary,
        },
        "mark_similarity_analysis": {
            "summary": (
                f"표장 유사도는 기존 발음·호칭·외관·관념·문자열 로직을 유지하되, 상품 유사성 필터를 통과한 {len(included)}건에 대해서만 강하게 반영했습니다. "
                f"완전 동일 표장은 {sum(1 for item in included if item.get('mark_identity') == 'exact')}건입니다."
                if included
                else "상품 유사성 필터를 통과한 후보가 없어 외관·호칭·관념 유사도는 참고 수준으로만 보았습니다."
            ),
            "actual_risk_prior_count": actual_risk_count,
        },
        "confusion_analysis": {
            "summary": confusion_summary,
            "highest_confusion_score": included[0]["confusion_score"] if included else 0,
            "actual_risk_prior_count": actual_risk_count,
            "direct_score_prior_count": len(live_blockers),
            "historical_reference_count": len(historical_references),
        },
        "score_explanation": {
            "summary": " / ".join(calibration_notes) if calibration_notes else "최종 점수는 실질 장애물만 직접 반영했습니다.",
            "raw_score": raw_score,
            "final_score": score,
            "notes": calibration_notes,
        },
    }
