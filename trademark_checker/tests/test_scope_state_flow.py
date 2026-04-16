import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nice_catalog import (
    SCOPE_SUBSTEP_GROUP,
    SCOPE_SUBSTEP_REVIEW_READY,
    SCOPE_SUBSTEP_SUBGROUP,
    build_scope_session_state,
    can_enter_subgroup_stage,
    can_run_review,
    find_group,
    should_render_subgroup_stage,
    subgroup_to_field,
)


def _field_from_group(kind: str, group_id: str, class_no: int | None = None) -> dict:
    group = find_group(kind, group_id)
    assert group is not None
    if class_no is None:
        subgroup = group["subgroups"][0]
    else:
        subgroup = next(item for item in group["subgroups"] if class_no in item.get("nice_classes", []))
    return subgroup_to_field(
        {
            "kind": kind,
            "group_id": group["group_id"],
            "group_label": group["group_label"],
            "group_hint": group.get("group_hint", ""),
            **subgroup,
        }
    )


class ScopeStateFlowTests(unittest.TestCase):
    def test_group_click_stores_selected_group_id(self) -> None:
        state = build_scope_session_state(selected_kind="services", selected_group_id="misc_services")
        self.assertEqual(state["selected_group_id"], "misc_services")
        self.assertTrue(state["selected_group_label"])

    def test_group_id_enables_subgroup_move_button(self) -> None:
        self.assertFalse(can_enter_subgroup_stage("services", None))
        self.assertTrue(can_enter_subgroup_stage("services", "misc_services"))

    def test_move_button_click_switches_scope_substep_to_subgroup(self) -> None:
        state = build_scope_session_state(
            selected_kind="services",
            selected_group_id="misc_services",
            current_substep=SCOPE_SUBSTEP_SUBGROUP,
        )
        self.assertEqual(state["step_scope_sub"], SCOPE_SUBSTEP_SUBGROUP)

    def test_subgroup_screen_rendering_follows_scope_substep(self) -> None:
        self.assertFalse(should_render_subgroup_stage(SCOPE_SUBSTEP_GROUP, "services", "misc_services"))
        self.assertTrue(should_render_subgroup_stage(SCOPE_SUBSTEP_SUBGROUP, "services", "misc_services"))

    def test_subgroup_selection_derives_nice_classes(self) -> None:
        field = _field_from_group("services", "misc_services", class_no=36)
        state = build_scope_session_state(
            selected_kind="services",
            selected_group_id="misc_services",
            selected_fields=[field],
            current_substep=SCOPE_SUBSTEP_SUBGROUP,
        )
        self.assertEqual(state["selected_subgroup_ids"], [field["field_id"]])
        self.assertEqual(state["derived_nice_classes"], [36])

    def test_subgroup_selection_derives_similarity_codes(self) -> None:
        field = _field_from_group("services", "misc_services", class_no=36)
        state = build_scope_session_state(
            selected_kind="services",
            selected_group_id="misc_services",
            selected_fields=[field],
            current_substep=SCOPE_SUBSTEP_SUBGROUP,
        )
        self.assertTrue(state["derived_similarity_codes"])

    def test_subgroup_selection_enables_review(self) -> None:
        field = _field_from_group("goods", "living_health")
        state = build_scope_session_state(
            selected_kind="goods",
            selected_group_id="living_health",
            selected_fields=[field],
            current_substep=SCOPE_SUBSTEP_SUBGROUP,
        )
        self.assertEqual(state["step_scope_sub"], SCOPE_SUBSTEP_REVIEW_READY)
        self.assertTrue(can_run_review(state["selected_subgroup_ids"]))

    def test_empty_legacy_selected_codes_do_not_block_subgroup_stage(self) -> None:
        legacy_selected_codes: list[str] = []
        self.assertEqual(legacy_selected_codes, [])
        state = build_scope_session_state(
            selected_kind="services",
            selected_group_id="misc_services",
            current_substep=SCOPE_SUBSTEP_SUBGROUP,
        )
        self.assertEqual(state["step_scope_sub"], SCOPE_SUBSTEP_SUBGROUP)
        self.assertTrue(can_enter_subgroup_stage("services", state["selected_group_id"]))


if __name__ == "__main__":
    unittest.main()
