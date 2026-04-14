"""등록 가능성 개선 제안."""

from __future__ import annotations

from typing import Iterable, List

from scoring import similarity_percent


def _latin_variants(name: str) -> List[str]:
    base = name.upper().replace(" ", "")
    return [f"{base}Z", f"{base}X", f"{base}IA", f"{base}ONE", f"{base}LAB"]


def _korean_variants(name: str) -> List[str]:
    base = name.replace(" ", "")
    return [f"{base}온", f"{base}리", f"{base}원", f"{base}플러스", f"{base}테크"]


def _name_variants(name: str) -> List[str]:
    if not name.strip():
        return []
    if name.encode("utf-8", errors="ignore").isascii():
        return _latin_variants(name)
    return _korean_variants(name)


def get_improvements(
    trademark_name: str,
    selected_codes: Iterable[str],
    search_results: List[dict],
    current_score: int,
) -> dict:
    """초보 사용자용 개선안 묶음."""
    effective_results = [item for item in search_results if item.get("counts_toward_final_score", True)]
    if not effective_results:
        effective_results = search_results

    name_suggestions = []
    seen = set()
    for index, candidate in enumerate(_name_variants(trademark_name), start=1):
        if candidate in seen:
            continue
        seen.add(candidate)
        max_conflict = 0
        for item in effective_results[:5]:
            baseline = item.get("mark_similarity", item.get("similarity", 0))
            compared = similarity_percent(candidate, item.get("trademarkName", ""))
            max_conflict = max(max_conflict, int(max(baseline, compared)))
        bonus = max(5, 16 - int(max_conflict / 10))
        expected_score = min(96, max(current_score + 1, current_score + bonus - index))
        name_suggestions.append(
            {
                "name": candidate,
                "score": expected_score,
                "reason": "기존 선행상표와 발음·철자를 조금 더 벌리는 대안입니다.",
            }
        )

    selected_codes = list(selected_codes)
    code_suggestions = []
    sale_codes = [code for code in selected_codes if code.startswith("S")]
    goods_codes = [code for code in selected_codes if code.startswith("G")]

    if sale_codes:
        code_suggestions.append(
            {
                "description": f"{', '.join(sale_codes)}와 실제 영업 범위가 일치하는지 점검",
                "reason": "판매업 코드는 보호 범위 정리 목적이 강하므로 실제 충돌 후보가 있는 코드만 유지하는 편이 안전합니다.",
                "expected_score": min(95, current_score + 4),
            }
        )

    if goods_codes:
        code_suggestions.append(
            {
                "description": f"{goods_codes[0]} 중심으로 우선 출원",
                "reason": "처음에는 핵심 지정상품부터 좁게 출원하면 거절 위험을 낮추기 쉽습니다.",
                "expected_score": min(95, current_score + 7),
            }
        )

    class_suggestions = [
        {
            "description": "35류 판매업과 실제 제공 서비스 범위를 다시 점검",
            "reason": "온라인 판매보다 개발·교육·제조가 핵심이면 다른 류 조합이 더 적합할 수 있습니다.",
            "expected_score": min(95, current_score + 8),
        },
        {
            "description": "핵심 업종 1개부터 먼저 출원 후 범위 확장",
            "reason": "초기 충돌 리스크를 줄이고 등록 전략을 단순하게 만들 수 있습니다.",
            "expected_score": min(95, current_score + 5),
        },
    ]

    return {
        "name_suggestions": name_suggestions[:5],
        "code_suggestions": code_suggestions[:3],
        "class_suggestions": class_suggestions[:3],
    }


def build_improvement_plan(
    trademark_name: str,
    current_score: int,
    selected_codes: Iterable[str],
    prior_items: List[dict],
    selected_fields: Iterable[dict],
) -> dict:
    """기존 호환용 래퍼."""
    payload = get_improvements(trademark_name, selected_codes, prior_items, current_score)
    return {
        "name_options": [{"name": item["name"], "expected_score": item["score"]} for item in payload["name_suggestions"]],
        "scope_options": [
            {
                "title": item["description"],
                "description": item["reason"],
                "expected_score": item["expected_score"],
            }
            for item in payload["code_suggestions"]
        ],
        "class_options": [
            {
                "title": item["description"],
                "description": item["reason"],
                "expected_score": item["expected_score"],
            }
            for item in payload["class_suggestions"]
        ],
    }
