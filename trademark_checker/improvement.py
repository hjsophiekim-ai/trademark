"""등록 가능성을 높이기 위한 개선안을 만든다."""

from __future__ import annotations

from typing import Iterable, List

from scoring import similarity_percent


def _normalize(text: str) -> str:
    return text.strip()


def _latin_name_variants(name: str) -> List[str]:
    base = name.upper().replace(" ", "")
    return [f"{base}Z", f"{base}X", f"{base}IA", f"{base}ONE", f"{base}LAB"]


def _korean_name_variants(name: str) -> List[str]:
    base = name.replace(" ", "")
    return [f"{base}온", f"{base}리", f"{base}랩", f"{base}플러스", f"{base}앤코"]


def _variant_candidates(name: str) -> List[str]:
    clean = _normalize(name)
    if not clean:
        return []
    if clean.encode("utf-8", errors="ignore").isascii():
        return _latin_name_variants(clean)
    return _korean_name_variants(clean)


def generate_name_improvements(name: str, current_score: int, prior_items: List[dict]) -> List[dict]:
    suggestions = []
    seen = set()
    for index, variant in enumerate(_variant_candidates(name), start=1):
        if variant in seen:
            continue
        seen.add(variant)
        max_conflict = 0
        for item in prior_items[:5]:
            max_conflict = max(max_conflict, similarity_percent(variant, item.get("trademarkName", "")))
        bonus = max(5, 16 - int(max_conflict / 10))
        expected_score = min(96, max(current_score + 1, current_score + bonus - index))
        suggestions.append({"name": variant, "expected_score": expected_score})
    return suggestions[:5]


def generate_scope_improvements(selected_codes: Iterable[str], current_score: int, prior_items: List[dict]) -> List[dict]:
    codes = list(selected_codes)
    results = []
    sale_codes = [code for code in codes if code.startswith("S")]
    goods_codes = [code for code in codes if code.startswith("G")]

    if sale_codes:
        results.append(
            {
                "title": "판매업 코드 제외",
                "expected_score": min(95, current_score + 10),
                "description": f"{', '.join(sale_codes)}를 제외하면 판매업 충돌 가능성을 줄일 수 있습니다.",
            }
        )

    if goods_codes:
        results.append(
            {
                "title": "핵심 상품 코드만 우선 출원",
                "expected_score": min(95, current_score + 7),
                "description": f"{goods_codes[0]} 중심으로 범위를 좁히면 충돌 위험을 낮출 수 있습니다.",
            }
        )

    if any("43" in str(item.get("classificationCode", "")) for item in prior_items):
        results.append(
            {
                "title": "서비스업 범주 재검토",
                "expected_score": min(95, current_score + 12),
                "description": "43류 충돌이 많다면 42류 등 인접 서비스군으로 전략을 다시 볼 수 있습니다.",
            }
        )

    return results[:3]


def generate_class_improvements(selected_fields: Iterable[dict], current_score: int) -> List[dict]:
    fields = list(selected_fields)
    class_numbers = {field["class_no"] for field in fields}
    options = []

    if "35류" in class_numbers:
        options.append(
            {
                "title": "35류 대신 다른 서비스군 검토",
                "expected_score": min(95, current_score + 9),
                "description": "소매업 대신 실제 서비스 제공 중심이라면 42류, 41류 등으로 조정할 수 있습니다.",
            }
        )

    if "43류" in class_numbers:
        options.append(
            {
                "title": "43류와 제품류 분리 출원",
                "expected_score": min(95, current_score + 6),
                "description": "카페/음식점업과 커피 상품류를 분리해서 접근하면 충돌 분석이 더 명확해집니다.",
            }
        )

    if not options:
        options.append(
            {
                "title": "핵심 업종부터 우선 출원",
                "expected_score": min(95, current_score + 5),
                "description": "처음에는 가장 중요한 업종 1개만 먼저 출원하고 이후 확대하는 방식도 가능합니다.",
            }
        )

    return options[:2]


def build_improvement_plan(
    trademark_name: str,
    current_score: int,
    selected_codes: Iterable[str],
    prior_items: List[dict],
    selected_fields: Iterable[dict],
) -> dict:
    return {
        "name_options": generate_name_improvements(trademark_name, current_score, prior_items),
        "scope_options": generate_scope_improvements(selected_codes, current_score, prior_items),
        "class_options": generate_class_improvements(selected_fields, current_score),
    }
