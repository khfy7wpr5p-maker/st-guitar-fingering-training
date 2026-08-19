from __future__ import annotations

import json
from pathlib import Path
import unittest


class S2ABatch01DiagnosticDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = (
            Path(__file__).resolve().parents[1]
            / "evidence"
            / "stage7g_e3_s2a_batch01_diagnostic_decision.json"
        )
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_batch01_is_permanently_diagnostic_only(self):
        self.assertEqual(self.data["status"], "DIAGNOSTIC_ONLY_NEVER_TRAINING")
        policy = self.data["source_policy_review"]
        self.assertTrue(policy["same_40_source_families_were_used_in_prior_teacher_preference_development"])
        self.assertFalse(policy["fit_eligibility"])
        self.assertEqual(policy["effective_s2a_fit_rows_from_batch01"], 0)

    def test_no_equal_or_unsure_coercion_or_distance_confidence_rewrite(self):
        diagnostics = self.data["response_diagnostics"]
        self.assertEqual(diagnostics["tasks"], 720)
        self.assertEqual(diagnostics["A"], 164)
        self.assertEqual(diagnostics["B"], 167)
        self.assertEqual(diagnostics["EQUAL_OR_UNSURE"], 389)
        self.assertEqual(diagnostics["decisive"], 331)
        guards = diagnostics["interpretation_guards"]
        self.assertTrue(guards["do_not_coerce_equal_or_unsure"])
        self.assertTrue(guards["distance_l1_is_not_monotonic_with_decisiveness_in_this_pilot"])
        self.assertTrue(guards["do_not_redefine_FAR_as_human_confidence"])

    def test_fresh_source_reservations_are_predeclared(self):
        plan = self.data["fresh_collection_plan"]
        self.assertEqual(plan["primary_development_family_target"], 80)
        self.assertEqual(plan["primary_development_task_target"], 1440)
        self.assertEqual(plan["tasks_per_primary_family"], 18)
        self.assertEqual(plan["pair_type_x_distance_target_each"], 240)
        self.assertEqual(plan["pre_reserved_contingency_family_count"], 20)
        self.assertEqual(plan["pre_reserved_untouched_final_family_count"], 20)
        self.assertTrue(plan["repeat_deferred_until_fresh_development_corpus_gate_passes"])

    def test_batch01_repeat_fit_and_promotion_remain_closed(self):
        decision = self.data["decision"]
        self.assertFalse(decision["run_repeat_on_batch01"])
        self.assertFalse(decision["fit_model_on_batch01"])
        self.assertFalse(decision["change_frozen_v1_model_from_batch01_labels"])
        boundary = self.data["scientific_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))
        self.assertEqual(
            self.data["next_gate"],
            "FREEZE_FRESH_SOURCE_RESERVATION_AND_BATCH02_TASK_IDENTITIES_BEFORE_COLLECTION",
        )


if __name__ == "__main__":
    unittest.main()
