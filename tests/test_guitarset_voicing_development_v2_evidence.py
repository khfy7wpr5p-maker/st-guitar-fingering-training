import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_development_v2 import verify_sealed_json
from st_guitar_fingering_training.guitarset_voicing_prereg_v2 import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_v2.json"
MODEL = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
EXPECTED_EVIDENCE_SHA256 = "177cc54ef38c619f475074f9e1c529865772d182a135faf4f4cdf50ee2c64351"
EXPECTED_MODEL_SHA256 = "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314"


class GuitarSetV2DevelopmentEvidenceTests(unittest.TestCase):
    def test_exact_sealed_development_evidence(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        verify_sealed_json(evidence, "evidence_sha256")
        self.assertEqual(evidence["evidence_sha256"], EXPECTED_EVIDENCE_SHA256)
        self.assertTrue(evidence["development_pass"])
        self.assertEqual(evidence["prereg_protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(evidence["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(evidence["candidate_fret_domain"], [0, 20])
        self.assertEqual(evidence["source_observed_fret_domain"], [0, 19])
        self.assertEqual(evidence["development_source_counts"]["observed_fret20_positive_gold_count"], 0)
        self.assertGreater(evidence["development_source_counts"]["fret20_candidate_event_count"], 0)
        self.assertGreater(evidence["development_source_counts"]["fret20_candidate_count_across_all_voicings"], 0)
        self.assertEqual(evidence["gate"]["deterministic_reproduction"]["observed_identical_runs"], 10)
        self.assertEqual(evidence["macro"]["top1_fold_wins"], 4)
        self.assertEqual(evidence["macro"]["mrr_fold_wins"], 4)
        self.assertFalse(evidence["runtime_connection_authorized"])
        self.assertFalse(evidence["production_authorized"])
        self.assertFalse(evidence["validation_access_authorized"])
        self.assertFalse(evidence["final_access_authorized"])
        self.assertFalse(evidence["fret20_quality_authority"])

    def test_exact_sealed_development_model(self):
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        verify_sealed_json(model, "artifact_sha256")
        self.assertEqual(model["artifact_sha256"], EXPECTED_MODEL_SHA256)
        self.assertEqual(model["model_version"], "GUITARSET-OBSERVED-VOICING-MODEL.v2")
        self.assertEqual(model["protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(model["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(model["candidate_fret_domain"], [0, 20])
        self.assertEqual(model["source_observed_fret_domain"], [0, 19])
        self.assertEqual(model["observed_fret20_positive_gold_count"], 0)
        self.assertFalse(model["checkpoint_authorized"])
        self.assertFalse(model["runtime_connection_authorized"])
        self.assertFalse(model["production_authorized"])
        self.assertFalse(model["fret20_quality_authority"])

    def test_evidence_binds_exact_model(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        self.assertEqual(evidence["sealed_development_model_artifact_sha256"], model["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
