"""니스분류 기반 상품/서비스 검색 매핑."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from nice_catalog import flatten_subgroups, format_nice_classes, get_groups


ALIASES = {
    "쇼핑몰": "패션",
    "온라인몰": "온라인쇼핑몰",
    "앱": "소프트웨어",
    "app": "소프트웨어",
    "saas": "소프트웨어서비스",
    "뷰티": "화장품",
    "코스메틱": "화장품",
    "가방류": "가방",
    "패션": "의류",
    "레스토랑": "카페",
    "병원": "의료서비스",
    "학원": "교육",
}


def _normalize(text: str) -> str:
    return str(text or "").strip().lower().replace(" ", "")


def _score(source: str, target: str) -> float:
    left = _normalize(source)
    right = _normalize(target)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def _subgroup_payload(subgroup: dict, match_score: float = 0.0, matched_keyword: str = "") -> dict[str, Any]:
    return {
        "kind": subgroup["kind"],
        "group_id": subgroup["group_id"],
        "group_label": subgroup["group_label"],
        "group_icon": subgroup.get("group_icon", ""),
        "subgroup_id": subgroup["subgroup_id"],
        "subgroup_label": subgroup["subgroup_label"],
        "nice_classes": list(subgroup.get("nice_classes", [])),
        "nice_class_summary": format_nice_classes(subgroup.get("nice_classes", [])),
        "keywords": list(subgroup.get("keywords", [])),
        "similarity_codes": list(subgroup.get("similarity_codes", [])),
        "match_score": round(match_score, 3),
        "matched_keyword": matched_keyword,
    }


def get_category_suggestions(query: str, kind: str | None = None, limit: int = 6) -> list[dict]:
    if not str(query or "").strip():
        return []

    alias_target = ALIASES.get(_normalize(query), query)
    ranked: list[dict] = []
    seen = set()

    for subgroup in flatten_subgroups(kind):
        targets = [subgroup["subgroup_label"], subgroup["group_label"], *subgroup.get("keywords", [])]
        best_score = 0.0
        best_keyword = ""
        for target in targets:
            score = max(_score(query, target), _score(alias_target, target))
            if score > best_score:
                best_score = score
                best_keyword = target
        if best_score < 0.35:
            continue
        key = subgroup["subgroup_id"]
        if key in seen:
            continue
        seen.add(key)
        ranked.append(_subgroup_payload(subgroup, best_score, best_keyword))

    ranked.sort(
        key=lambda item: (
            -item["match_score"],
            min(item["nice_classes"]) if item["nice_classes"] else 999,
            item["group_label"],
            item["subgroup_label"],
        )
    )
    return ranked[:limit]


def search_products(query: str, kind: str | None = None, limit: int = 6) -> list[dict]:
    return get_category_suggestions(query, kind=kind, limit=limit)


def get_catalog() -> dict[str, list[dict]]:
    return {"goods": get_groups("goods"), "services": get_groups("services")}
