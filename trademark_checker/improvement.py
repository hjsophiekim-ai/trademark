"""등록 가능성을 높이는 개선안 생성."""

from __future__ import annotations

from typing import Iterable, List

from scoring import similarity_percent


def _normalize(text: str) -> str:
    return text.strip().upper().replace(" ", "")


def _variant_bases(name: str) -> List[str]:
    base = _normalize(name)
    if not base:
        return []

    candidates = [
        f"{base}Z",
        f"{base}X",
        f"{base}A",
        f"{base}ONE",
        f"{base}LAB",
        f"{base}MATE",
    ]
    deduped = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def generate_name_improvements(name: str, current_score: int, prior_items: List[dict]) -> List[dict]:
    suggestions = []
    for index, variant in enumerate(_variant_bases(name), start=1):
        conflict = 0
        for item in prior_items[:5]:
            conflict = max(conflict, similarity_percent(variant, item.get("trademarkName", "")))
        bonus = max(4, 15 - int(conflict / 12))
        expected = max(current_score + bonus - index, current_score + 1)
        suggestions.append({"name": variant, "expected_score": min(96, expected)})
    return suggestions[:5]


def generate_scope_improvements(selected_codes: Iterable[str], current_score: int, prior_items: List[dict]) -> List[dict]:
    codes = list(selected_codes)
    improvements = []
    sale_codes = [code for code in codes if code.startswith("S")]
    goods_codes = [code for code in codes if code.startswith("G")]

    if sale_codes:
        improvements.append(
            {
                "title": "판매업 코드 일부 제외",
                "expected_score": min(95, current_score + 10),
                "description": f"{', '.join(sale_codes)}를 제외하면 판매업 충돌을 줄여 점수가 올라갈 수 있습니다.",
            }
        )

    if goods_codes:
        improvements.append(
            {
                "title": "핵심 상품 코드만 유지",
                "expected_score": min(95, current_score + 7),
                "description": f"{goods_codes[0]} 중심으로 출원하면 범위는 좁아지지만 충돌 위험은 낮아집니다.",
            }
        )

    if any("43" in str(item.get("classificationCode", "")) for item in prior_items):
        improvements.append(
            {
                "title": "다른 서비스군 검토",
                "expected_score": min(95, current_score + 12),
                "description": "현재 음식점/판매업 충돌이 많다면 인접 서비스군 검토가 필요합니다.",
            }
        )

    return improvements[:3]


def build_improvement_plan(
    trademark_name: str,
    current_score: int,
    selected_codes: Iterable[str],
    prior_items: List[dict],
) -> dict:
    return {
        "name_options": generate_name_improvements(trademark_name, current_score, prior_items),
        "scope_options": generate_scope_improvements(selected_codes, current_score, prior_items),
    }
