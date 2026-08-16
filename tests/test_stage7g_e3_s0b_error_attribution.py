from __future__ import annotations

import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from st_guitar_fingering_training.stage7g_e3_r2_learning import Stage7GE3R2TrainingRow
from st_guitar_fingering_training.stage7g_e3_s0b_error_attribution import (
    STAGE7G_E3_S0B_AXIS_PROPERTIES,
    STAGE7G_E3_S0B_CONFIG,
    STAGE7G_E3_S0B_SCHEMA,
    _axis_attribution,
    stage7g_e3_s0b_event_audit,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads(
    (ROOT / "evidence/stage7g_e3_s0b_error_attribution_protocol.json").read_text(
        encoding="utf-8"
    )
)


class Stage7GE3S0BErrorAttributionTests(unittest.TestCase):
    def test_protocol_keeps_specialist_candidate_only_and_forbids_selection(self) -> None:
        self.assertEqual(
            PROTOCOL["schema"],
            "st-guitar-stage7g-e3-s0b-error-attribution-protocol-v1",
        )
        self.assertEqual(PROTOCOL["status"], "PREREGISTERED_NO_RESULTS")
        self.assertEqual(
            PROTOCOL["architecture_decision"]["specialist_architecture_status"],
            "TARGET_ARCHITECTURE_CANDIDATE_ONLY",
        )
        for key, value in STAGE7G_E3_S0B_CONFIG["forbidden"].items():
            self.assertTrue(value, key)

    def test_public_api_has_no_tuning_or_external_validation_inputs(self) -> None:
        signature = inspect.signature(stage7g_e3_s0b_event_audit)
        self.assertEqual(tuple(signature.parameters), ("rows",))
        self.assertIn("does not tune", stage7g_e3_s0b_event_audit.__doc__)
        self.assertNotIn("e3e", signature.parameters)
        self.assertNotIn("threshold", signature.parameters)

    def test_axis_mapping_uses_only_existing_frozen_strong_contrast_properties(self) -> None:
        self.assertEqual(
            STAGE7G_E3_S0B_AXIS_PROPERTIES,
            {
                "OPEN_STRING_ECONOMY": ("open_note_count", "fretted_note_count"),
                "POSITION": ("mean_positive_fret",),
                "STRETCH": ("positive_fret_span",),
                "STRING_TOPOLOGY": ("string_span", "internal_string_gaps"),
            },
        )
        deltas = {
            "open_note_count": 0.0,
            "fretted_note_count": 0.0,
            "min_positive_fret": 0.0,
            "mean_positive_fret": 3.0,
            "max_fret": 0.0,
            "positive_fret_span": -2.0,
            "unique_positive_frets": 0.0,
            "max_same_positive_fret_count": 0.0,
            "string_span": 0.0,
            "adjacent_string_ratio": 0.0,
            "internal_string_gaps": 0.0,
        }
        result = _axis_attribution(deltas)
        self.assertEqual(result["primary_bucket"], "MULTI_AXIS")
        self.assertEqual(result["active_axes"], ["POSITION", "STRETCH"])
        self.assertEqual(
            result["property_directions"]["mean_positive_fret"],
            "COMPACT_HIGHER_BY_THRESHOLD",
        )
        self.assertEqual(
            result["property_directions"]["positive_fret_span"],
            "OPEN_LOW_HIGHER_BY_THRESHOLD",
        )
        self.assertIn("NOT_CAUSAL", result["semantics"])

    @staticmethod
    def _synthetic_rows() -> tuple[Stage7GE3R2TrainingRow, ...]:
        rows = []
        levels = ("L1", "L2", "L3", "L4")
        global_index = 0
        for family_index in range(40):
            family_size = 9 if family_index == 39 else 10
            for local_index in range(family_size):
                target = int(local_index in (0, 5))
                features = [0.0] * 40
                features[0] = float(2 + (local_index % 3))
                if local_index % 2 == 0:
                    features[32] = 3.0
                if local_index % 3 == 0:
                    features[34] = -2.0
                rows.append(
                    Stage7GE3R2TrainingRow(
                        event_id=f"synthetic-{global_index:03d}",
                        family_id=f"family-{family_index:02d}",
                        curriculum_level=levels[global_index % 4],
                        teacher_prefers_compact=target,
                        features=tuple(features),
                    )
                )
                global_index += 1
        assert len(rows) == 399
        return tuple(rows)

    def test_event_audit_covers_399_rows_and_reproduces_confusion_counts(self) -> None:
        def fake_fit(X_train, y_train, X_val, y_val):
            probabilities = np.where(y_val == 1, 0.8, 0.2).astype(np.float64)
            history = [
                {
                    "epoch": epoch,
                    "train_loss": 0.2,
                    "val_loss": 0.2,
                    "train_macro_f1": 1.0,
                    "val_macro_f1": 1.0,
                    "val_balanced_accuracy": 1.0,
                    "val_compact_precision": 1.0,
                    "val_compact_recall": 1.0,
                }
                for epoch in range(1, 61)
            ]
            return history, probabilities

        with patch(
            "st_guitar_fingering_training.stage7g_e3_s0b_error_attribution._fit_fixed_epochs",
            side_effect=fake_fit,
        ):
            report = stage7g_e3_s0b_event_audit(self._synthetic_rows())

        self.assertEqual(report["schema"], STAGE7G_E3_S0B_SCHEMA)
        self.assertEqual(report["status"], "S0B_EVENT_AUDIT_COMPLETE_NO_ARCHITECTURE_DECISION")
        self.assertEqual(report["dataset"]["rows"], 399)
        self.assertEqual(report["dataset"]["families"], 40)
        self.assertEqual(len(report["event_rows"]), 399)
        self.assertEqual(
            report["summary"]["error_counts"],
            {"TP": 80, "FP": 0, "FN": 0, "TN": 319},
        )
        self.assertTrue(
            report["interpretation_boundary"]["attribution_is_descriptive_not_causal"]
        )
        self.assertFalse(
            report["interpretation_boundary"]["specialist_architecture_activation_authorized"]
        )
        self.assertFalse(report["interpretation_boundary"]["e3e_teacher_gold_used"])
        self.assertFalse(report["interpretation_boundary"]["stage7e_used"])
        self.assertFalse(
            report["interpretation_boundary"]["production_or_shadow_integration"]
        )


if __name__ == "__main__":
    unittest.main()
