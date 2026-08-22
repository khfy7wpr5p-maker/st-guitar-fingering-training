from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_final_v2 import (
    EXPECTED_VALIDATION_EVIDENCE_SHA256,
    verify_final_open_preconditions_v2,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
VALIDATION = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_validation_v2.json"


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


if __name__ == "__main__":
    unittest.main()
