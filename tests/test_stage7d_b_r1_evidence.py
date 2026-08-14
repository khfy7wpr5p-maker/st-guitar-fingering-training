from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7DBR1EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7d_b_r1_real_rollout_summary.json"
        self.report = json.loads(path.read_text(encoding="utf-8"))

    def test_reproduction_guard_matches_stage7c_r1(self) -> None:
        guard = self.report["reproduction_guard"]
        self.assertTrue(guard["matches_stage7c_r1"])
        self.assertEqual(guard["open_low_events"], 1828)
        self.assertEqual(guard["common_tone_teacher_forced_events"], 1797)
        self.assertAlmostEqual(guard["open_low_event_top1"], 0.7915754923413567)
        self.assertAlmostEqual(guard["common_tone_teacher_forced_event_top1"], 0.7473567056204786)

    def test_self_rollout_is_rejected_against_open_low(self) -> None:
        rollout = self.report["rollout"]
        self.assertFalse(rollout["observed_previous_voicing_in_rollout_features"])
        self.assertLess(rollout["event_weighted_self_rollout_top1"], rollout["event_weighted_always_open_low_top1_same_events"])
        self.assertLess(rollout["self_rollout_delta_vs_open_low"], 0.0)
        self.assertEqual(rollout["family_outcome_vs_open_low"], {"wins": 1, "ties": 1, "losses": 22})
        self.assertEqual(self.report["status"], "FAIL_NO_PROMOTION")
        self.assertFalse(self.report["decision"]["common_tone_self_rollout_promoted"])

    def test_rollout_failure_keeps_training_checkpoint_and_production_closed(self) -> None:
        safety = self.report["safety"]
        self.assertEqual(safety["real_training_rows"], 0)
        self.assertFalse(safety["real_model_fit"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["real_xml_committed_to_git"])

    def test_real_corpus_boundary_is_unchanged(self) -> None:
        corpus = self.report["corpus"]
        self.assertEqual(corpus["unique_admitted_xml"], 33)
        self.assertEqual(corpus["families"], 25)
        self.assertEqual(corpus["chord_events"], 1879)
        self.assertEqual(self.report["rollout"]["evaluated_ambiguous_post_seed_events"], 1797)


if __name__ == "__main__":
    unittest.main()
