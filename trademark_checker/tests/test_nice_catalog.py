import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nice_catalog import get_groups, subgroup_to_field, validate_catalog_coverage
from scoring import evaluate_registration
from search_mapper import get_category_suggestions
from similarity_code_db import get_similarity_codes


class NiceCatalogTests(unittest.TestCase):
    def test_all_nice_classes_exist_and_are_mapped(self) -> None:
        coverage = validate_catalog_coverage()
        self.assertEqual(coverage["goods_class_count"], 34)
        self.assertEqual(coverage["services_class_count"], 11)
        self.assertEqual(coverage["missing_goods_classes"], [])
        self.assertEqual(coverage["missing_services_classes"], [])
        self.assertEqual(coverage["unmapped_goods_classes"], [])
        self.assertEqual(coverage["unmapped_services_classes"], [])

    def test_goods_and_services_groups_are_separated(self) -> None:
        goods_groups = get_groups("goods")
        services_groups = get_groups("services")
        self.assertTrue(goods_groups)
        self.assertTrue(services_groups)
        self.assertTrue(all(max(group["classes"]) <= 34 for group in goods_groups))
        self.assertTrue(all(min(group["classes"]) >= 35 for group in services_groups))

    def test_subgroup_selection_is_saved_as_actual_nice_classes(self) -> None:
        group = next(group for group in get_groups("goods") if group["group_id"] == "living_health")
        subgroup = next(item for item in group["subgroups"] if item["subgroup_id"] == "household_cleaning")
        field = subgroup_to_field(
            {"kind": "goods", "group_id": group["group_id"], "group_label": group["group_label"], **subgroup}
        )
        self.assertEqual(field["kind"], "goods")
        self.assertEqual(field["field_id"], "household_cleaning")
        self.assertEqual(field["nice_classes"], [21])
        self.assertEqual(field["description"], "주방/생활/청소용품")

    def test_similarity_code_priority_uses_selected_subgroup_first(self) -> None:
        rows = get_similarity_codes(
            "임의 입력",
            seed_classes=[9],
            seed_keywords=["소프트웨어", "AI"],
            seed_codes=["G0901"],
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0]["code"], "G0901")
        self.assertEqual(rows[0]["seed_source"], "selected_subgroup")

    def test_search_suggestions_can_be_filtered_by_kind(self) -> None:
        rows = get_category_suggestions("카페", kind="services", limit=5)
        self.assertTrue(rows)
        self.assertTrue(all(row["kind"] == "services" for row in rows))

    def test_selected_nice_classes_are_used_in_analysis_filter(self) -> None:
        result = evaluate_registration(
            trademark_name="CleanDay",
            trademark_type="문자만",
            is_coined=True,
            selected_classes=[],
            selected_codes=[],
            prior_items=[
                {
                    "applicationNumber": "21-1",
                    "trademarkName": "CLEANDEY",
                    "registerStatus": "등록",
                    "classificationCode": "21",
                    "similarityGroupCode": "",
                    "applicantName": "A",
                }
            ],
            selected_fields=[
                {
                    "field_id": "household_cleaning",
                    "kind": "goods",
                    "group_id": "living_health",
                    "group_label": "생활/건강",
                    "description": "주방/생활/청소용품",
                    "example": "주방용품, 청소용품",
                    "class_no": "제21류",
                    "nice_classes": [21],
                    "keywords": ["청소용품", "생활용품"],
                    "similarity_codes": [],
                }
            ],
            specific_product="청소용품",
        )
        self.assertEqual(result["filtered_prior_count"], 1)
        self.assertEqual(result["included_priors"][0]["classificationCode"], "21")

    def test_selected_structure_is_exposed_to_analysis(self) -> None:
        result = evaluate_registration(
            trademark_name="CloudLex",
            trademark_type="문자만",
            is_coined=True,
            selected_classes=[42],
            selected_codes=["S420201"],
            prior_items=[],
            selected_fields=[
                {
                    "field_id": "software_platform",
                    "kind": "services",
                    "group_id": "it_science",
                    "group_label": "IT/과학기술",
                    "description": "소프트웨어서비스/SaaS/플랫폼",
                    "example": "SaaS, 플랫폼",
                    "class_no": "제42류",
                    "nice_classes": [42],
                    "keywords": ["소프트웨어서비스", "SaaS", "플랫폼"],
                    "similarity_codes": ["S420201"],
                }
            ],
            specific_product="법률 SaaS",
        )
        self.assertEqual(result["selected_kind"], "services")
        self.assertEqual(result["selected_groups"], ["IT/과학기술"])
        self.assertEqual(result["selected_subgroups"], ["소프트웨어서비스/SaaS/플랫폼"])
        self.assertEqual(result["selected_nice_classes"], [42])
        self.assertEqual(result["selected_similarity_codes"], ["S420201"])


if __name__ == "__main__":
    unittest.main()
