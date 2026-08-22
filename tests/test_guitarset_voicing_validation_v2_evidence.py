import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_validation_v2 import verify_validation_evidence_v2


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_validation_v2.json"
EXPECTED_EVIDENCE_SHA256 = "2df8a41bf9c319c481984d116b473ebb78a4569faf36b2a5ec3a883f6b96d987"


class GuitarSetV2ValidationEvidenceTests(unittest.TestCase):
    def test_exact_one_shot_validation_evidence_is_sealed(self):
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        verify_validation_evidence_v2(payload)
        self.assertEqual(payload["evidence_sha256"], EXPECTED_EVIDENCE_SHA256)
        self.assertEqual(payload["status"], "VALIDATION_PASS_FINAL_STILL_CLOSED")
        self.assertTrue(payload["validation_pass"])
        self.assertEqual(payload["validation_performer"], "03")
        self.assertTrue(payload["validation_performer_opened"])
        self.assertFalse(payload["untouched_final_performer_opened"])
        self.assertFalse(payload["model_refit_performed"])
        self.assertFalse(payload["hyperparameter_tuning_performed"])
        self.assertFalse(payload["checkpoint_authorized"])
        self.assertFalse(payload["runtime_connection_authorized"])
        self.assertFalse(payload["production_authorized"])
        self.assertFalse(payload["final_access_authorized"])
        self.assertFalse(payload["fret20_quality_authority"])

    def test_all_preregistered_validation_gates_pass(self):
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertTrue(all(item["pass"] for item in payload["gate"].values()))
        self.assertEqual(payload["recording_block_bootstrap"]["repetitions"], 2000)
        self.assertEqual(payload["recording_block_bootstrap"]["seed"], 0)
        self.assertEqual(payload["recording_block_bootstrap"]["lower_order_statistic_index_zero_based"], 49)
        self.assertGreater(payload["recording_block_bootstrap"]["lower_bound"], 0.0)
        self.assertEqual(payload["validation_source_counts"]["observed_fret20_positive_gold_count"], 0)
        self.assertGreater(payload["validation_source_counts"]["fret20_candidate_event_count"], 0)
        self.assertGreater(payload["metrics"]["event_top1_delta"], 0.02)
        self.assertGreater(payload["metrics"]["event_mrr_delta"], 0.05)


if __name__ == "__main__":
    unittest.main()
