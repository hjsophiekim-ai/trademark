import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nice_catalog import (
    EXCEL_SOURCE_PATH,
    build_selection_summary,
    can_continue_to_code_selection,
    can_enter_subgroup_stage,
    flatten_subgroups,
    get_group_cards,
    get_groups,
    load_nice_class_catalog,
    subgroup_to_field,
    validate_catalog_coverage,
)


def _field_by_labels(kind: str, group_label: str, subgroup_label: str) -> dict:
    group = next(group for group in get_groups(kind) if group["group_label"] == group_label)
    subgroup = next(item for item in group["subgroups"] if item["subgroup_label"] == subgroup_label)
    return subgroup_to_field(
        {
            "kind": kind,
            "group_id": group["group_id"],
            "group_label": group["group_label"],
            "group_hint": group.get("group_hint", ""),
            **subgroup,
        }
    )


class NiceCatalogTests(unittest.TestCase):
    def test_excel_source_covers_all_nice_classes_and_subgroups(self) -> None:
        self.assertTrue(EXCEL_SOURCE_PATH.exists())
        coverage = validate_catalog_coverage()
        self.assertEqual(coverage["goods_class_count"], 34)
        self.assertEqual(coverage["services_class_count"], 11)
        self.assertEqual(coverage["missing_goods_classes"], [])
        self.assertEqual(coverage["missing_services_classes"], [])
        self.assertEqual(coverage["unmapped_goods_classes"], [])
        self.assertEqual(coverage["unmapped_services_classes"], [])
        self.assertEqual(coverage["empty_subgroup_classes"], [])

    def test_each_loaded_class_is_marked_as_excel_source(self) -> None:
        class_catalog = load_nice_class_catalog()
        self.assertEqual(len(class_catalog), 45)
        self.assertTrue(all(row["source"] == "excel" for row in class_catalog))

    def test_group_cards_hide_long_class_heading(self) -> None:
        goods_cards = get_group_cards("goods")
        services_cards = get_group_cards("services")
        self.assertTrue(goods_cards)
        self.assertTrue(services_cards)
        self.assertTrue(all("class_heading" not in card for card in goods_cards + services_cards))
        self.assertTrue(all(len(card["group_label"]) <= 20 for card in goods_cards + services_cards))

    def test_group_cards_are_short_mobile_categories(self) -> None:
        goods_labels = {card["group_label"] for card in get_group_cards("goods")}
        services_labels = {card["group_label"] for card in get_group_cards("services")}
        self.assertIn("생활/건강", goods_labels)
        self.assertIn("소프트웨어", goods_labels)
        self.assertIn("기타 서비스", services_labels)
        self.assertIn("교육/유아/반려동물", services_labels)

    def test_group_selection_moves_to_subgroup_stage(self) -> None:
        first_goods_group = get_group_cards("goods")[0]
        self.assertFalse(can_enter_subgroup_stage(None, None))
        self.assertFalse(can_enter_subgroup_stage("goods", None))
        self.assertTrue(can_enter_subgroup_stage("goods", first_goods_group["group_id"]))

    def test_subgroup_selection_controls_next_button_state(self) -> None:
        self.assertFalse(can_continue_to_code_selection([]))
        field = _field_by_labels("goods", "생활/건강", "표백제 및 기타 세탁용 제제")
        self.assertTrue(can_continue_to_code_selection([field]))

    def test_selection_summary_saves_actual_subgroup_and_nice_class(self) -> None:
        first = _field_by_labels("services", "기타 서비스", "금융, 통화 및 은행업")
        second = _field_by_labels("services", "기타 서비스", "보험서비스업")
        summary = build_selection_summary("services", [first, second])
        self.assertEqual(summary["selected_kind_label"], "서비스")
        self.assertEqual(summary["selected_groups"], ["기타 서비스"])
        self.assertEqual(summary["selected_subgroups"], ["금융, 통화 및 은행업", "보험서비스업"])
        self.assertEqual(summary["selected_nice_classes"], [36])

    def test_selected_subgroup_keeps_similarity_codes(self) -> None:
        field = _field_by_labels("goods", "소프트웨어", "컴퓨터 및 컴퓨터주변기기")
        self.assertEqual(field["nice_classes"], [9])
        self.assertEqual(field["similarity_codes"], ["G390802", "G0901", "G0903"])

    def test_goods_and_services_share_same_step_flow_helpers(self) -> None:
        goods_group_id = get_group_cards("goods")[0]["group_id"]
        services_group_id = get_group_cards("services")[0]["group_id"]
        self.assertTrue(can_enter_subgroup_stage("goods", goods_group_id))
        self.assertTrue(can_enter_subgroup_stage("services", services_group_id))

    def test_requested_example_flows_exist(self) -> None:
        living_health = next(group for group in get_groups("goods") if group["group_label"] == "생활/건강")
        misc_services = next(group for group in get_groups("services") if group["group_label"] == "기타 서비스")
        education_services = next(group for group in get_groups("services") if group["group_label"] == "교육/유아/반려동물")

        living_labels = [row["subgroup_label"] for row in living_health["subgroups"]]
        misc_labels = [row["subgroup_label"] for row in misc_services["subgroups"]]
        edu_labels = [row["subgroup_label"] for row in education_services["subgroups"]]

        self.assertIn("표백제 및 기타 세탁용 제제", living_labels)
        self.assertIn("세정/광택 및 연마재", living_labels)
        self.assertIn("금융, 통화 및 은행업", misc_labels)
        self.assertIn("보험서비스업", misc_labels)
        self.assertIn("교육업", edu_labels)

    def test_flatten_subgroups_still_exposes_internal_filter_inputs(self) -> None:
        rows = flatten_subgroups("services")
        finance = next(row for row in rows if row["subgroup_label"] == "금융, 통화 및 은행업")
        self.assertEqual(finance["group_label"], "기타 서비스")
        self.assertEqual(finance["nice_classes"], [36])
        self.assertIn("keywords", finance)


if __name__ == "__main__":
    unittest.main()
