import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = json.loads(
    (ROOT / "evidence" / "stage7g_d_r2_pairwise_transition.json").read_text(encoding="utf-8")
)


class Stage7GDR2PairwiseTransitionTests(unittest.TestCase):
    def test_first_38_full_candidate_choices_are_retained_without_raw_rows_in_git(self):
        full = EVIDENCE["validated_full_candidate_choices"]
        self.assertEqual(full["reported_selected_count"], 38)
        self.assertEqual(full["validated_task_ids"], 38)
        self.assertEqual(full["validated_candidate_ids"], 38)
        self.assertEqual(full["duplicate_task_ids"], 0)
        self.assertTrue(full["all_tasks_match_sealed_manifest"])
        self.assertTrue(full["all_choices_are_members_of_their_deterministic_physical_candidate_sets"])
        self.assertFalse(full["raw_choice_rows_committed_to_git"])
        self.assertEqual(full["finalized_teacher_gold_records"], 0)

    def test_pairwise_transition_uses_the_remaining_sealed_tasks_without_reselection(self):
        pairwise = EVIDENCE["pairwise_transition"]
        self.assertEqual(pairwise["completed_full_candidate_tasks_excluded"], 38)
        self.assertEqual(pairwise["remaining_sealed_tasks"], 562)
        self.assertEqual(pairwise["teacher_visible_options_per_task"], 2)
        self.assertEqual(pairwise["teacher_visible_option_labels"], ["A", "B"])
        self.assertEqual(pairwise["allowed_responses"], ["A", "B", "EQUAL_OR_UNSURE"])
        self.assertFalse(pairwise["specialist_identity_visible_to_teacher"])
        self.assertFalse(pairwise["model_scores_visible_to_teacher"])
        self.assertFalse(pairwise["source_identity_visible_to_teacher"])
        self.assertFalse(pairwise["observed_source_voicing_visible_to_teacher"])
        self.assertFalse(pairwise["reselection_after_first_38_choices"])
        self.assertIn("not equivalent", pairwise["pairwise_label_semantics"])

    def test_pairwise_training_gate_is_preregistered_before_pairwise_labels(self):
        gate = EVIDENCE["preregistered_pairwise_training_gate"]
        boundary = EVIDENCE["scientific_boundary"]
        self.assertEqual(boundary["pairwise_labels_collected"], 0)
        self.assertEqual(gate["minimum_decisive_ab_labels"], 400)
        self.assertEqual(gate["minimum_independent_families_with_decisive_labels"], 30)
        self.assertTrue(gate["equal_or_unsure_is_preserved_and_never_coerced_to_a_or_b"])
        self.assertTrue(gate["family_isolated_validation_required"])
        self.assertFalse(gate["training_authorized_before_gate"])
        self.assertFalse(boundary["teacher_gold_corpus_gate_passed"])
        self.assertFalse(boundary["pairwise_training_gate_passed"])
        self.assertFalse(boundary["model_fit_started"])
        self.assertFalse(boundary["colab_training_started"])
        self.assertFalse(boundary["checkpoint_retained"])
        self.assertFalse(boundary["production_integration"])
        self.assertFalse(boundary["stage7e_final_reused"])


if __name__ == "__main__":
    unittest.main()
