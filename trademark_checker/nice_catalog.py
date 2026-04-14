from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable


DATA_DIR = Path(__file__).resolve().parent / "data"
CLASS_CATALOG_PATH = DATA_DIR / "nice_class_catalog.json"
GROUP_CATALOG_PATH = DATA_DIR / "nice_group_catalog.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_nice_class_catalog() -> list[dict]:
    rows = _load_json(CLASS_CATALOG_PATH)
    return sorted(rows, key=lambda item: int(item["nice_class_no"]))


@lru_cache(maxsize=1)
def load_nice_group_catalog() -> dict[str, list[dict]]:
    return _load_json(GROUP_CATALOG_PATH)


def get_nice_class_map() -> dict[int, dict]:
    return {int(item["nice_class_no"]): item for item in load_nice_class_catalog()}


def get_groups(kind: str) -> list[dict]:
    return list(load_nice_group_catalog().get(kind, []))


def find_group(kind: str, group_id: str) -> dict | None:
    for group in get_groups(kind):
        if group.get("group_id") == group_id:
            return group
    return None


def flatten_subgroups(kind: str | None = None) -> list[dict]:
    groups_by_kind = load_nice_group_catalog()
    selected_kinds = [kind] if kind else list(groups_by_kind.keys())
    rows: list[dict] = []
    for current_kind in selected_kinds:
        for group in groups_by_kind.get(current_kind, []):
            for subgroup in group.get("subgroups", []):
                rows.append(
                    {
                        "kind": current_kind,
                        "group_id": group["group_id"],
                        "group_label": group["group_label"],
                        "group_icon": group.get("icon", ""),
                        "group_classes": list(group.get("classes", [])),
                        **subgroup,
                    }
                )
    return rows


def dedupe_strings(values: Iterable[str]) -> list[str]:
    seen = set()
    items: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def dedupe_ints(values: Iterable[int | str]) -> list[int]:
    seen = set()
    items: list[int] = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number in seen:
            continue
        seen.add(number)
        items.append(number)
    return sorted(items)


def format_nice_class(number: int | str) -> str:
    return f"제{int(number)}류"


def format_nice_classes(numbers: Iterable[int | str]) -> str:
    classes = dedupe_ints(numbers)
    return ", ".join(format_nice_class(number) for number in classes)


def subgroup_to_field(subgroup: dict) -> dict:
    nice_classes = dedupe_ints(subgroup.get("nice_classes", []))
    keywords = dedupe_strings(subgroup.get("keywords", []))
    similarity_codes = dedupe_strings(subgroup.get("similarity_codes", []))
    return {
        "field_id": subgroup["subgroup_id"],
        "kind": subgroup["kind"],
        "group_id": subgroup["group_id"],
        "group_label": subgroup["group_label"],
        "description": subgroup["subgroup_label"],
        "example": ", ".join(keywords[:3]),
        "class_no": format_nice_classes(nice_classes),
        "nice_classes": nice_classes,
        "keywords": keywords,
        "similarity_codes": similarity_codes,
    }


def selected_group_labels(selected_fields: Iterable[dict]) -> list[str]:
    return dedupe_strings(field.get("group_label", "") for field in selected_fields)


def selected_subgroup_labels(selected_fields: Iterable[dict]) -> list[str]:
    return dedupe_strings(field.get("description", "") for field in selected_fields)


def validate_catalog_coverage() -> dict:
    class_catalog = load_nice_class_catalog()
    class_numbers = {int(item["nice_class_no"]) for item in class_catalog}
    goods_expected = set(range(1, 35))
    services_expected = set(range(35, 46))

    goods_group_classes = set()
    services_group_classes = set()
    for subgroup in flatten_subgroups("goods"):
        goods_group_classes.update(int(value) for value in subgroup.get("nice_classes", []))
    for subgroup in flatten_subgroups("services"):
        services_group_classes.update(int(value) for value in subgroup.get("nice_classes", []))

    group_catalog = load_nice_group_catalog()
    return {
        "goods_class_count": len([item for item in class_catalog if item["kind"] == "goods"]),
        "services_class_count": len([item for item in class_catalog if item["kind"] == "services"]),
        "missing_goods_classes": sorted(goods_expected - class_numbers),
        "missing_services_classes": sorted(services_expected - class_numbers),
        "unmapped_goods_classes": sorted(goods_expected - goods_group_classes),
        "unmapped_services_classes": sorted(services_expected - services_group_classes),
        "group_count_goods": len(group_catalog.get("goods", [])),
        "group_count_services": len(group_catalog.get("services", [])),
    }
