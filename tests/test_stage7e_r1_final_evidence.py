from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7ER1FinalEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7e_r1_untouched_final_result.json"
        self.report = json.loads(path.read_text(encoding="utf-8"))

    def test_final_corpus_is_independent_and_sufficient(self) -> None:
        intake = self.report["independence_and_intake"]
        self.assertEqual(intake["development_source_hash_overlap"], 0)
        self.assertEqual(intake["observed_missing_from_deterministic_candidates"], 0)
        self.assertEqual(intake["no_candidate_events"], 0)
        self.assertGreaterEqual(intake["final_ambiguous_events"], 100)
        self.assertGreaterEqual(intake["final_families_with_ambiguous_events"], 8)
        self.assertTrue(intake["sufficiency_gate_passed"])

    def test_reproduction_guard_matches_accepted_development_evidence(self) -> None:
        guard = self.report["reproduction_guard"]
        self.assertEqual(guard["development_unique_xml"], 33)
        self.assertEqual(guard["development_families"], 25)
        self.assertEqual(guard["development_chord_events"], 1879)
        self.assertAlmostEqual(guard["development_open_low_top1"], 0.7915754923413567)
        self.assertAlmostEqual(guard["stage7d_a_cv_macro_router_top1"], 0.8386507946895563)
        self.assertAlmostEqual(guard["stage7d_a_cv_macro_open_low_top1"], 0.7967706271049415)
        self.assertTrue(guard["passed"])

    def test_preregistered_promotion_gate_passed_without_post_result_tuning(self) -> None:
        final = self.report["final"]
        gate = self.report["promotion_gate"]
        self.assertGreater(final["event_weighted_router_top1"], final["event_weighted_always_open_low_top1"])
        self.assertGreaterEqual(final["macro_family_router_top1"], final["macro_family_always_open_low_top1"])
        self.assertTrue(gate["event_weighted_router_must_exceed_open_low"])
        self.assertTrue(gate["macro_family_router_must_not_trail_open_low"])
        self.assertTrue(gate["passed"])
        self.assertTrue(self.report["promotion_gate_passed"] if "promotion_gate_passed" in self.report else gate["passed"])
        self.assertFalse(self.report["safety"]["post_result_tuning"])

    def test_final_targets_never_enter_fit_and_no_deployment_is_authorized(self) -> None:
        safety = self.report["safety"]
        self.assertEqual(safety["final_training_rows"], 0)
        self.assertFalse(safety["final_targets_used_for_fit"])
        self.assertFalse(safety["common_tone_included"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertEqual(
            self.report["promotion_gate"]["meaning"],
            "evidence_supports_next_promotion_review_not_automatic_checkpoint_or_production_integration",
        )


if __name__ == "__main__":
    unittest.main()
