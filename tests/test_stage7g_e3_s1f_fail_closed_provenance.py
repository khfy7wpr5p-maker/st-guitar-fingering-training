from __future__ import annotations

from dataclasses import replace
import unittest

from st_guitar_fingering_training.stage7g_e3_s1f_component_training_prep import (
    S1F_ALLOWED_PROVENANCE,
    S1F_FEATURE_NAMES,
    S1F_TRAINING_GATE_SCHEMA,
    Stage7GE3S1FTrainingRow,
    build_training_row,
    fit_component_specialist,
    split_family_safe,
)

TUNING = (64, 59, 55, 50, 45, 40)
PITCHES = (52, 55, 59)
FRETTED_VOICING = ((52, 5, 7), (55, 4, 5), (59, 3, 4))


class Stage7GE3S1FFailClosedProvenanceTests(unittest.TestCase):
    @staticmethod
    def _rows() -> tuple[Stage7GE3S1FTrainingRow, ...]:
        rows = []
        for family_index in range(5):
            for label in (0, 1):
                values = [0.0] * len(S1F_FEATURE_NAMES)
                values[0] = 3.0
                values[-1] = float(label)
                rows.append(
                    Stage7GE3S1FTrainingRow(
                        example_id=f"{family_index}-{label}",
                        family_id=f"family-{family_index}",
                        task_id=f"task-{family_index}-{label}",
                        option_id="A",
                        specialist="STRING_SKIP_PENALTY",
                        label=label,
                        features=tuple(values),
                        provenance=S1F_ALLOWED_PROVENANCE,
                    )
                )
        return tuple(rows)

    @staticmethod
    def _forged_authorization() -> dict:
        return {
            "schema": S1F_TRAINING_GATE_SCHEMA,
            "full_reliability_status": "PASS",
            "training_protocol_status": "MERGED",
            "repeat_labels_used": False,
            "pilot_labels_used": False,
            "threshold_tuned_on_validation": False,
            "checkpoint_retention_authorized": False,
            "production_or_shadow_integration": False,
        }

    def test_manual_pass_dict_cannot_open_training_gate(self) -> None:
        with self.assertRaisesRegex(PermissionError, "hard closed"):
            fit_component_specialist(
                self._rows(), authorization=self._forged_authorization()
            )

    def test_exact_provenance_rejects_prefix_suffix_and_repeat(self) -> None:
        common = dict(
            example_id="example-1",
            family_id="family-1",
            task_id="task-1",
            option_id="A",
            specialist="STRING_SKIP_PENALTY",
            label="YES",
            pitches_midi=PITCHES,
            tuning=TUNING,
            voicing=FRETTED_VOICING,
        )
        for bad in (
            "FAKE_FULL_RELIABILITY_FIRST_PASS",
            "FULL_RELIABILITY_FIRST_PASS_FAKE",
            "FULL_RELIABILITY_REPEAT",
            "S1E_PILOT_FIRST_PASS",
        ):
            with self.subTest(provenance=bad):
                with self.assertRaisesRegex(
                    ValueError, "exactly FULL_RELIABILITY_FIRST_PASS"
                ):
                    build_training_row(**common, provenance=bad)

    def test_unsure_does_not_bypass_provenance_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly FULL_RELIABILITY_FIRST_PASS"):
            build_training_row(
                example_id="example-unsure",
                family_id="family-1",
                task_id="task-unsure",
                option_id="A",
                specialist="STRING_SKIP_PENALTY",
                label="UNSURE",
                pitches_midi=PITCHES,
                tuning=TUNING,
                voicing=FRETTED_VOICING,
                provenance="S1E_PILOT_FIRST_PASS",
            )

    def test_direct_dataclass_construction_cannot_bypass_exact_provenance(self) -> None:
        rows = self._rows()
        bad = (
            replace(rows[0], provenance="FAKE_FULL_RELIABILITY_FIRST_PASS"),
            *rows[1:],
        )
        with self.assertRaisesRegex(
            ValueError, "exact FULL_RELIABILITY_FIRST_PASS provenance"
        ):
            split_family_safe(bad, validation_fold=0)


if __name__ == "__main__":
    unittest.main()
