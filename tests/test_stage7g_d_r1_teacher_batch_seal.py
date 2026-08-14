import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEAL = json.loads((ROOT / "evidence" / "stage7g_d_r1_teacher_batch01_seal.json").read_text())
SOURCE = json.loads((ROOT / "evidence" / "stage7g_c_r1_animetab_batch01_result.json").read_text())


class Stage7GDR1TeacherBatchSealTests(unittest.TestCase):
    def test_batch_is_derived_from_the_accepted_clean_source_pool(self):
        self.assertEqual(SOURCE["status"], "CLEAN_SOURCE_POOL_READY_FOR_BLIND_ANNOTATION")
        self.assertEqual(SEAL["source_batch"]["independent_families"], 40)
        self.assertEqual(SEAL["source_batch"]["eligible_ambiguous_events"], 12714)
        self.assertEqual(SEAL["source_batch"]["open_low_compact_disagreement_events"], 5626)
        self.assertEqual(SEAL["source_batch"]["any_stateless_disagreement_events"], 12358)
        self.assertFalse(SEAL["source_batch"]["stage7e_final_reused"])

    def test_teacher_effort_guard_is_fixed_before_human_labels(self):
        selection = SEAL["annotation_selection"]
        self.assertEqual(selection["teacher_labels_observed_before_selection"], 0)
        self.assertEqual(selection["priority_tier"], "open_low_vs_compact_disagreement_only")
        self.assertEqual(selection["candidate_count_cap"], 20)
        self.assertEqual(selection["selection_input_after_tier_and_candidate_cap"], 3011)
        self.assertEqual(selection["families_with_at_least_15_eligible_events_after_cap"], 40)
        self.assertEqual(selection["selected_tasks"], 600)
        self.assertEqual(selection["selected_families"], 40)
        self.assertEqual(selection["tasks_per_family"], 15)
        self.assertEqual(selection["selected_open_low_compact_disagreement"], 600)
        self.assertEqual(selection["selected_any_stateless_disagreement"], 600)
        self.assertLessEqual(selection["candidate_count_max"], selection["candidate_count_cap"])
        self.assertGreaterEqual(selection["candidate_count_min"], 2)

    def test_teacher_package_is_blind_and_pinned_outside_git(self):
        package = SEAL["teacher_facing_package"]
        sha_pattern = re.compile(r"^[0-9a-f]{64}$")
        self.assertRegex(package["teacher_manifest_sha256"], sha_pattern)
        self.assertRegex(package["package_zip_sha256"], sha_pattern)
        self.assertEqual(package["teacher_manifest_schema"], "st-guitar-stage7g-teacher-task-manifest-v1")
        self.assertFalse(package["raw_musicxml_in_package"])
        self.assertFalse(package["source_identity_in_teacher_manifest"])
        self.assertFalse(package["specialist_predictions_in_teacher_manifest"])
        self.assertFalse(package["observed_source_voicing_in_teacher_manifest"])
        self.assertEqual(package["candidate_order"], "deterministic_physical_candidate_order_not_model_ranked")
        self.assertTrue(package["annotation_ui_local_only"])

    def test_training_checkpoint_and_production_remain_closed(self):
        boundary = SEAL["scientific_boundary"]
        self.assertEqual(boundary["teacher_gold_labels_created"], 0)
        self.assertFalse(boundary["teacher_gold_corpus_gate_passed"])
        self.assertFalse(boundary["teacher_gold_model_fit"])
        self.assertFalse(boundary["training_authorized"])
        self.assertFalse(boundary["checkpoint_retained"])
        self.assertFalse(boundary["production_integration"])
        self.assertFalse(boundary["colab_training_started"])


if __name__ == "__main__":
    unittest.main()
