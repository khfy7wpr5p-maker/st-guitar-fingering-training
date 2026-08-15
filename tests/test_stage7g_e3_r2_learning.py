from __future__ import annotations

from hashlib import sha256
import inspect
import unittest
from unittest.mock import patch

from st_guitar_fingering_training.stage7g_e3_r2_learning import (
    STAGE7G_E3_R2_CONFIG,
    Stage7GE3R2PoolRow,
    Stage7GE3R2TrainingRow,
    rows_from_choices,
    stage7g_e3_r2_learning_report,
)


class Stage7GE3R2LearningTests(unittest.TestCase):
    def test_config_is_fixed_manual_learning_demo_not_promotion(self):
        self.assertEqual(STAGE7G_E3_R2_CONFIG["model"]["epochs"], 60)
        self.assertEqual(STAGE7G_E3_R2_CONFIG["model"]["hidden_layer_sizes"], [32, 16])
        self.assertEqual(STAGE7G_E3_R2_CONFIG["model"]["decision_threshold"], 0.5)
        self.assertEqual(STAGE7G_E3_R2_CONFIG["split"]["method"], "StratifiedGroupKFold")
        self.assertFalse(STAGE7G_E3_R2_CONFIG["checkpoint_retained"])
        self.assertFalse(STAGE7G_E3_R2_CONFIG["e3e_teacher_gold_used"])
        self.assertFalse(STAGE7G_E3_R2_CONFIG["stage7e_used"])
        self.assertFalse(STAGE7G_E3_R2_CONFIG["production_integration"])

    def test_learning_api_has_no_e3e_or_untouched_label_parameter(self):
        params = set(inspect.signature(stage7g_e3_r2_learning_report).parameters)
        self.assertEqual(params, {"rows"})
        source = inspect.getsource(stage7g_e3_r2_learning_report)
        self.assertNotIn("E3E_B_RESPONSE", source)
        self.assertNotIn("stage7e", " ".join(params).lower())

    def test_choice_join_decodes_blind_ab_and_excludes_equal(self):
        ids = [f"task_{i:03d}" for i in range(400)]
        pool = tuple(
            Stage7GE3R2PoolRow(
                event_id=task_id,
                family_id=f"family_{i % 40:02d}",
                curriculum_level=("L1", "L2", "L3", "L4")[i % 4],
                features=tuple(float((i + j) % 7) for j in range(40)),
            )
            for i, task_id in enumerate(ids)
        )
        choices_rows = []
        decoded = {"OPEN_LOW": 0, "COMPACT": 0, "EQUAL_OR_UNSURE": 0}
        from st_guitar_fingering_training.stage7g_e3_r2_learning import _development_blind_style_order
        for i, task_id in enumerate(ids):
            if i == 0:
                response = "EQUAL_OR_UNSURE"
                decoded[response] += 1
            else:
                response = "A" if i % 2 else "B"
                style_a, style_b = _development_blind_style_order(task_id)
                preferred = style_a if response == "A" else style_b
                decoded["COMPACT" if preferred == "compact" else "OPEN_LOW"] += 1
            choices_rows.append({"task_id": task_id, "response": response})
        choices = {
            "schema": "st-guitar-stage7g-e3-pairwise-choice-export-v1",
            "annotation_blinded": True,
            "manifest_sha256": "manifest",
            "selected_count": 400,
            "task_count": 400,
            "choices": choices_rows,
        }
        digest = sha256("\n".join(sorted(ids)).encode()).hexdigest()
        level_counts = {level: 100 for level in ("L1", "L2", "L3", "L4")}
        with (
            patch("st_guitar_fingering_training.stage7g_e3_r2_learning.STAGE7G_E3_R2_EXPECTED_MANIFEST_SHA256", "manifest"),
            patch("st_guitar_fingering_training.stage7g_e3_r2_learning.STAGE7G_E3_R2_EXPECTED_TASK_SET_SHA256", digest),
            patch("st_guitar_fingering_training.stage7g_e3_r2_learning.STAGE7G_E3_R2_EXPECTED_DECODED", decoded),
            patch("st_guitar_fingering_training.stage7g_e3_r2_learning.STAGE7G_E3_R2_EXPECTED_LEVEL_COUNTS", level_counts),
        ):
            rows, preflight = rows_from_choices(pool, choices)
        self.assertEqual(len(rows), 399)
        self.assertEqual(preflight["status"], "R2_PREFLIGHT_PASS_STOP_BEFORE_MANUAL_TRAIN")
        self.assertEqual(preflight["equal_or_unsure_excluded"], 1)
        self.assertFalse(preflight["e3e_teacher_gold_used"])

    def test_learning_report_emits_epoch_val_loss_and_macro_f1_without_checkpoint(self):
        rows = []
        for i in range(399):
            family_index = i % 40
            block = i // 40
            target = int((block + family_index) % 5 == 0)
            signal = 1.0 if target else -1.0
            features = (signal,) + tuple(float(((i + j) % 11) - 5) / 10.0 for j in range(39))
            rows.append(Stage7GE3R2TrainingRow(
                event_id=f"event_{i:03d}",
                family_id=f"family_{family_index:02d}",
                curriculum_level=("L1", "L2", "L3", "L4")[i % 4],
                teacher_prefers_compact=target,
                features=features,
            ))
        report = stage7g_e3_r2_learning_report(rows)
        self.assertEqual(len(report["history"]), 60)
        self.assertIn("val_loss", report["history"][0])
        self.assertIn("val_macro_f1", report["history"][0])
        self.assertIn("macro_f1_gain_vs_always_open_low", report["final_validation"])
        self.assertEqual(report["split"]["family_overlap"], 0)
        self.assertIsNone(report["pixel_localization_metric"]["LocF1@2px"])
        self.assertFalse(report["scientific_boundary"]["checkpoint_retained"])
        self.assertFalse(report["scientific_boundary"]["e3e_teacher_gold_used"])
        self.assertFalse(report["scientific_boundary"]["best_epoch_checkpoint_selected"])


if __name__ == "__main__":
    unittest.main()
