from __future__ import annotations

import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.finger_assignments import (
    S1HC_RULE_VERSION,
    generate_standard_fingerings,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _canonical(candidate):
    return tuple(sorted(candidate))


def _candidate_result(result, candidate):
    canonical = _canonical(candidate)
    return next(item for item in result.candidates if item.candidate == canonical)


class StandardFingerAssignmentTests(unittest.TestCase):
    def test_open_c_gets_four_single_finger_assignments_and_open_finger_zero(self):
        pitches = (55, 60, 64)
        candidate = ((55, 3, 0), (60, 2, 1), (64, 1, 0))
        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(result.rule_version, S1HC_RULE_VERSION)
        self.assertEqual(len(item.assignments), 4)
        observed_fretting_fingers = set()
        for assignment in item.assignments:
            by_string = {string: finger for _, string, _, finger in assignment.placements}
            self.assertEqual(by_string[1], 0)
            self.assertEqual(by_string[3], 0)
            self.assertIn(by_string[2], (1, 2, 3, 4))
            observed_fretting_fingers.add(by_string[2])
        self.assertEqual(observed_fretting_fingers, {1, 2, 3, 4})

    def test_all_open_voicing_has_one_zero_finger_assignment(self):
        pitches = (59, 64)
        candidate = ((59, 2, 0), (64, 1, 0))
        self.assertIn(_canonical(candidate), valid_chord_voicings(pitches, STANDARD_TUNING))

        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(len(item.assignments), 1)
        assignment = item.assignments[0]
        self.assertEqual(assignment.barres, ())
        self.assertTrue(all(finger == 0 for _, _, _, finger in assignment.placements))

    def test_passable_noncontiguous_same_fret_targets_share_one_barre_finger(self):
        pitches = (56, 65)
        candidate = ((65, 1, 1), (56, 3, 1))
        self.assertIn(_canonical(candidate), valid_chord_voicings(pitches, STANDARD_TUNING))

        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(len(item.assignments), 4)
        for assignment in item.assignments:
            fretted = [(string, finger) for _, string, fret, finger in assignment.placements if fret > 0]
            self.assertEqual(len({finger for _, finger in fretted}), 1)
            finger = fretted[0][1]
            self.assertEqual(assignment.barres, ((finger, 1, 1, 3),))

    def test_open_string_block_splits_same_fret_into_two_distinct_fingers(self):
        pitches = (56, 59, 65)
        candidate = ((65, 1, 1), (59, 2, 0), (56, 3, 1))
        self.assertIn(_canonical(candidate), valid_chord_voicings(pitches, STANDARD_TUNING))

        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(len(item.assignments), 12)
        for assignment in item.assignments:
            by_string = {string: finger for _, string, _, finger in assignment.placements}
            self.assertEqual(by_string[2], 0)
            self.assertNotEqual(by_string[1], by_string[3])
            self.assertEqual(assignment.barres, ())

    def test_higher_fret_override_generates_only_monotonic_finger_pairs(self):
        pitches = (56, 62, 65)
        candidate = ((65, 1, 1), (62, 2, 3), (56, 3, 1))
        self.assertIn(_canonical(candidate), valid_chord_voicings(pitches, STANDARD_TUNING))

        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(len(item.assignments), 6)
        for assignment in item.assignments:
            by_string = {string: finger for _, string, _, finger in assignment.placements}
            self.assertEqual(by_string[1], by_string[3])
            self.assertLess(by_string[1], by_string[2])
            self.assertEqual(assignment.barres, ((by_string[1], 1, 1, 3),))

    def test_four_distinct_frets_have_exactly_one_monotonic_assignment(self):
        candidate = (
            (65, 1, 1),
            (61, 2, 2),
            (58, 3, 3),
            (54, 4, 4),
        )
        pitches = tuple(pitch for pitch, _, _ in candidate)
        self.assertIn(_canonical(candidate), valid_chord_voicings(pitches, STANDARD_TUNING))

        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(len(item.assignments), 1)
        assignment = item.assignments[0]
        fret_finger = sorted((fret, finger) for _, _, fret, finger in assignment.placements if fret > 0)
        self.assertEqual(fret_finger, [(1, 1), (2, 2), (3, 3), (4, 4)])

    def test_five_distinct_frets_pruned_by_hb_receive_no_assignments(self):
        candidate = (
            (65, 1, 1),
            (61, 2, 2),
            (58, 3, 3),
            (54, 4, 4),
            (50, 5, 5),
        )
        pitches = tuple(pitch for pitch, _, _ in candidate)
        result = generate_standard_fingerings(pitches, STANDARD_TUNING)
        item = _candidate_result(result, candidate)

        self.assertEqual(item.upstream_classification, "RESOURCE_INFEASIBLE")
        self.assertEqual(item.assignments, ())
        self.assertNotIn(_canonical(candidate), result.retained_candidates)

    def test_assignment_ids_are_unique_and_preserve_every_retained_voicing(self):
        pitch_sets = (
            (55, 60, 64),
            (60, 64, 67),
            (65, 67),
            (52, 55, 59, 64),
        )
        for pitches in pitch_sets:
            with self.subTest(pitches=pitches):
                result = generate_standard_fingerings(pitches, STANDARD_TUNING)
                retained = set(result.retained_candidates)
                for item in result.candidates:
                    if item.candidate in retained:
                        self.assertGreater(len(item.assignments), 0)
                    else:
                        self.assertEqual(item.assignments, ())
                    ids = [assignment.assignment_id for assignment in item.assignments]
                    self.assertEqual(len(ids), len(set(ids)))
                    for assignment in item.assignments:
                        restored = tuple(sorted(
                            (pitch, string, fret)
                            for pitch, string, fret, _ in assignment.placements
                        ))
                        self.assertEqual(restored, item.candidate)
                self.assertEqual(
                    result.total_assignment_count,
                    sum(len(item.assignments) for item in result.candidates),
                )

    def test_ten_of_ten_repeatability(self):
        pitches = (55, 60, 64)
        expected = generate_standard_fingerings(pitches, STANDARD_TUNING)
        for _ in range(10):
            self.assertEqual(generate_standard_fingerings(pitches, STANDARD_TUNING), expected)


if __name__ == "__main__":
    unittest.main()
