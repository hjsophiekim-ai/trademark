from __future__ import annotations

from nice_catalog import CLASS_CATALOG_PATH, EXCEL_SOURCE_PATH, GROUP_CATALOG_PATH, export_catalog_cache


def main() -> None:
    class_catalog, group_catalog = export_catalog_cache()
    print(f"excel_source={EXCEL_SOURCE_PATH}")
    print(f"class_catalog={CLASS_CATALOG_PATH} ({len(class_catalog)} rows)")
    print(
        "group_catalog="
        f"{GROUP_CATALOG_PATH} "
        f"(goods={len(group_catalog.get('goods', []))}, services={len(group_catalog.get('services', []))})"
    )


if __name__ == "__main__":
    main()
