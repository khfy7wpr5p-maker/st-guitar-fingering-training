from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.stage7g_e3_s1f_component_training_prep import (
    S1F_COMPONENTS,
    S1F_FEATURE_NAMES,
    S1F_TRAINING_GATE_SCHEMA,
    Stage7GE3S1FTrainingRow,
    build_training_row,
    component_feature_record,
    evaluate_component_specialist,
    evaluate_constant_baseline,
    family_fold_map,
    fit_component_specialist,
    majority_baseline_label,
    split_family_safe,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads(
    (ROOT / "evidence/stage7g_e3_s1f_component_training_prep_protocol.json").read_text(
        encoding="utf-8"
    )
)
TUNING = (64, 59, 55, 50, 45, 40)
PITCHES = (52, 55, 59)
OPEN_VOICING = ((52, 6, 12), (55, 3, 0), (59, 2, 0))
FRETTED_VOICING = ((52, 5, 7), (55, 4, 5), (59, 3, 4))


class Stage7GE3S1FComponentTrainingPrepTests(unittest.TestCase):
    def test_protocol_is_preparation_only_and_forbids_current_labels(self) -> None:
        self.assertEqual(
            PROTOCOL["status"], "PREREGISTERED_PREPARATION_ONLY_NO_S1_LABELS"
        )
        self.assertFalse(PROTOCOL["label_contract"]["pilot_labels_for_training"])
        self.assertFalse(PROTOCOL["label_contract"]["repeat_labels_for_training"])
        self.assertFalse(PROTOCOL["current_scientific_boundary"]["model_fit_on_project_labels"])
        self.assertFalse(PROTOCOL["current_scientific_boundary"]["training_execution_authorized"])
        self.assertTrue(PROTOCOL["current_scientific_boundary"]["full_reliability_test_still_required"])

    def test_feature_contract_reuses_target_blind_geometry_and_physical_boundary(self) -> None:
        record = component_feature_record(
            specialist="OPEN_STRING_HAND_RELIEF",
            pitches_midi=PITCHES,
            tuning=TUNING,
            voicing=OPEN_VOICING,
        )
        self.assertEqual(tuple(record), S1F_FEATURE_NAMES)
        self.assertEqual(record["chord_size"], 3.0)
        self.assertEqual(record["open_note_count"], 2.0)
        self.assertGreaterEqual(record["candidate_count"], 1.0)

        with self.assertRaises(ValueError):
            component_feature_record(
                specialist="STRING_SKIP_PENALTY",
                pitches_midi=PITCHES,
                tuning=TUNING,
                voicing=((52, 1, 99), (55, 2, 0), (59, 3, 4)),
            )

    def test_open_string_specialists_fail_closed_when_no_open_string_exists(self) -> None:
        for specialist in ("OPEN_STRING_HAND_RELIEF", "OPEN_STRING_CONTROL_PENALTY"):
            with self.assertRaisesRegex(ValueError, "at least one open string"):
                component_feature_record(
                    specialist=specialist,
                    pitches_midi=PITCHES,
                    tuning=TUNING,
                    voicing=FRETTED_VOICING,
                )

    def test_training_row_rejects_repeat_and_pilot_and_excludes_unsure(self) -> None:
        common = dict(
            example_id="example-1",
            family_id="family-1",
            task_id="task-1",
            option_id="A",
            specialist="STRING_SKIP_PENALTY",
            pitches_midi=PITCHES,
            tuning=TUNING,
            voicing=FRETTED_VOICING,
        )
        self.assertIsNone(
            build_training_row(
                **common,
                label="UNSURE",
                provenance="FULL_RELIABILITY_FIRST_PASS",
            )
        )
        with self.assertRaisesRegex(ValueError, "repeat labels"):
            build_training_row(
                **common,
                label="YES",
                provenance="FULL_RELIABILITY_REPEAT",
            )
        with self.assertRaisesRegex(ValueError, "pilot labels"):
            build_training_row(
                **common,
                label="NO",
                provenance="S1E_PILOT_FIRST_PASS",
            )
        row = build_training_row(
            **common,
            label="YES",
            provenance="FULL_RELIABILITY_FIRST_PASS",
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.label, 1)

    @staticmethod
    def _synthetic_rows() -> tuple[Stage7GE3S1FTrainingRow, ...]:
        rows = []
        for family_index in range(10):
            for local_index in range(4):
                label = (family_index + local_index) % 2
                features = [0.0] * len(S1F_FEATURE_NAMES)
                features[0] = 3.0
                features[4] = float(local_index % 2)
                features[12] = float(label)
                features[14] = float(label)
                rows.append(
                    Stage7GE3S1FTrainingRow(
                        example_id=f"e-{family_index}-{local_index}",
                        family_id=f"family-{family_index}",
                        task_id=f"task-{family_index}-{local_index}",
                        option_id="A",
                        specialist="STRING_SKIP_PENALTY",
                        label=label,
                        features=tuple(features),
                        provenance="FULL_RELIABILITY_FIRST_PASS",
                    )
                )
        return tuple(rows)

    def test_family_split_has_no_leakage(self) -> None:
        rows = self._synthetic_rows()
        mapping = family_fold_map(rows)
        self.assertEqual(set(mapping.values()), {0, 1, 2, 3, 4})
        train, validation = split_family_safe(rows, validation_fold=0)
        self.assertFalse(
            {row.family_id for row in train} & {row.family_id for row in validation}
        )
        self.assertEqual(len(train) + len(validation), len(rows))

    def test_fit_gate_is_closed_without_future_reliability_and_merged_protocol(self) -> None:
        rows = self._synthetic_rows()
        with self.assertRaisesRegex(PermissionError, "gate is closed"):
            fit_component_specialist(rows, authorization={})
        with self.assertRaisesRegex(PermissionError, "gate is closed"):
            fit_component_specialist(
                rows,
                authorization={
                    "schema": S1F_TRAINING_GATE_SCHEMA,
                    "full_reliability_status": "FAIL",
                    "training_protocol_status": "MERGED",
                    "repeat_labels_used": False,
                    "pilot_labels_used": False,
                    "threshold_tuned_on_validation": False,
                    "checkpoint_retention_authorized": False,
                    "production_or_shadow_integration": False,
                },
            )

    def test_fixed_in_memory_baseline_harness_works_only_with_synthetic_fixture(self) -> None:
        rows = self._synthetic_rows()
        train, validation = split_family_safe(rows, validation_fold=0)
        authorization = {
            "schema": S1F_TRAINING_GATE_SCHEMA,
            "full_reliability_status": "PASS",
            "training_protocol_status": "MERGED",
            "repeat_labels_used": False,
            "pilot_labels_used": False,
            "threshold_tuned_on_validation": False,
            "checkpoint_retention_authorized": False,
            "production_or_shadow_integration": False,
        }
        model = fit_component_specialist(train, authorization=authorization)
        report = evaluate_component_specialist(model, validation)
        self.assertEqual(report.specialist, "STRING_SKIP_PENALTY")
        self.assertEqual(report.rows, len(validation))
        self.assertGreaterEqual(report.balanced_accuracy, 0.5)

        majority = majority_baseline_label(train)
        baseline = evaluate_constant_baseline(validation, predicted_label=majority)
        self.assertEqual(baseline.rows, len(validation))
        self.assertGreaterEqual(baseline.accuracy, 0.0)
        self.assertLessEqual(baseline.accuracy, 1.0)

    def test_component_list_is_exactly_three_micro_specialists(self) -> None:
        self.assertEqual(
            S1F_COMPONENTS,
            (
                "STRING_SKIP_PENALTY",
                "OPEN_STRING_HAND_RELIEF",
                "OPEN_STRING_CONTROL_PENALTY",
            ),
        )


if __name__ == "__main__":
    unittest.main()
