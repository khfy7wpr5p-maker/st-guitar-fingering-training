from __future__ import annotations

import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from st_guitar_fingering_training.stage7g_e3_r2_learning import (
    STAGE7G_E3_R2_CONFIG,
    Stage7GE3R2TrainingRow,
)
from st_guitar_fingering_training.stage7g_e3_s0_diagnostic import (
    STAGE7G_E3_S0_CONFIG,
    STAGE7G_E3_S0_SCHEMA,
    _metrics,
    stage7g_e3_s0_diagnostic_report,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads(
    (ROOT / "evidence/stage7g_e3_s0_failure_diagnostic_protocol.json").read_text(
        encoding="utf-8"
    )
)


class Stage7GE3S0DiagnosticTests(unittest.TestCase):
    def test_protocol_is_preregistered_and_specialist_is_candidate_only(self) -> None:
        self.assertEqual(
            PROTOCOL["schema"],
            "st-guitar-stage7g-e3-s0-failure-diagnostic-protocol-v1",
        )
        self.assertEqual(PROTOCOL["status"], "PREREGISTERED_NO_RESULTS")
        self.assertEqual(
            PROTOCOL["architecture_decision"]["specialist_architecture_status"],
            "TARGET_ARCHITECTURE_CANDIDATE_ONLY",
        )
        self.assertTrue(
            PROTOCOL["architecture_decision"]["specialist_activation_forbidden_in_s0"]
        )
        self.assertFalse(
            PROTOCOL["architecture_decision"]["current_monolithic_architecture_changed"]
        )

    def test_s0_keeps_r2_model_and_split_frozen_and_forbids_tuning(self) -> None:
        for key in ("method", "n_splits", "shuffle", "random_state", "group_key"):
            self.assertEqual(
                STAGE7G_E3_S0_CONFIG["outer_cv"][key],
                STAGE7G_E3_R2_CONFIG["split"][key],
            )
        self.assertEqual(STAGE7G_E3_S0_CONFIG["model"], STAGE7G_E3_R2_CONFIG["model"])
        forbidden = STAGE7G_E3_S0_CONFIG["forbidden"]
        for name in (
            "scheduler",
            "threshold_search",
            "hyperparameter_search",
            "new_features",
            "specialist_training",
            "early_stopping",
            "best_epoch_checkpoint_selection",
            "e3e_teacher_gold",
            "stage7e",
            "checkpoint_retention",
            "production_or_shadow_integration",
        ):
            self.assertTrue(forbidden[name])

    def test_public_diagnostic_api_accepts_only_development_rows(self) -> None:
        signature = inspect.signature(stage7g_e3_s0_diagnostic_report)
        self.assertEqual(tuple(signature.parameters), ("rows",))
        self.assertNotIn("e3e", signature.parameters)
        self.assertNotIn("threshold_search", signature.parameters)
        self.assertIn("no model selection", stage7g_e3_s0_diagnostic_report.__doc__)

    def test_metric_panel_includes_threshold_free_and_calibration_metrics(self) -> None:
        y = np.asarray([0, 0, 1, 1], dtype=np.int64)
        p = np.asarray([0.1, 0.4, 0.6, 0.9], dtype=np.float64)
        result = _metrics(y, p)
        self.assertEqual((result["tn"], result["fp"], result["fn"], result["tp"]), (2, 0, 0, 2))
        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["macro_f1"], 1.0)
        self.assertEqual(result["balanced_accuracy"], 1.0)
        self.assertEqual(result["compact_precision"], 1.0)
        self.assertEqual(result["compact_recall"], 1.0)
        self.assertIn("average_precision", result)
        self.assertIn("roc_auc", result)
        self.assertIn("brier_score", result)
        self.assertIn("mcc", result)

    @staticmethod
    def _synthetic_rows() -> tuple[Stage7GE3R2TrainingRow, ...]:
        rows = []
        global_index = 0
        levels = ("L1", "L2", "L3", "L4")
        for family_index in range(40):
            family_size = 9 if family_index == 39 else 10
            for local_index in range(family_size):
                target = int(local_index in (0, 5))
                features = [0.0] * 40
                features[0] = float(target)
                features[1] = float(family_index % 7)
                features[2] = float(local_index)
                rows.append(
                    Stage7GE3R2TrainingRow(
                        event_id=f"synthetic-{global_index:03d}",
                        family_id=f"family-{family_index:02d}",
                        curriculum_level=levels[global_index % len(levels)],
                        teacher_prefers_compact=target,
                        features=tuple(features),
                    )
                )
                global_index += 1
        assert len(rows) == 399
        return tuple(rows)

    def test_orchestration_covers_all_five_outer_folds_without_architecture_decision(self) -> None:
        def fake_fit(X_train, y_train, X_val, y_val):
            probabilities = np.where(y_val == 1, 0.7, 0.3).astype(np.float64)
            history = []
            for epoch in range(1, 61):
                val_loss = 0.50 - 0.002 * min(epoch, 20) + 0.001 * max(epoch - 20, 0)
                history.append(
                    {
                        "epoch": epoch,
                        "train_loss": 0.60 - 0.005 * epoch,
                        "val_loss": val_loss,
                        "train_macro_f1": 0.8,
                        "val_macro_f1": 0.8,
                        "val_balanced_accuracy": 0.8,
                        "val_compact_precision": 0.8,
                        "val_compact_recall": 0.8,
                    }
                )
            return history, probabilities

        fake_bootstrap = {
            "unit": "family_id",
            "requested_draws": 2000,
            "accepted_resamples": 2000,
            "confidence": 0.95,
            "random_state": 20260816,
            "intervals": {},
        }
        with patch(
            "st_guitar_fingering_training.stage7g_e3_s0_diagnostic._fit_fixed_epochs",
            side_effect=fake_fit,
        ), patch(
            "st_guitar_fingering_training.stage7g_e3_s0_diagnostic._family_bootstrap_ci",
            return_value=fake_bootstrap,
        ):
            report = stage7g_e3_s0_diagnostic_report(self._synthetic_rows())

        self.assertEqual(report["schema"], STAGE7G_E3_S0_SCHEMA)
        self.assertEqual(report["status"], "S0_DIAGNOSTIC_COMPLETE_NO_ARCHITECTURE_DECISION")
        self.assertEqual(report["dataset"]["rows"], 399)
        self.assertEqual(report["dataset"]["families"], 40)
        self.assertEqual(len(report["outer_folds"]), 5)
        self.assertTrue(all(row["family_overlap"] == 0 for row in report["outer_folds"]))
        self.assertEqual(report["oof_final_epoch"]["support"], 399)
        self.assertEqual(len(report["family_breakdown"]), 40)
        self.assertEqual(len(report["curriculum_level_breakdown"]), 4)
        self.assertEqual(len(report["feature_regime_breakdown"]), 6)
        self.assertEqual(
            [row["target_fraction"] for row in report["learning_curve"]],
            [0.25, 0.5, 0.75, 1.0],
        )
        boundary = report["interpretation_boundary"]
        self.assertEqual(
            boundary["specialist_architecture_status"],
            "TARGET_ARCHITECTURE_CANDIDATE_ONLY",
        )
        self.assertTrue(boundary["no_model_or_checkpoint_retained"])
        self.assertFalse(boundary["e3e_teacher_gold_used"])
        self.assertFalse(boundary["stage7e_used"])
        self.assertFalse(boundary["production_or_shadow_integration"])
        self.assertFalse(
            report["diagnostic_flags"]["specialist_architecture_activation_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
