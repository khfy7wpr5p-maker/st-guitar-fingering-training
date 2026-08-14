from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7EFinalSealTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7e_final_test_seal.json"
        self.seal = json.loads(path.read_text(encoding="utf-8"))

    def test_final_corpus_is_pinned_and_result_is_pending(self) -> None:
        self.assertEqual(self.seal["status"], "SEALED_RESULT_PENDING")
        corpus = self.seal["external_corpus"]
        self.assertEqual(corpus["repository"], "robust-guitar-tabs/code")
        self.assertEqual(corpus["repository_commit"], "f50309ad06dc734ddae5e3a0eda756fca221e2e7")
        self.assertEqual(corpus["license"], "CC0-1.0")
        self.assertEqual(len(corpus["paths"]), 16)
        self.assertEqual(len({item["git_blob_sha1"] for item in corpus["paths"]}), 16)

    def test_final_contract_forbids_leakage_and_common_tone(self) -> None:
        contract = self.seal["contract"]
        self.assertFalse(contract["development_corpus_allowed_in_final"])
        self.assertFalse(contract["final_targets_allowed_in_any_fit"])
        self.assertFalse(contract["common_tone_included"])
        self.assertEqual(contract["specialists"], ["open_low", "compact", "mid_position", "high_position"])
        self.assertTrue(contract["single_evaluation"])

    def test_final_gate_and_minimum_corpus_are_preregistered(self) -> None:
        contract = self.seal["contract"]
        self.assertEqual(contract["minimum_final_families_with_ambiguous_events"], 8)
        self.assertEqual(contract["minimum_final_ambiguous_events"], 100)
        self.assertEqual(contract["primary_metric"], "event_weighted_router_top1")
        self.assertEqual(contract["primary_baseline"], "event_weighted_always_open_low_top1")
        self.assertIn("router_top1 > always_open_low_top1", contract["promotion_gate"])

    def test_no_checkpoint_or_production_promotion_is_preapproved(self) -> None:
        safety = self.seal["safety"]
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["raw_final_gp3_committed_to_training_repo"])
        self.assertFalse(safety["final_result_read_before_seal"])


if __name__ == "__main__":
    unittest.main()
