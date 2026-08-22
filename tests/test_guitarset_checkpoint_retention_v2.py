from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_checkpoint_retention_v2 import (
    EXPECTED_FINAL_EVIDENCE_SHA256,
    EXPECTED_MODEL_ARTIFACT_SHA256,
    build_checkpoint_retention_decision_v2,
    validate_checkpoint_retention_decision_v2,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
FINAL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_final_v2.json"
DECISION = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_checkpoint_retention_v2.json"
EXPECTED_DECISION_SHA256 = "53f4ea1491b37dfc8360278f852927229f7a3ba6f10a6f8c9a3fb8fb8df80c71"


class GuitarSetCheckpointRetentionV2Tests(unittest.TestCase):
    def test_retention_decision_is_exact_and_reproducible(self):
        built = build_checkpoint_retention_decision_v2(
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        sealed = validate_checkpoint_retention_decision_v2(
            DECISION,
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        self.assertEqual(built, sealed)
        self.assertEqual(sealed["evidence_sha256"], EXPECTED_DECISION_SHA256)
        self.assertEqual(sealed["retained_model_artifact_sha256"], EXPECTED_MODEL_ARTIFACT_SHA256)
        self.assertEqual(sealed["accepted_final_evidence_sha256"], EXPECTED_FINAL_EVIDENCE_SHA256)

    def test_retention_grants_no_execution_or_fret20_quality_authority(self):
        sealed = validate_checkpoint_retention_decision_v2(
            DECISION,
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        self.assertTrue(sealed["checkpoint_retained"])
        self.assertTrue(sealed["checkpoint_retention_authorized"])
        self.assertFalse(sealed["checkpoint_mutation_authorized"])
        self.assertFalse(sealed["refit_authorized"])
        self.assertFalse(sealed["tuning_authorized"])
        self.assertFalse(sealed["validation_reuse_for_training_authorized"])
        self.assertFalse(sealed["final_reuse_for_training_authorized"])
        self.assertFalse(sealed["shadow_integration_authorized"])
        self.assertFalse(sealed["runtime_connection_authorized"])
        self.assertFalse(sealed["production_authorized"])
        self.assertFalse(sealed["fret20_quality_authority"])
        self.assertEqual(sealed["candidate_fret_domain"], [0, 20])
        self.assertEqual(sealed["source_observed_fret_domain"], [0, 19])
        self.assertEqual(sealed["next_gate"], "SHADOW_INTEGRATION_REVIEW")


if __name__ == "__main__":
    unittest.main()
