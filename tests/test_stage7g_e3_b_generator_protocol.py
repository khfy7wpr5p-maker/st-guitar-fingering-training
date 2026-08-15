from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "stage7g_e3_b_curriculum_generator_protocol.json"


class Stage7GE3BGeneratorProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_protocol_identity_and_target_blind_boundary(self):
        payload = self.payload
        self.assertEqual(payload["schema"], "st-guitar-stage7g-e3-b-generator-protocol-v1")
        self.assertEqual(payload["stage"], "7G-E3-B")
        self.assertEqual(payload["feature_contract"]["raw_feature_count"], 40)
        self.assertTrue(payload["feature_contract"]["difficulty_assignment_target_blind"])
        self.assertFalse(payload["eligibility"]["teacher_response_used"])
        self.assertFalse(payload["eligibility"]["observed_source_tab_used"])
        self.assertFalse(payload["eligibility"]["stage7e_used"])

    def test_selection_and_teacher_blinding_are_preregistered(self):
        selection = self.payload["selection"]
        self.assertTrue(selection["explicit_quota_required_for_every_level"])
        self.assertFalse(selection["data_dependent_default_quotas"])
        self.assertTrue(selection["family_balanced_within_level"])

        teacher = self.payload["teacher_manifest"]
        self.assertTrue(teacher["blind_ab"])
        self.assertTrue(teacher["source_identity_withheld"])
        self.assertTrue(teacher["family_identity_withheld"])
        self.assertTrue(teacher["specialist_identity_withheld"])
        self.assertTrue(teacher["curriculum_level_withheld"])
        self.assertTrue(teacher["feature_values_withheld"])
        self.assertEqual(teacher["responses"], ["A", "B", "EQUAL_OR_UNSURE"])

    def test_rule_supervision_is_not_teacher_preference(self):
        supervision = self.payload["rule_derived_property_supervision"]
        self.assertEqual(supervision["levels"], ["L1", "L2"])
        self.assertFalse(supervision["teacher_gold"])
        self.assertEqual(
            supervision["semantic_boundary"],
            "descriptive_geometry_only_not_guitaristic_preference",
        )

    def test_training_checkpoint_and_production_remain_closed(self):
        boundary = self.payload["scientific_boundary"]
        self.assertFalse(boundary["real_curriculum_batch_generated"])
        self.assertEqual(boundary["new_teacher_labels_collected"], 0)
        self.assertFalse(boundary["model_fit_performed"])
        self.assertFalse(boundary["threshold_tuning"])
        self.assertFalse(boundary["hyperparameter_search"])
        self.assertFalse(boundary["old_556_used_as_fresh_benchmark"])
        self.assertFalse(boundary["first_38_full_candidate_choices_mixed"])
        self.assertFalse(boundary["stage7e_reused"])
        self.assertFalse(boundary["checkpoint_retained"])
        self.assertFalse(boundary["production_integration"])

    def test_manual_colab_policy_requires_identity_checks(self):
        policy = self.payload["execution_policy"]
        self.assertEqual(
            policy["preferred_training_execution"],
            "github_pinned_protocol_plus_manual_colab",
        )
        self.assertTrue(policy["colab_run_requires_exact_git_sha"])
        self.assertTrue(policy["colab_run_requires_input_sha256"])
        self.assertTrue(policy["colab_run_requires_pre_fit_report"])
        self.assertTrue(policy["colab_training_cell_manual"])
        self.assertTrue(policy["aggregate_evidence_returns_to_github"])


if __name__ == "__main__":
    unittest.main()
