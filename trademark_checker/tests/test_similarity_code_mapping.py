import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nice_catalog import get_groups, subgroup_to_field, derive_selected_scope
from scoring import evaluate_registration
from similarity_code_db import derive_similarity_mapping, get_similarity_codes


FAKE_CODES = {"S3601", "S3602", "S3603"}


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


class SimilarityCodeMappingTests(unittest.TestCase):
    def test_finance_group_maps_to_s0201(self) -> None:
        mapping = derive_similarity_mapping("금융, 통화 및 은행업", class_no=36, seed_classes=[36])
        self.assertEqual(mapping["chosen_codes"], ["S0201"])
        self.assertIn("S120401", mapping["candidate_codes"])
        self.assertNotIn("S3601", mapping["candidate_codes"])

    def test_insurance_group_maps_to_s0301(self) -> None:
        mapping = derive_similarity_mapping("보험서비스업", class_no=36, seed_classes=[36])
        self.assertEqual(mapping["chosen_codes"], ["S0301"])

    def test_real_estate_group_maps_to_s1212(self) -> None:
        mapping = derive_similarity_mapping("부동산업", class_no=36, seed_classes=[36])
        self.assertEqual(mapping["chosen_codes"], ["S1212"])
        self.assertIn("S121201", mapping["candidate_codes"])

    def test_financial_advisory_maps_to_s120401(self) -> None:
        mapping = derive_similarity_mapping("재무상담 서비스", class_no=36, seed_classes=[36])
        self.assertEqual(mapping["chosen_codes"], ["S120401"])

    def test_unmatched_class_36_uses_s173699_fallback(self) -> None:
        mapping = derive_similarity_mapping("핀테크 데이터 인증업", class_no=36, seed_classes=[36])
        self.assertEqual(mapping["chosen_codes"], ["S173699"])
        self.assertTrue(mapping["fallback_used"])
        self.assertEqual(mapping["match_confidence"], "fallback")

    def test_fake_codes_are_never_generated(self) -> None:
        labels = [
            "금융, 통화 및 은행업",
            "보험서비스업",
            "부동산업",
            "재무상담 서비스",
            "핀테크 데이터 인증업",
        ]
        for label in labels:
            mapping = derive_similarity_mapping(label, class_no=36, seed_classes=[36])
            self.assertTrue(FAKE_CODES.isdisjoint(mapping["candidate_codes"]))
            self.assertTrue(FAKE_CODES.isdisjoint(mapping["chosen_codes"]))

    def test_mapping_confidence_and_product_samples_use_real_codes(self) -> None:
        finance = derive_similarity_mapping("금융, 통화 및 은행업", class_no=36, seed_classes=[36])
        cosmetics = derive_similarity_mapping("비의료용 화장품 및 세면용품", class_no=3, seed_classes=[3])
        software = derive_similarity_mapping(
            "기록 및 내려받기 가능한 멀티미디어 파일, 컴퓨터 소프트웨어, 빈 디지털 또는 아날로그 기록 및 저장매체",
            class_no=9,
            seed_classes=[9],
        )
        furniture = derive_similarity_mapping("가구, 거울, 액자", class_no=20, seed_classes=[20])

        self.assertEqual(finance["match_confidence"], "exact")
        self.assertEqual(cosmetics["chosen_codes"], ["G1201"])
        self.assertEqual(software["chosen_codes"], ["G390802"])
        self.assertEqual(furniture["chosen_codes"], ["G2601"])

    def test_derived_similarity_codes_flow_into_review_engine(self) -> None:
        field = _field_by_labels("services", "기타 서비스", "금융, 통화 및 은행업")
        scope = derive_selected_scope(
            "services",
            [field],
            specific_products={field["field_id"]: "재무상담 서비스"},
            code_lookup=get_similarity_codes,
        )

        result = evaluate_registration(
            trademark_name="LexBank",
            trademark_type="문자상표",
            is_coined=True,
            selected_classes=scope["derived_nice_classes"],
            selected_codes=scope["derived_similarity_codes"],
            prior_items=[
                {
                    "applicationNumber": "900",
                    "trademarkName": "LEXBANK",
                    "registerStatus": "출원",
                    "classificationCode": "36",
                    "similarityGroupCode": "S120401",
                    "applicantName": "G",
                }
            ],
            selected_fields=[field],
            specific_product="재무상담 서비스",
        )

        self.assertIn("S0201", scope["derived_similarity_codes"])
        self.assertIn("S120401", scope["derived_similarity_codes"])
        self.assertEqual(result["selected_similarity_codes"], scope["derived_similarity_codes"])
        self.assertGreaterEqual(result["filtered_prior_count"], 1)


if __name__ == "__main__":
    unittest.main()
