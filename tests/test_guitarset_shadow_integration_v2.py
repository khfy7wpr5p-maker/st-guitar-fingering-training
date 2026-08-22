from pathlib import Path
import json
import unittest

from st_guitar_fingering_training.guitarset_shadow_integration_v2 import (
    EXPECTED_REVIEW_EVIDENCE_SHA256,
    build_shadow_integration_review_v2,
    validate_shadow_integration_review_v2,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
FINAL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_final_v2.json"
RETENTION = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_checkpoint_retention_v2.json"
REVIEW = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_shadow_integration_review_v2.json"


class GuitarSetShadowIntegrationV2Tests(unittest.TestCase):
    def test_review_reproduces_from_exact_retained_checkpoint(self):
        review = validate_shadow_integration_review_v2(
            REVIEW,
            retention_decision_path=RETENTION,
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        self.assertEqual(review["evidence_sha256"], EXPECTED_REVIEW_EVIDENCE_SHA256)
        self.assertEqual(review["candidate_fret_domain"], [0, 20])
        self.assertEqual(review["runtime_candidate_contract"]["maximum_fret"], 20)
        self.assertTrue(review["compatibility"]["fret_domain_exact_match"])
        self.assertTrue(review["fret20_candidate_scoring_authorized"])
        self.assertFalse(review["fret20_quality_authority"])
        self.assertTrue(review["shadow_integration_authorized"])
        self.assertTrue(review["offline_node_adapter_implementation_authorized"])
        self.assertFalse(review["shadow_execution_authorized"])
        self.assertFalse(review["live_or_user_input_authorized"])
        self.assertFalse(review["authoritative_decision_effect_authorized"])
        self.assertFalse(review["canonical_result_effect_authorized"])
        self.assertFalse(review["runtime_connection_authorized"])
        self.assertFalse(review["production_authorized"])

    def test_review_builder_keeps_candidate_authority_immutable(self):
        review = build_shadow_integration_review_v2(
            retention_decision_path=RETENTION,
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        policy = review["mandatory_offline_adapter_policy"]
        self.assertTrue(policy["complete_candidate_set_required"])
        self.assertTrue(policy["no_candidate_filtering"])
        self.assertTrue(policy["no_candidate_generation"])
        self.assertTrue(policy["no_candidate_mutation"])
        self.assertFalse(policy["optimizer_decision_effect"])
        self.assertFalse(policy["canonical_result_effect"])
        self.assertFalse(policy["tab_output_effect"])
        self.assertTrue(policy["require_node_python_score_parity_before_controlled_offline_execution"])

    def test_sealed_review_does_not_smuggle_runtime_authority(self):
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        forbidden_true = (
            "shadow_execution_authorized",
            "live_or_user_input_authorized",
            "authoritative_decision_effect_authorized",
            "canonical_result_effect_authorized",
            "checkpoint_mutation_authorized",
            "refit_authorized",
            "tuning_authorized",
            "runtime_connection_authorized",
            "production_authorized",
            "fret20_quality_authority",
        )
        for field in forbidden_true:
            self.assertIs(review[field], False, field)


if __name__ == "__main__":
    unittest.main()
