from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7GE3CTeacherBatch01ResponseSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_e3_c_teacher_batch01_response_seal.json"
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_schema_status_and_base(self):
        self.assertEqual(self.data["schema"], "st-guitar-stage7g-e3-c-response-seal-v1")
        self.assertEqual(self.data["stage"], "7G-E3-C")
        self.assertEqual(self.data["status"], "SEALED_TEACHER_BATCH01_RESPONSE_READY_PENDING_MERGE")
        self.assertEqual(self.data["base_main_sha"], "00dea6e5da5fef44ea14a0ae59193ba7deed7b73")

    def test_external_artifacts_are_pinned_but_raw_rows_stay_out_of_git(self):
        external = self.data["external_inputs"]
        self.assertEqual(
            external["choices_sha256"],
            "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e",
        )
        self.assertEqual(
            external["manifest_sha256"],
            "433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2",
        )
        self.assertFalse(external["raw_choices_committed_to_git"])
        self.assertFalse(external["validated_rows_committed_to_git"])

    def test_validation_is_complete_and_exact(self):
        validation = self.data["validation"]
        self.assertEqual(validation["status"], "PASS")
        self.assertEqual(validation["declared_choices"], 400)
        self.assertEqual(validation["actual_choices"], 400)
        self.assertEqual(validation["unique_task_ids"], 400)
        self.assertTrue(validation["exact_manifest_task_set_match"])
        self.assertEqual(validation["duplicate_task_ids"], 0)
        self.assertEqual(validation["missing_task_ids"], 0)
        self.assertEqual(validation["invalid_responses"], 0)
        self.assertTrue(validation["annotation_blinded"])
        self.assertTrue(validation["manifest_sha256_match"])

    def test_blind_and_decoded_counts_are_consistent(self):
        blind = self.data["blind_response_counts"]
        decoded = self.data["decoded_teacher_preference_counts"]
        self.assertEqual(blind, {"A": 201, "B": 198, "EQUAL_OR_UNSURE": 1, "total": 400})
        self.assertEqual(decoded["open_low"], 311)
        self.assertEqual(decoded["compact"], 88)
        self.assertEqual(decoded["EQUAL_OR_UNSURE"], 1)
        self.assertEqual(decoded["decisive"], 399)
        self.assertEqual(decoded["total"], 400)
        self.assertEqual(decoded["open_low"] + decoded["compact"], decoded["decisive"])

    def test_curriculum_level_aggregates_match_sealed_result(self):
        levels = self.data["curriculum_level_results"]
        expected = {
            "L1": (140, 131, 9, 0),
            "L2": (120, 88, 32, 0),
            "L3": (80, 63, 17, 0),
            "L4": (60, 29, 30, 1),
        }
        for level, (tasks, open_low, compact, equal) in expected.items():
            row = levels[level]
            self.assertEqual(row["tasks"], tasks)
            self.assertEqual(row["open_low"], open_low)
            self.assertEqual(row["compact"], compact)
            self.assertEqual(row["equal_or_unsure"], equal)
            self.assertEqual(open_low + compact + equal, tasks)

        self.assertAlmostEqual(levels["L1"]["compact_rate_decisive"], 9 / 140)
        self.assertAlmostEqual(levels["L2"]["compact_rate_decisive"], 32 / 120)
        self.assertAlmostEqual(levels["L3"]["compact_rate_decisive"], 17 / 80)
        self.assertAlmostEqual(levels["L4"]["compact_rate_decisive"], 30 / 59)

    def test_scientific_boundaries_prevent_promotion_claims(self):
        boundary = self.data["scientific_boundary"]
        self.assertEqual(boundary["new_teacher_gold_labels"], 400)
        self.assertEqual(boundary["source_families"], 40)
        self.assertTrue(boundary["development_family_overlap_with_prior_teacher_gold"])
        for key in (
            "untouched_final_validation",
            "eligible_for_final_validation_claim",
            "stage7e_used",
            "model_fit",
            "threshold_tuned",
            "hyperparameters_tuned",
            "checkpoint_retained",
            "production_integration",
            "raw_teacher_rows_committed_to_git",
            "full_candidate_first_38_mixed_into_pairwise_batch",
        ):
            self.assertFalse(boundary[key], key)


if __name__ == "__main__":
    unittest.main()
