from __future__ import annotations

from dataclasses import replace
import unittest

from st_guitar_fingering_training.stage7g_e3_s1f_component_training_prep import (
    S1F_FEATURE_NAMES,
    S1F_TRAINING_GATE_SCHEMA,
    Stage7GE3S1FTrainingRow,
    fit_component_specialist,
)


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
                        provenance="FULL_RELIABILITY_FIRST_PASS",
                    )
                )
        return tuple(rows)

    @staticmethod
    def _authorization() -> dict:
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

    def test_direct_dataclass_construction_cannot_bypass_provenance_gate(self) -> None:
        rows = self._rows()
        bad = (replace(rows[0], provenance="MANUAL_LABEL_IMPORT"), *rows[1:])
        with self.assertRaisesRegex(ValueError, "FULL_RELIABILITY_FIRST_PASS"):
            fit_component_specialist(bad, authorization=self._authorization())

    def test_repeat_provenance_is_rejected_even_with_authorization_object(self) -> None:
        rows = self._rows()
        bad = (replace(rows[0], provenance="FULL_RELIABILITY_REPEAT"), *rows[1:])
        with self.assertRaisesRegex(ValueError, "repeat/pilot"):
            fit_component_specialist(bad, authorization=self._authorization())


if __name__ == "__main__":
    unittest.main()
