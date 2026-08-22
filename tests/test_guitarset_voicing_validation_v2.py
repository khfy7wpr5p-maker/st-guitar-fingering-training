from pathlib import Path
import unittest

import numpy as np

from st_guitar_fingering_training.guitarset_voicing_development_v2 import feature_vector_v2
from st_guitar_fingering_training.guitarset_voicing_validation_v2 import (
    EXPECTED_DEVELOPMENT_EVIDENCE_SHA256,
    EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
    load_sealed_development_scorer_v2,
    verify_development_evidence_v2,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
DEVELOPMENT_EVIDENCE = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_v2.json"


class GuitarSetVoicingValidationV2Tests(unittest.TestCase):
    def test_exact_development_prerequisites_are_bound(self):
        evidence = verify_development_evidence_v2(DEVELOPMENT_EVIDENCE)
        scorer, model = load_sealed_development_scorer_v2(MODEL)
        self.assertEqual(evidence["evidence_sha256"], EXPECTED_DEVELOPMENT_EVIDENCE_SHA256)
        self.assertEqual(model["artifact_sha256"], EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256)
        self.assertEqual(evidence["sealed_development_model_artifact_sha256"], model["artifact_sha256"])
        self.assertFalse(model["runtime_connection_authorized"])
        self.assertFalse(model["production_authorized"])
        self.assertFalse(model["fret20_quality_authority"])
        self.assertIsNotNone(scorer)

    def test_inference_only_scorer_can_score_fret20_feature_vector(self):
        scorer, _ = load_sealed_development_scorer_v2(MODEL)
        features = np.asarray([feature_vector_v2(((79, 2, 20), (84, 1, 20)))], dtype=np.float64)
        score = scorer.decision_function(features)
        self.assertEqual(score.shape, (1,))
        self.assertTrue(np.isfinite(score).all())


if __name__ == "__main__":
    unittest.main()
