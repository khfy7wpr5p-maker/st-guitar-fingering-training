from __future__ import annotations

import json
from pathlib import Path
import unittest


class S2ABatch01FirstPassResponseSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = (
            Path(__file__).resolve().parents[1]
            / "evidence"
            / "stage7g_e3_s2a_batch01_first_pass_response_seal.json"
        )
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_all_six_choice_exports_validate_exactly(self):
        self.assertEqual(
            self.data["schema"],
            "st-guitar-stage7g-e3-s2a-batch01-first-pass-response-seal-v1",
        )
        self.assertEqual(self.data["validation"]["status"], "PASS")
        self.assertEqual(self.data["validation"]["actual_tasks"], 720)
        self.assertEqual(self.data["validation"]["unique_task_ids"], 720)
        self.assertEqual(self.data["validation"]["duplicate_task_ids"], 0)
        self.assertTrue(self.data["validation"]["all_session_task_sets_match_sealed_manifests"])
        sessions = self.data["external_inputs"]["sessions"]
        self.assertEqual(len(sessions), 6)
        self.assertTrue(all(row["validation_status"] == "PASS" for row in sessions))
        self.assertTrue(all(row["task_count"] == 120 for row in sessions))
        self.assertTrue(all(row["unique_task_ids"] == 120 for row in sessions))
        self.assertEqual(len({row["choices_sha256"] for row in sessions}), 6)
        self.assertFalse(self.data["external_inputs"]["raw_choice_rows_committed_to_git"])

    def test_response_counts_are_complete_without_coercing_unsure(self):
        responses = self.data["responses"]
        self.assertEqual(responses["A"], 164)
        self.assertEqual(responses["B"], 167)
        self.assertEqual(responses["EQUAL_OR_UNSURE"], 389)
        self.assertEqual(responses["decisive"], 331)
        self.assertEqual(responses["total"], 720)
        self.assertEqual(responses["A"] + responses["B"], responses["decisive"])
        self.assertEqual(responses["decisive"] + responses["EQUAL_OR_UNSURE"], 720)

    def test_frozen_v1_corpus_gate_stays_closed(self):
        gate = self.data["frozen_corpus_gate"]
        self.assertEqual(gate["overall_status"], "FAIL")
        self.assertEqual(gate["decisive_first_pass_pairs"]["observed"], 331)
        self.assertEqual(gate["decisive_first_pass_pairs"]["required_min"], 600)
        self.assertEqual(gate["decisive_first_pass_pairs"]["shortfall"], 269)
        self.assertEqual(gate["FINGER_ONLY_decisive"]["observed"], 139)
        self.assertEqual(gate["FINGER_ONLY_decisive"]["status"], "FAIL")
        self.assertEqual(gate["MIXED_decisive"]["observed"], 192)
        self.assertEqual(gate["MIXED_decisive"]["status"], "PASS")
        self.assertEqual(gate["NEAR_decisive"]["observed"], 128)
        self.assertEqual(gate["MID_decisive"]["observed"], 105)
        self.assertEqual(gate["FAR_decisive"]["observed"], 98)
        self.assertEqual(gate["FAR_decisive"]["status"], "FAIL")

    def test_no_repeat_fit_or_promotion_is_claimed(self):
        reliability = self.data["reliability"]
        self.assertEqual(reliability["status"], "NOT_RUN")
        self.assertTrue(reliability["deferred_until_development_first_pass_corpus_is_complete"])
        boundary = self.data["scientific_boundary"]
        self.assertFalse(boundary["real_model_fit_executed"])
        self.assertFalse(boundary["repeat_reliability_executed"])
        self.assertFalse(boundary["untouched_final_opened"])
        self.assertFalse(boundary["checkpoint_retained"])
        self.assertFalse(boundary["shadow_or_production_integration"])
        self.assertFalse(boundary["historical_teacher_answers_reused_as_labels"])
        self.assertTrue(boundary["source_policy_fit_eligibility_requires_explicit_contract_review_before_any_fit"])


if __name__ == "__main__":
    unittest.main()
