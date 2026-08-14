from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7FPromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7f_promotion_review.json"
        self.report = json.loads(path.read_text(encoding="utf-8"))

    def test_only_research_direction_is_promoted(self) -> None:
        decisions = self.report["promotion_decisions"]
        self.assertEqual(
            decisions["target_blind_stateless_router_architecture"],
            "PROMOTE_TO_NEXT_RESEARCH_STAGE",
        )
        self.assertEqual(decisions["current_router_checkpoint"], "DO_NOT_RETAIN")
        self.assertEqual(decisions["production_integration"], "BLOCKED")
        self.assertEqual(decisions["common_tone_self_rollout"], "REJECTED")

    def test_final_evidence_is_preserved_without_post_hoc_checkpoint_gate(self) -> None:
        final = self.report["final_evidence"]
        rationale = self.report["decision_rationale"]
        self.assertAlmostEqual(final["event_weighted_router_top1"], 0.45668098004546603)
        self.assertAlmostEqual(final["event_weighted_open_low_top1"], 0.4311694872442536)
        self.assertAlmostEqual(final["macro_family_router_top1"], 0.43413248464387444)
        self.assertAlmostEqual(final["macro_family_open_low_top1"], 0.3950520337661793)
        self.assertGreater(final["stateless_oracle_coverage"], final["event_weighted_router_top1"])
        self.assertTrue(rationale["no_absolute_checkpoint_threshold_was_preregistered"])
        self.assertTrue(rationale["checkpoint_promotion_requires_new_preregistered_criteria"])

    def test_stage7e_final_is_permanently_quarantined_from_development(self) -> None:
        quarantine = self.report["final_corpus_quarantine"]
        self.assertFalse(quarantine["may_train"])
        self.assertFalse(quarantine["may_tune"])
        self.assertFalse(quarantine["may_calibrate"])
        self.assertFalse(quarantine["may_select_features"])
        self.assertFalse(quarantine["may_select_hyperparameters"])
        self.assertEqual(quarantine["role"], "permanent_evaluation_only_reference")

    def test_stage7g_teacher_gold_contract_is_new_and_disjoint(self) -> None:
        next_stage = self.report["next_stage"]
        self.assertEqual(
            next_stage["label_semantics"],
            "teacher_preferred_guitaristic_choice_not_observed_behavior",
        )
        self.assertGreaterEqual(next_stage["minimum_independent_families"], 30)
        self.assertGreaterEqual(next_stage["minimum_teacher_labeled_ambiguous_events"], 600)
        self.assertGreaterEqual(next_stage["minimum_specialist_disagreement_events"], 100)
        self.assertTrue(next_stage["family_isolated_validation_required"])
        self.assertTrue(next_stage["final_test_sources_forbidden"])
        self.assertTrue(next_stage["development_source_hash_overlap_with_stage7e_forbidden"])
        self.assertFalse(next_stage["checkpoint_retention_preapproved"])
        self.assertFalse(next_stage["production_integration_preapproved"])

    def test_safety_boundary_remains_closed(self) -> None:
        safety = self.report["safety"]
        self.assertFalse(safety["model_algorithm_changed"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["stage7e_final_reused_for_training"])


if __name__ == "__main__":
    unittest.main()
