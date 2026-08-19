from __future__ import annotations

import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.fingering_feasibility import (
    H101_MIN_STANDARD_FINGERS_GE_5,
    S1HB_NO_STANDARD_FINGERING_CANDIDATE,
    S1HB_OK,
    U100_UPSTREAM_S1H_A_PRUNED,
    analyze_standard_fingering_feasibility,
    fretting_resource_facts,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _canonical(candidate):
    return tuple(sorted(candidate))


def _assessment(result, candidate):
    canonical = _canonical(candidate)
    return next(item for item in result.assessments if item.candidate == canonical)


class FingeringFeasibilityTests(unittest.TestCase):
    def test_observed_open_c_regression_remains_resource_feasible(self):
        pitches = (55, 60, 64)
        observed = ((55, 3, 0), (60, 2, 1), (64, 1, 0))
        self.assertIn(observed, valid_chord_voicings(pitches, STANDARD_TUNING))

        result = analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING)
        item = _assessment(result, observed)

        self.assertEqual(result.status, S1HB_OK)
        self.assertEqual(item.classification, "RESOURCE_FEASIBLE")
        self.assertFalse(item.pruned)
        self.assertIsNotNone(item.facts)
        assert item.facts is not None
        self.assertEqual(item.facts.minimum_standard_fingers, 1)
        self.assertEqual(item.facts.canonical_assignment, ((1, 1, (2,)),))
        self.assertIn(observed, result.retained_candidates)

    def test_five_distinct_positive_frets_are_rejected_by_four_finger_envelope(self):
        candidate = (
            (65, 1, 1),
            (61, 2, 2),
            (58, 3, 3),
            (54, 4, 4),
            (50, 5, 5),
        )
        pitches = tuple(pitch for pitch, _, _ in candidate)
        canonical = _canonical(candidate)
        self.assertIn(canonical, valid_chord_voicings(pitches, STANDARD_TUNING))

        result = analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING)
        item = _assessment(result, candidate)

        self.assertEqual(item.classification, "RESOURCE_INFEASIBLE")
        self.assertTrue(item.pruned)
        self.assertEqual(item.reason_codes, (H101_MIN_STANDARD_FINGERS_GE_5,))
        self.assertIsNotNone(item.facts)
        assert item.facts is not None
        self.assertEqual(item.facts.minimum_standard_fingers, 5)
        self.assertEqual(item.facts.canonical_assignment, ())
        self.assertNotIn(canonical, result.retained_candidates)
        self.assertIn(canonical, result.upstream_retained_candidates)

    def test_open_string_blocks_same_fret_continuous_barre(self):
        candidate = _canonical(((65, 1, 1), (59, 2, 0), (56, 3, 1)))
        facts = fretting_resource_facts(candidate)

        self.assertEqual(facts.positive_frets, (1,))
        self.assertEqual(tuple(group.strings for group in facts.groups), ((1,), (3,)))
        self.assertEqual(facts.blockers_by_fret, ((1, (2,)),))
        self.assertEqual(facts.minimum_standard_fingers, 2)
        self.assertEqual(facts.canonical_assignment, ((1, 1, (1,)), (2, 1, (3,))))

    def test_lower_fretted_intervening_string_blocks_higher_barre(self):
        candidate = _canonical(((67, 1, 3), (60, 2, 1), (58, 3, 3)))
        facts = fretting_resource_facts(candidate)

        self.assertEqual(facts.positive_frets, (1, 3))
        self.assertEqual(tuple((group.fret, group.strings) for group in facts.groups), (
            (1, (2,)),
            (3, (1,)),
            (3, (3,)),
        ))
        self.assertEqual(facts.blockers_by_fret, ((1, ()), (3, (2,))))
        self.assertEqual(facts.minimum_standard_fingers, 3)

    def test_higher_fretted_intervening_string_can_override_lower_barre(self):
        candidate = _canonical(((65, 1, 1), (62, 2, 3), (56, 3, 1)))
        facts = fretting_resource_facts(candidate)

        self.assertEqual(facts.positive_frets, (1, 3))
        self.assertEqual(tuple((group.fret, group.strings) for group in facts.groups), (
            (1, (1, 3)),
            (3, (2,)),
        ))
        self.assertEqual(facts.blockers_by_fret, ((1, ()), (3, ())))
        self.assertEqual(facts.minimum_standard_fingers, 2)
        self.assertEqual(facts.groups[0].span_start_string, 1)
        self.assertEqual(facts.groups[0].span_end_string, 3)

    def test_unused_intervening_string_does_not_block_barre(self):
        candidate = _canonical(((65, 1, 1), (56, 3, 1)))
        facts = fretting_resource_facts(candidate)

        self.assertEqual(len(facts.groups), 1)
        self.assertEqual(facts.groups[0].strings, (1, 3))
        self.assertEqual(facts.groups[0].span_start_string, 1)
        self.assertEqual(facts.groups[0].span_end_string, 3)
        self.assertEqual(facts.minimum_standard_fingers, 1)

    def test_upstream_all_pruned_state_is_preserved_and_explicit(self):
        pitches = (41, 47, 53, 59, 80, 81)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertEqual(len(authority), 2)

        result = analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING)

        self.assertEqual(result.raw_candidates, tuple(sorted(result.raw_candidates, key=lambda item: next(
            assessment.candidate_id for assessment in result.assessments if assessment.candidate == item
        ))))
        self.assertEqual(result.upstream_retained_candidates, ())
        self.assertEqual(result.retained_candidates, ())
        self.assertEqual(result.status, S1HB_NO_STANDARD_FINGERING_CANDIDATE)
        self.assertTrue(all(item.classification == "UPSTREAM_PRUNED" for item in result.assessments))
        self.assertTrue(all(item.reason_codes == (U100_UPSTREAM_S1H_A_PRUNED,) for item in result.assessments))
        self.assertTrue(all(item.facts is None for item in result.assessments))

    def test_full_set_subset_and_no_reintroduction_invariants(self):
        pitch_sets = (
            (55, 60, 64),
            (60, 64, 67),
            (65, 67),
            (52, 55, 59, 64),
            (41, 47, 53, 59, 64),
        )
        for pitches in pitch_sets:
            with self.subTest(pitches=pitches):
                authority = set(valid_chord_voicings(pitches, STANDARD_TUNING))
                result = analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING)
                self.assertEqual(set(result.raw_candidates), authority)
                self.assertTrue(set(result.retained_candidates).issubset(set(result.upstream_retained_candidates)))
                self.assertTrue(set(result.retained_candidates).issubset(authority))
                upstream_pruned = {
                    item.candidate
                    for item in result.assessments
                    if item.classification == "UPSTREAM_PRUNED"
                }
                self.assertFalse(upstream_pruned & set(result.retained_candidates))
                self.assertEqual(len(result.assessments), len(result.raw_candidates))

    def test_canonical_assignment_and_ten_of_ten_repeatability(self):
        pitches = (55, 60, 64)
        expected = analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING)
        for _ in range(10):
            self.assertEqual(
                analyze_standard_fingering_feasibility(pitches, STANDARD_TUNING),
                expected,
            )

        item = _assessment(expected, ((55, 3, 0), (60, 2, 1), (64, 1, 0)))
        assert item.facts is not None
        self.assertEqual(item.facts.canonical_assignment, ((1, 1, (2,)),))


if __name__ == "__main__":
    unittest.main()
