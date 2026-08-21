from __future__ import annotations

from hashlib import sha256
import inspect
import json
from pathlib import Path
import unittest

from st_guitar_fingering_training import guitarset_voicing_final as final
from st_guitar_fingering_training.guitarset_voicing_prereg import protocol_payload


class GuitarSetVoicingFinalTests(unittest.TestCase):
    def test_exact_validation_pass_and_sealed_model_are_required_before_final(self):
        root = Path(__file__).parents[1]
        scorer, model, validation = final.verify_final_open_preconditions(
            validation_evidence_path=root / "evidence/stage7g_e3_guitarset_observed_voicing_validation_v1.json",
            sealed_model_path=root / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json",
        )
        self.assertEqual(validation["evidence_sha256"], final.EXPECTED_VALIDATION_EVIDENCE_SHA256)
        self.assertTrue(validation["validation_pass"])
        self.assertFalse(validation["untouched_final_performer_opened"])
        self.assertEqual(model["artifact_sha256"], final.EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256)
        self.assertEqual(scorer.mean.shape, (28,))

    def test_final_protocol_remains_strictly_positive_and_nonpromoting(self):
        frozen = protocol_payload()["final"]
        self.assertEqual(frozen["performer"], "02")
        self.assertTrue(frozen["no_refit_after_validation"])
        self.assertTrue(frozen["no_tuning_after_open"])
        self.assertEqual(frozen["pass"]["event_top1_delta_vs_baseline_gt"], 0.0)
        self.assertEqual(frozen["pass"]["event_mrr_delta_vs_baseline_gt"], 0.0)
        self.assertEqual(frozen["pass"]["recording_macro_top1_delta_gt"], 0.0)
        self.assertEqual(frozen["pass"]["recording_macro_mrr_delta_gt"], 0.0)
        self.assertEqual(frozen["pass"]["recording_block_bootstrap"]["lower_bound_gt"], 0.0)
        self.assertEqual(frozen["pass_semantics"], "ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY")

    def test_final_gate_requires_every_delta_and_bootstrap_lower_bound_above_zero(self):
        metrics = {
            "event_top1_delta": 0.01,
            "event_mrr_delta": 0.02,
            "recording_macro_top1_delta": 0.03,
            "recording_macro_mrr_delta": 0.04,
        }
        passed, gate = final._final_gate(metrics, {"lower_bound": 0.001})
        self.assertTrue(passed)
        self.assertTrue(all(item["pass"] for item in gate.values()))
        metrics["event_top1_delta"] = 0.0
        passed, gate = final._final_gate(metrics, {"lower_bound": 0.001})
        self.assertFalse(passed)
        self.assertFalse(gate["event_top1_delta"]["pass"])

    def test_final_bootstrap_is_frozen_deterministic_and_uses_literal_indices(self):
        blocks = {"b": (0.3, -0.1), "a": (0.2, 0.4), "c": (0.1, 0.0)}
        first = final.final_recording_block_bootstrap_mrr(blocks)
        second = final.final_recording_block_bootstrap_mrr(dict(reversed(list(blocks.items()))))
        self.assertEqual(first, second)
        self.assertEqual(first["repetitions"], 2000)
        self.assertEqual(first["seed"], 0)
        self.assertEqual(first["lower_order_statistic_index_zero_based"], 49)
        self.assertEqual(first["upper_order_statistic_index_zero_based"], 1949)
        with self.assertRaisesRegex(ValueError, "frozen"):
            final.final_recording_block_bootstrap_mrr(blocks, repetitions=1999)

    def test_final_module_has_no_model_fit_path(self):
        source = inspect.getsource(final)
        self.assertNotIn(".fit(", source)
        self.assertNotIn("LogisticRegression", source)
        self.assertNotIn("training_matrix", source)

    def test_final_open_request_is_preoutcome_sealed_and_keeps_deployment_closed(self):
        root = Path(__file__).parents[1]
        path = root / "evidence/stage7g_e3_guitarset_observed_voicing_final_open_request_v1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        claimed = payload.pop("request_sha256")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.assertEqual(sha256(raw).hexdigest(), claimed)
        self.assertEqual(claimed, "6201314404578ba2c1d1c3dc1e43704b2cd401914583f025700319152edf5338")
        self.assertEqual(payload["status"], "AUTHORIZED_TO_OPEN_UNTOUCHED_FINAL_ONCE")
        self.assertEqual(payload["untouched_final_performer"], "02")
        self.assertEqual(payload["bootstrap"]["lower_order_statistic_index_zero_based"], 49)
        self.assertFalse(payload["checkpoint_authorized"])
        self.assertFalse(payload["runtime_connection_authorized"])
        self.assertFalse(payload["production_authorized"])


if __name__ == "__main__":
    unittest.main()
