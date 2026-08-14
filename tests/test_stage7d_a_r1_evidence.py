from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7DAR1EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7d_a_r1_real_router_summary.json"
        self.report = json.loads(path.read_text(encoding="utf-8"))

    def test_router_result_beats_open_low_without_target_feature_leakage(self) -> None:
        router = self.report["router"]
        self.assertTrue(router["family_isolated"])
        self.assertFalse(router["observed_target_in_features"])
        self.assertFalse(router["common_tone_included"])
        self.assertGreater(router["macro_router_top1"], router["macro_always_open_low_top1"])
        self.assertGreater(router["event_weighted_router_top1"], router["event_weighted_always_open_low_top1"])

    def test_router_evidence_preserves_real_corpus_boundary_and_reproduction_guard(self) -> None:
        corpus = self.report["corpus"]
        self.assertEqual(corpus["unique_admitted_xml"], 33)
        self.assertEqual(corpus["broad_families"], 25)
        self.assertEqual(corpus["chord_events"], 1879)
        self.assertEqual(corpus["ambiguous_router_events"], 1828)
        self.assertTrue(self.report["reproduction_guard"]["matches_stage7c_r1_stateless_specialists_exactly"])

    def test_router_result_is_positive_but_not_promoted(self) -> None:
        router = self.report["router"]
        self.assertEqual(router["fold_wins"], 4)
        self.assertEqual(router["fold_losses"], 1)
        self.assertEqual(router["family_wins"], 16)
        self.assertEqual(router["family_ties"], 7)
        self.assertEqual(router["family_losses"], 1)
        safety = self.report["safety"]
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["real_xml_committed_to_git"])

    def test_poorly_transferring_mid_high_specialists_are_not_selected_oof(self) -> None:
        selected = self.report["router"]["selected_style_counts"]
        self.assertEqual(selected["mid_position"], 0)
        self.assertEqual(selected["high_position"], 0)
        self.assertEqual(sum(selected.values()), self.report["corpus"]["ambiguous_router_events"])


if __name__ == "__main__":
    unittest.main()
