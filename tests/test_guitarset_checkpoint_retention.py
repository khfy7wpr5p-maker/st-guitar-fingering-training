from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from st_guitar_fingering_training.guitarset_checkpoint_retention import (
    EXPECTED_FINAL_EVIDENCE_SHA256,
    EXPECTED_MODEL_ARTIFACT_SHA256,
    build_checkpoint_retention_decision,
    validate_checkpoint_retention_decision,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json"
FINAL = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_final_v1.json"
DECISION = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_checkpoint_retention_v1.json"


class GuitarSetCheckpointRetentionTests(unittest.TestCase):
    def test_retention_decision_rebuilds_exactly_from_sealed_inputs(self):
        rebuilt = build_checkpoint_retention_decision(model_path=MODEL, final_evidence_path=FINAL)
        committed = validate_checkpoint_retention_decision(
            DECISION,
            model_path=MODEL,
            final_evidence_path=FINAL,
        )
        self.assertEqual(committed, rebuilt)
        self.assertEqual(committed["retained_model_artifact_sha256"], EXPECTED_MODEL_ARTIFACT_SHA256)
        self.assertEqual(committed["accepted_final_evidence_sha256"], EXPECTED_FINAL_EVIDENCE_SHA256)

    def test_retention_is_immutable_research_only_and_does_not_open_runtime(self):
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertTrue(decision["checkpoint_retained"])
        self.assertTrue(decision["checkpoint_retention_authorized"])
        for key in (
            "checkpoint_mutation_authorized",
            "refit_authorized",
            "tuning_authorized",
            "validation_reuse_for_training_authorized",
            "final_reuse_for_training_authorized",
            "shadow_integration_authorized",
            "runtime_connection_authorized",
            "production_authorized",
        ):
            self.assertFalse(decision[key], key)
        self.assertEqual(decision["next_gate"], "SHADOW_INTEGRATION_REVIEW")

    def test_source_model_remains_unmodified_and_not_preapproved_for_checkpoint_use(self):
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        self.assertEqual(model["artifact_sha256"], EXPECTED_MODEL_ARTIFACT_SHA256)
        self.assertFalse(model["checkpoint_authorized"])
        self.assertFalse(model["runtime_connection_authorized"])

    def test_tampered_final_evidence_fails_closed(self):
        payload = json.loads(FINAL.read_text(encoding="utf-8"))
        payload["final_pass"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_checkpoint_retention_decision(model_path=MODEL, final_evidence_path=path)

    def test_tampered_model_fails_closed(self):
        payload = json.loads(MODEL.read_text(encoding="utf-8"))
        payload["runtime_connection_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_checkpoint_retention_decision(model_path=path, final_evidence_path=FINAL)


if __name__ == "__main__":
    unittest.main()
