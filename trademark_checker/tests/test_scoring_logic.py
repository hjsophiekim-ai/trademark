import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring import evaluate_registration


def run_eval(
    trademark_name: str,
    selected_class: str,
    selected_codes: list[str],
    prior_items: list[dict],
    specific_product: str = "소프트웨어",
    selected_kind: str = "goods",
) -> dict:
    return evaluate_registration(
        trademark_name=trademark_name,
        trademark_type="문자만",
        is_coined=True,
        selected_classes=[selected_class],
        selected_codes=selected_codes,
        prior_items=prior_items,
        selected_fields=[
            {
                "kind": selected_kind,
                "group_id": "test_group",
                "group_label": "테스트 대분류",
                "field_id": "test_field",
                "description": "테스트 상품군",
                "example": specific_product,
                "class_no": f"제{selected_class}류",
                "nice_classes": [int(selected_class)],
                "keywords": [specific_product],
                "similarity_codes": selected_codes,
            }
        ],
        specific_product=specific_product,
    )


class ScoringStatusTests(unittest.TestCase):
    def test_exact_live_blocker_same_code_is_top_risk(self) -> None:
        result = run_eval(
            trademark_name="LexAI",
            selected_class="9",
            selected_codes=["G0901"],
            prior_items=[
                {
                    "applicationNumber": "1",
                    "trademarkName": "LEXAI",
                    "registerStatus": "출원",
                    "classificationCode": "9",
                    "similarityGroupCode": "G0901",
                    "applicantName": "A",
                }
            ],
        )

        top = result["top_prior"][0]
        self.assertEqual(top["mark_identity"], "exact")
        self.assertEqual(top["mark_similarity"], 100)
        self.assertGreaterEqual(top["confusion_score"], 95)
        self.assertTrue(top["counts_toward_final_score"])
        self.assertEqual(top["scope_bucket"], "exact_scope_candidates")
        self.assertLessEqual(result["score"], 18)

    def test_exact_mark_but_irrelevant_scope_is_not_direct_penalty(self) -> None:
        result = run_eval(
            trademark_name="LexAI",
            selected_class="20",
            selected_codes=["G2001"],
            prior_items=[
                {
                    "applicationNumber": "2",
                    "trademarkName": "LEXAI",
                    "registerStatus": "등록",
                    "classificationCode": "9",
                    "similarityGroupCode": "G0901",
                    "applicantName": "B",
                }
            ],
            specific_product="가구",
        )

        self.assertEqual(result["filtered_prior_count"], 0)
        self.assertEqual(result["excluded_prior_count"], 1)
        self.assertEqual(result["excluded_priors"][0]["mark_identity"], "exact")
        self.assertGreaterEqual(result["score"], 88)

    def test_same_class_different_similarity_code_is_secondary_review(self) -> None:
        result = run_eval(
            trademark_name="LexAI",
            selected_class="20",
            selected_codes=["G2001"],
            prior_items=[
                {
                    "applicationNumber": "3",
                    "trademarkName": "LEXAIA",
                    "registerStatus": "등록",
                    "classificationCode": "20",
                    "similarityGroupCode": "G2002",
                    "applicantName": "C",
                }
            ],
            specific_product="가구",
        )

        top = result["top_prior"][0]
        self.assertEqual(top["scope_bucket"], "same_class_candidates")
        self.assertTrue(top["counts_toward_final_score"])
        self.assertGreaterEqual(top["product_similarity_score"], 40)
        self.assertLessEqual(result["score"], 75)

    def test_software_goods_and_class_42_service_use_exception_review(self) -> None:
        result = evaluate_registration(
            trademark_name="LexAI",
            trademark_type="문자만",
            is_coined=True,
            selected_classes=[9],
            selected_codes=["G390802"],
            prior_items=[
                {
                    "applicationNumber": "4",
                    "trademarkName": "LEXAI",
                    "registerStatus": "출원",
                    "classificationCode": "42",
                    "similarityGroupCode": "S420201",
                    "applicantName": "D",
                }
            ],
            selected_fields=[
                {
                    "kind": "goods",
                    "group_id": "electronics_it",
                    "group_label": "전자/IT",
                    "field_id": "software_apps",
                    "description": "소프트웨어/앱",
                    "example": "소프트웨어",
                    "class_no": "제9류",
                    "nice_classes": [9],
                    "keywords": ["소프트웨어", "SaaS", "플랫폼"],
                    "similarity_codes": ["G390802"],
                }
            ],
            specific_product="AI 소프트웨어",
        )

        top = result["top_prior"][0]
        self.assertEqual(top["scope_bucket"], "related_market_candidates")
        self.assertTrue(top["counts_toward_final_score"])
        self.assertGreaterEqual(top["product_similarity_score"], 50)

    def test_historical_only_refusal_does_not_directly_lower_final_score(self) -> None:
        result = run_eval(
            trademark_name="LexAI",
            selected_class="9",
            selected_codes=["G0901"],
            prior_items=[
                {
                    "applicationNumber": "5",
                    "trademarkName": "LEXAI",
                    "registerStatus": "거절",
                    "classificationCode": "9",
                    "similarityGroupCode": "G0901",
                    "applicantName": "E",
                    "reasonSummary": "동일 표장이지만 거절 이력만 존재",
                }
            ],
        )

        top = result["top_prior"][0]
        self.assertFalse(top["counts_toward_final_score"])
        self.assertIn("동일 표장이나 현재 생존 장애물은 아님", top["score_reflection_label"])
        self.assertEqual(result["direct_score_prior_count"], 0)
        self.assertEqual(result["historical_reference_count"], 1)
        self.assertGreaterEqual(result["score"], 88)

    def test_flexaicam_refusal_is_reference_only_for_lexai(self) -> None:
        result = run_eval(
            trademark_name="LexAI",
            selected_class="9",
            selected_codes=["G0901"],
            prior_items=[
                {
                    "applicationNumber": "6",
                    "trademarkName": "FlexAiCam",
                    "registerStatus": "거절",
                    "classificationCode": "9",
                    "similarityGroupCode": "G0901",
                    "applicantName": "F",
                    "reasonSummary": "Flex는 식별력이 약하고 AiCam이 핵심 요부이며 에이캠, 에이켐, ICAM과의 호칭·외관 충돌로 거절",
                    "weakElements": ["Flex"],
                    "refusalCore": "AiCam",
                    "citedMarks": ["에이캠", "에이켐", "ICAM"],
                    "refusalBasis": ["호칭", "외관"],
                    "currentMarkRelevance": "low",
                }
            ],
        )

        top = result["top_prior"][0]
        refusal = top["refusal_analysis"]
        self.assertEqual(refusal["weak_elements"], ["Flex"])
        self.assertEqual(refusal["refusal_core"], "AiCam")
        self.assertEqual(refusal["cited_marks"], ["에이캠", "에이켐", "ICAM"])
        self.assertEqual(refusal["current_mark_relevance"], "low")
        self.assertFalse(top["counts_toward_final_score"])
        self.assertIn("직접 관련 낮음", top["score_reflection_label"])


if __name__ == "__main__":
    unittest.main()
