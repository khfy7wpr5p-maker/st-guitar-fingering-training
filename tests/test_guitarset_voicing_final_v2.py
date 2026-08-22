from pathlib import Path
import json
import unittest

from st_guitar_fingering_training.guitarset_voicing_final_v2 import (
    EXPECTED_VALIDATION_EVIDENCE_SHA256,
    verify_final_evidence_v2,
    verify_final_open_preconditions_v2,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
VALIDATION = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_validation_v2.json"
FINAL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_final_v2.json"
EXPECTED_FINAL_EVIDENCE_SHA256 = "8aab8f841cf2a5e5a6e6437a8f2207026465b1863fdc064629e2818eae6a67b2"


class GuitarSetVoicingFinalV2Tests(unittest.TestCase):
    def test_exact_validation_and_model_are_required(self):
        scorer, model, validation = verify_final_open_preconditions_v2(
            validation_evidence_path=VALIDATION,
            sealed_model_path=MODEL,
        )
        self.assertIsNotNone(scorer)
        self.assertEqual(validation["evidence_sha256"], EXPECTED_VALIDATION_EVIDENCE_SHA256)
        self.assertEqual(validation["sealed_development_model_artifact_sha256"], model["artifact_sha256"])
        self.assertTrue(validation["validation_pass"])
        self.assertFalse(validation["untouched_final_performer_opened"])
        self.assertFalse(validation["model_refit_performed"])
        self.assertFalse(validation["hyperparameter_tuning_performed"])
        self.assertFalse(validation["checkpoint_authorized"])
        self.assertFalse(validation["runtime_connection_authorized"])
        self.assertFalse(validation["production_authorized"])
        self.assertFalse(validation["final_access_authorized"])
        self.assertFalse(validation["fret20_quality_authority"])

    def test_sealed_final_evidence_is_exact_and_non_authoritative(self):
        payload = json.loads(FINAL.read_text(encoding="utf-8"))
        verify_final_evidence_v2(payload)
        self.assertEqual(payload["evidence_sha256"], EXPECTED_FINAL_EVIDENCE_SHA256)
        self.assertEqual(payload["status"], "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY")
        self.assertTrue(payload["final_pass"])
        self.assertTrue(payload["checkpoint_retention_review_eligible"])
        self.assertEqual(payload["accepted_validation_evidence_sha256"], EXPECTED_VALIDATION_EVIDENCE_SHA256)
        self.assertEqual(payload["sealed_development_model_artifact_sha256"], "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314")
        self.assertEqual(payload["final_source_counts"]["observed_fret20_positive_gold_count"], 0)
        self.assertEqual(payload["final_source_counts"]["fret20_candidate_event_count"], 214)
        self.assertGreater(payload["metrics"]["event_top1_delta"], 0.0)
        self.assertGreater(payload["metrics"]["event_mrr_delta"], 0.0)
        self.assertGreater(payload["recording_block_bootstrap"]["lower_bound"], 0.0)
        self.assertFalse(payload["fret20_quality_authority"])
        self.assertFalse(payload["checkpoint_authorized"])
        self.assertFalse(payload["shadow_integration_authorized"])
        self.assertFalse(payload["runtime_connection_authorized"])
        self.assertFalse(payload["production_authorized"])


if __name__ == "__main__":
    unittest.main()
