from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.curriculum_contract import STAGE7G_E3_FEATURE_NAMES


class Stage7GE3DTrainingProtocolEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = (
            Path(__file__).resolve().parents[1]
            / "evidence"
            / "stage7g_e3_d_training_protocol_freeze.json"
        )
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_protocol_identity_and_no_fit_status(self):
        self.assertEqual(
            self.data["schema"], "st-guitar-stage7g-e3-d-training-protocol-v1"
        )
        self.assertEqual(self.data["stage"], "7G-E3-D")
        self.assertEqual(self.data["status"], "TRAINING_PROTOCOL_FROZEN_NO_FIT")
        self.assertEqual(
            self.data["base_main_sha"],
            "81f43e70b2eae734104d7d3b9d280001634d7327",
        )
        boundary = self.data["scientific_boundary"]
        for key in (
            "model_fit",
            "threshold_selected",
            "outer_cv_observed",
            "checkpoint_retained",
            "production_integration",
            "untouched_validation_claim",
            "stage7e_used",
        ):
            self.assertFalse(boundary[key], key)

    def test_inputs_are_pinned_and_fit_rows_are_new_e3_only(self):
        inputs = self.data["inputs"]
        self.assertEqual(inputs["expected_tasks"], 400)
        self.assertEqual(inputs["expected_families"], 40)
        self.assertEqual(
            inputs["expected_levels"], {"L1": 140, "L2": 120, "L3": 80, "L4": 60}
        )
        self.assertEqual(
            inputs["expected_decoded"],
            {
                "OPEN_LOW": 311,
                "COMPACT": 88,
                "EQUAL_OR_UNSURE": 1,
                "decisive_fit_rows": 399,
            },
        )
        self.assertEqual(
            inputs["curriculum_package"]["sha256"],
            "e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef",
        )
        self.assertEqual(
            inputs["teacher_choices"]["sha256"],
            "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e",
        )
        fit = self.data["fit_corpus"]
        self.assertTrue(fit["new_e3_curriculum_teacher_gold_only"])
        self.assertFalse(fit["old_e1_e2_556_decisive_rows_used"])
        self.assertFalse(fit["historical_first_38_full_candidate_rows_used"])
        self.assertFalse(fit["equal_or_unsure_used_in_binary_fit"])
        self.assertFalse(fit["stage7e_used"])

    def test_feature_contract_is_exact_and_target_blind(self):
        features = self.data["features"]
        self.assertEqual(features["count"], 40)
        self.assertEqual(len(STAGE7G_E3_FEATURE_NAMES), 40)
        digest = hashlib.sha256(
            "\n".join(STAGE7G_E3_FEATURE_NAMES).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            digest,
            "6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3",
        )
        self.assertEqual(digest, features["ordered_name_sha256"])
        self.assertFalse(features["model_uses_curriculum_level"])
        self.assertFalse(features["model_uses_family_id"])
        self.assertTrue(features["family_id_split_only"])
        self.assertTrue(features["curriculum_level_reporting_only"])
        self.assertFalse(features["sequence_context"])
        self.assertFalse(features["source_target_tab"])

    def test_model_is_fixed_unbalanced_logistic_gate(self):
        model = self.data["model"]
        self.assertEqual(model["positive_class"], "COMPACT")
        self.assertEqual(model["default_decision"], "OPEN_LOW")
        self.assertEqual(model["pipeline"], ["StandardScaler", "LogisticRegression"])
        params = model["logistic_regression"]
        self.assertEqual(
            params,
            {
                "max_iter": 2000,
                "class_weight": None,
                "C": 1.0,
                "solver": "lbfgs",
                "random_state": 0,
            },
        )
        for key in (
            "regularization_search",
            "class_weight_search",
            "feature_selection",
            "model_family_search",
            "calibration_search",
        ):
            self.assertFalse(model[key], key)

    def test_nested_family_isolation_and_threshold_gate_are_frozen(self):
        nested = self.data["nested_cv"]
        self.assertEqual(
            nested["classification"], "NESTED_DEVELOPMENT_CV_NOT_UNTOUCHED_VALIDATION"
        )
        self.assertEqual(
            nested["outer"],
            {
                "splitter": "StratifiedGroupKFold",
                "n_splits": 5,
                "shuffle": True,
                "random_state": 731,
                "group_key": "family_id",
            },
        )
        self.assertEqual(nested["inner"]["n_splits"], 4)
        self.assertEqual(nested["inner"]["random_state_rule"], "7310 + outer_fold_index")
        self.assertEqual(nested["inner"]["probabilities"], "pooled_inner_oof_only")
        self.assertTrue(nested["abort_on_family_leakage"])
        self.assertTrue(nested["abort_on_training_fold_single_class"])
        self.assertTrue(nested["abort_on_nonfinite_features"])

        gate = self.data["threshold_gate"]
        self.assertEqual(gate["candidate_thresholds"], [0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
        self.assertEqual(gate["selection_data"], "inner_oof_only")
        self.assertEqual(gate["eligibility"]["min_predicted_compact"], 10)
        self.assertAlmostEqual(gate["eligibility"]["min_compact_precision"], 2 / 3)
        self.assertEqual(
            gate["eligibility"]["min_event_accuracy_delta_vs_always_open_low"], 0.0
        )
        self.assertEqual(gate["fallback_if_none_eligible"], "NO_SWITCH_ALWAYS_OPEN_LOW")
        self.assertFalse(gate["outer_labels_may_select_threshold"])

    def test_development_gate_cannot_authorize_checkpoint_or_production(self):
        gate = self.data["development_gate"]
        self.assertEqual(
            gate["positive_status"],
            "POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN",
        )
        self.assertEqual(
            gate["negative_status"], "NEGATIVE_DEVELOPMENT_CV_NO_PROMOTION"
        )
        requirements = gate["requirements"]
        self.assertEqual(requirements["event_accuracy_delta_gt"], 0.0)
        self.assertEqual(requirements["macro_family_accuracy_delta_gt"], 0.0)
        self.assertEqual(requirements["compact_precision_gt"], 0.5)
        self.assertTrue(requirements["compact_true_positives_gt_false_positives"])
        self.assertTrue(requirements["family_wins_gt_losses"])
        self.assertFalse(gate["authorizes_checkpoint"])
        self.assertFalse(gate["authorizes_production"])

    def test_colab_stays_manual_and_checkpoint_defaults_closed(self):
        colab = self.data["colab"]
        for key in (
            "manual_training_only_after_protocol_merge",
            "exact_git_sha_required",
            "hash_preflight_required",
            "preflight_stop_before_train",
            "manual_train_cell_required",
            "frozen_evaluation_only",
            "aggregate_evidence_export",
        ):
            self.assertTrue(colab[key], key)
        self.assertFalse(colab["checkpoint_retained_default"])


if __name__ == "__main__":
    unittest.main()
