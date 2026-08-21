from __future__ import annotations

import inspect
from pathlib import Path
import unittest

import numpy as np

import st_guitar_fingering_training.guitarset_voicing_validation as validation
from st_guitar_fingering_training.guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    assert_frozen_protocol,
    protocol_payload,
)


class GuitarSetVoicingValidationTests(unittest.TestCase):
    def test_validation_identity_and_preregistered_gate_are_frozen(self):
        assert_frozen_protocol()
        self.assertEqual(validation.VALIDATION_PERFORMER, "03")
        self.assertEqual(validation.UNTOUCHED_FINAL_PERFORMER, "02")
        self.assertEqual(validation.VALIDATION_BOOTSTRAP_REPETITIONS, 2000)
        self.assertEqual(validation.VALIDATION_BOOTSTRAP_SEED, 0)
        self.assertEqual(validation.VALIDATION_CONFIDENCE, 0.95)
        frozen = protocol_payload()["validation"]
        self.assertEqual(frozen["performer"], "03")
        self.assertEqual(frozen["use"], "ONE_SHOT_GATE_NO_TUNING")
        self.assertEqual(frozen["minimum_ambiguous_events"], 500)
        self.assertEqual(frozen["pass"]["event_top1_delta_vs_baseline_gte"], 0.02)
        self.assertEqual(frozen["pass"]["event_mrr_delta_vs_baseline_gte"], 0.05)
        self.assertEqual(frozen["pass"]["recording_block_bootstrap"]["repetitions"], 2000)
        self.assertEqual(frozen["pass"]["recording_block_bootstrap"]["seed"], 0)

    def test_validation_module_has_no_fit_estimator_path(self):
        source = inspect.getsource(validation)
        self.assertNotIn("LogisticRegression(", source)
        self.assertNotIn(".fit(", source)
        self.assertNotIn("fit_preregistered_model", source)

    def test_sealed_development_artifact_loads_as_inference_only_scorer(self):
        root = Path(__file__).parents[1]
        model_path = root / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json"
        scorer, payload = validation.load_sealed_development_scorer(model_path)
        self.assertEqual(
            payload["artifact_sha256"],
            validation.EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
        )
        self.assertEqual(payload["protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(payload["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertTrue(payload["validation_only_artifact"])
        self.assertFalse(payload["checkpoint_authorized"])
        self.assertFalse(payload["runtime_connection_authorized"])
        zeros = np.zeros((2, 28), dtype=np.float64)
        scores = scorer.decision_function(zeros)
        self.assertEqual(scores.shape, (2,))
        self.assertTrue(np.isfinite(scores).all())
        self.assertAlmostEqual(float(scores[0]), float(scores[1]))

    def test_recording_block_bootstrap_is_exactly_deterministic(self):
        blocks = {
            "r1": (0.10, 0.20, 0.15),
            "r2": (0.08, 0.12),
            "r3": (0.30,),
        }
        first = validation.recording_block_bootstrap_mrr(blocks)
        second = validation.recording_block_bootstrap_mrr(blocks)
        self.assertEqual(first, second)
        self.assertEqual(first["repetitions"], 2000)
        self.assertEqual(first["seed"], 0)
        self.assertEqual(first["lower_order_statistic_index_zero_based"], 49)
        self.assertEqual(first["upper_order_statistic_index_zero_based"], 1949)
        self.assertGreater(first["lower_bound"], 0.0)

    def test_bootstrap_refuses_post_hoc_run_count_or_seed_change(self):
        blocks = {"r1": (0.1,), "r2": (0.2,)}
        with self.assertRaises(ValueError):
            validation.recording_block_bootstrap_mrr(blocks, repetitions=1999)
        with self.assertRaises(ValueError):
            validation.recording_block_bootstrap_mrr(blocks, seed=1)


if __name__ == "__main__":
    unittest.main()
