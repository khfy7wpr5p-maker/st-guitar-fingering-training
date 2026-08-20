from __future__ import annotations

import unittest

from st_guitar_fingering_training.finger_assignments import generate_standard_fingerings
from st_guitar_fingering_training.finger_assignments_v2 import (
    S1HC_V2_RULE_VERSION,
    generate_standard_fingerings_v2,
)
from st_guitar_fingering_training.teacher_correction_manual_v1 import (
    build_manual_regression_manifest,
    build_manual_task,
    render_manual_regression_html,
    validate_manual_teacher_solution,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)
E_MINOR_PITCHES = (40, 47, 52, 55)
E_MINOR_VOICING = ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0))
E_MINOR_TEACHER = (
    {"pitch_midi": 40, "string": 6, "fret": 0, "finger": 0},
    {"pitch_midi": 47, "string": 5, "fret": 2, "finger": 2},
    {"pitch_midi": 52, "string": 4, "fret": 2, "finger": 3},
    {"pitch_midi": 55, "string": 3, "fret": 0, "finger": 0},
)


def _candidate(result, voicing):
    frozen = tuple(sorted(voicing))
    return next(row for row in result.candidates if row.candidate == frozen)


class TeacherCorrectionManualRegressionTests(unittest.TestCase):
    def test_v1_reproduces_same_fret_forced_barre_gap(self):
        item = _candidate(generate_standard_fingerings(E_MINOR_PITCHES, STANDARD_TUNING), E_MINOR_VOICING)
        teacher_placements = tuple(sorted(
            (row["pitch_midi"], row["string"], row["fret"], row["finger"])
            for row in E_MINOR_TEACHER
        ))
        self.assertNotIn(teacher_placements, {a.placements for a in item.assignments})
        self.assertTrue(any(a.barres for a in item.assignments))

    def test_v2_keeps_barre_as_option_but_adds_separate_finger_solution(self):
        result = generate_standard_fingerings_v2(E_MINOR_PITCHES, STANDARD_TUNING)
        self.assertEqual(result.rule_version, S1HC_V2_RULE_VERSION)
        item = _candidate(result, E_MINOR_VOICING)
        teacher_placements = tuple(sorted(
            (row["pitch_midi"], row["string"], row["fret"], row["finger"])
            for row in E_MINOR_TEACHER
        ))
        exact = [a for a in item.assignments if a.placements == teacher_placements]
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0].barres, ())
        self.assertTrue(any(a.barres for a in item.assignments))

    def test_manual_validator_accepts_requested_e_minor_shape_exactly(self):
        validated = validate_manual_teacher_solution(
            pitches_midi=E_MINOR_PITCHES,
            tuning=STANDARD_TUNING,
            rows=E_MINOR_TEACHER,
        )
        self.assertEqual(validated["status"], "VALID_EXACT_S1HC_V2")
        self.assertEqual(validated["hc_rule_version"], S1HC_V2_RULE_VERSION)
        self.assertEqual(validated["barres"], [])
        self.assertEqual(
            {(r["string"], r["fret"], r["finger"]) for r in validated["placements"]},
            {(6, 0, 0), (5, 2, 2), (4, 2, 3), (3, 0, 0)},
        )

    def test_manual_validator_rejects_wrong_string_fret_pitch(self):
        bad = list(E_MINOR_TEACHER)
        bad[1] = {"pitch_midi": 47, "string": 5, "fret": 3, "finger": 2}
        with self.assertRaisesRegex(ValueError, "does not produce"):
            validate_manual_teacher_solution(
                pitches_midi=E_MINOR_PITCHES,
                tuning=STANDARD_TUNING,
                rows=bad,
            )

    def test_manual_validator_rejects_duplicate_string(self):
        bad = list(E_MINOR_TEACHER)
        bad[2] = {"pitch_midi": 52, "string": 5, "fret": 7, "finger": 3}
        with self.assertRaisesRegex(ValueError, "one string twice"):
            validate_manual_teacher_solution(
                pitches_midi=E_MINOR_PITCHES,
                tuning=STANDARD_TUNING,
                rows=bad,
            )

    def test_short_regression_html_contains_manual_edit_and_reject_paths(self):
        task = build_manual_task(
            task_name="Mi minör — açık pozisyon",
            pitches_midi=E_MINOR_PITCHES,
            tuning=STANDARD_TUNING,
        )
        manifest = build_manual_regression_manifest((task,))
        rendered = render_manual_regression_html(manifest)
        self.assertIn("ELLE DÜZELT", rendered)
        self.assertIn("DOĞRULA + KAYDET", rendered)
        self.assertIn("ELE / REDDET", rendered)
        self.assertIn("exact S1-H-C.v2", rendered)
        self.assertFalse(manifest["training_authorized"])

    def test_v2_ten_of_ten_repeatability(self):
        expected = generate_standard_fingerings_v2(E_MINOR_PITCHES, STANDARD_TUNING)
        for _ in range(10):
            self.assertEqual(generate_standard_fingerings_v2(E_MINOR_PITCHES, STANDARD_TUNING), expected)


if __name__ == "__main__":
    unittest.main()
