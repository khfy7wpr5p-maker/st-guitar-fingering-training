from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_validation import (
    EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
    VALIDATION_BOOTSTRAP_LOWER_INDEX,
    VALIDATION_BOOTSTRAP_UPPER_INDEX,
    verify_validation_evidence,
)


class GuitarSetVoicingValidationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]

    def test_corrected_validation_evidence_is_sealed_pass_and_final_closed(self):
        path = self.root / "evidence/stage7g_e3_guitarset_observed_voicing_validation_v1.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        verify_validation_evidence(evidence)
        self.assertEqual(
            evidence["evidence_sha256"],
            "13b706076205abea42a436d10cf019a36445035e08172054989191121ff59e51",
        )
        self.assertEqual(evidence["status"], "VALIDATION_PASS_FINAL_STILL_CLOSED")
        self.assertTrue(evidence["validation_pass"])
        self.assertEqual(evidence["validation_performer"], "03")
        self.assertEqual(evidence["validation_source_counts"]["ambiguous_voicings"], 1890)
        self.assertEqual(
            evidence["sealed_development_model_artifact_sha256"],
            EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
        )
        self.assertFalse(evidence["model_refit_performed"])
        self.assertFalse(evidence["hyperparameter_tuning_performed"])
        self.assertFalse(evidence["untouched_final_performer_opened"])
        self.assertFalse(evidence["checkpoint_authorized"])
        self.assertFalse(evidence["runtime_connection_authorized"])
        self.assertFalse(evidence["final_access_authorized"])
        self.assertEqual(
            evidence["next_gate"],
            "OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW",
        )

    def test_corrected_bootstrap_uses_preoutcome_literal_indices_and_passes(self):
        evidence = json.loads(
            (self.root / "evidence/stage7g_e3_guitarset_observed_voicing_validation_v1.json").read_text(
                encoding="utf-8"
            )
        )
        bootstrap = evidence["recording_block_bootstrap"]
        self.assertEqual(VALIDATION_BOOTSTRAP_LOWER_INDEX, 49)
        self.assertEqual(VALIDATION_BOOTSTRAP_UPPER_INDEX, 1949)
        self.assertEqual(bootstrap["lower_order_statistic_index_zero_based"], 49)
        self.assertEqual(bootstrap["upper_order_statistic_index_zero_based"], 1949)
        self.assertEqual(bootstrap["repetitions"], 2000)
        self.assertEqual(bootstrap["seed"], 0)
        self.assertGreater(bootstrap["lower_bound"], 0.0)
        self.assertTrue(evidence["gate"]["recording_block_bootstrap_mrr_delta_lower_bound"]["pass"])

    def test_run01_is_permanently_invalidated_and_never_authorizes_gate(self):
        path = self.root / "evidence/stage7g_e3_guitarset_observed_voicing_validation_run01_invalidated_v1.json"
        invalid = json.loads(path.read_text(encoding="utf-8"))
        claimed = invalid.pop("invalidation_record_sha256")
        canonical = json.dumps(invalid, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.assertEqual(sha256(canonical).hexdigest(), claimed)
        self.assertEqual(invalid["status"], "INVALIDATED_IMPLEMENTATION_DEVIATION_DO_NOT_USE_FOR_GATE")
        self.assertEqual(invalid["preoutcome_required_lower_index"], 49)
        self.assertEqual(invalid["observed_run_lower_index"], 50)
        self.assertFalse(invalid["gate_decision_from_this_run_authorized"])
        self.assertFalse(invalid["model_refit_performed"])
        self.assertFalse(invalid["feature_change_performed"])
        self.assertFalse(invalid["hyperparameter_tuning_performed"])
        self.assertFalse(invalid["threshold_change_performed"])
        self.assertFalse(invalid["untouched_final_performer_opened"])


if __name__ == "__main__":
    unittest.main()
