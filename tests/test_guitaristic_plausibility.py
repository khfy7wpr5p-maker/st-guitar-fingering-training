from __future__ import annotations

import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.guitaristic_plausibility import (
    B001_FIVE_DISTINCT_POSITIVE_FRETS,
    D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY,
    H001_MIN_FINGER_PROXY_GE_6,
    S1H_NO_PLAUSIBLE_CANDIDATE,
    S1H_OK,
    analyze_guitaristic_plausibility,
    analyze_valid_chord_voicings,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _assessment(result, candidate):
    canonical = tuple(sorted(candidate))
    return next(item for item in result.assessments if item.candidate == canonical)


class GuitaristicPlausibilityTests(unittest.TestCase):
    def test_observed_open_c_regression_remains_plausible(self):
        pitches = (55, 60, 64)
        observed = ((55, 3, 0), (60, 2, 1), (64, 1, 0))
        self.assertIn(observed, valid_chord_voicings(pitches, STANDARD_TUNING))
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        item = _assessment(result, observed)
        self.assertEqual(item.classification, "PLAUSIBLE")
        self.assertFalse(item.pruned)
        self.assertEqual(item.facts.open_strings, (1, 3))
        self.assertEqual(item.facts.conservative_minimum_finger_proxy, 1)

    def test_geometry_helper_is_reused_and_extended_deterministically(self):
        pitches = (55, 60, 64)
        candidate = ((55, 3, 0), (60, 2, 1), (64, 1, 0))
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        facts = _assessment(result, candidate).facts
        geometry = dict(facts.geometry)
        self.assertEqual(geometry["open_note_count"], 2.0)
        self.assertEqual(geometry["fretted_note_count"], 1.0)
        self.assertEqual(geometry["positive_fret_span"], 0.0)
        self.assertEqual(facts.fretted_string_topology, ("O", "F", "O", "-", "-", "-"))
        self.assertEqual(facts.contiguous_fretted_runs, ((2,),))
        self.assertEqual(facts.isolated_fretted_string_count, 1)
        self.assertEqual(facts.internal_gap_positions, ())
        self.assertEqual(facts.effective_fretted_hand_span, 0)

    def test_six_distinct_positive_frets_is_the_only_v1_hard_prune(self):
        candidate = (
            (51, 6, 11),
            (54, 5, 9),
            (57, 4, 7),
            (60, 3, 5),
            (62, 2, 3),
            (65, 1, 1),
        )
        pitches = tuple(pitch for pitch, _, _ in candidate)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertIn(candidate, authority)
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        item = _assessment(result, candidate)
        self.assertEqual(item.classification, "IMPRACTICAL")
        self.assertTrue(item.pruned)
        self.assertEqual(item.reason_codes, (H001_MIN_FINGER_PROXY_GE_6,))
        self.assertEqual(result.status, S1H_OK)
        self.assertNotIn(candidate, result.retained_candidates)
        self.assertEqual(set(result.raw_candidates), set(authority))

    def test_full_authoritative_all_pruned_reports_no_plausible_candidate(self):
        pitches = (41, 47, 53, 59, 80, 81)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertEqual(len(authority), 2)
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertEqual(set(result.raw_candidates), set(authority))
        self.assertEqual(result.retained_candidates, ())
        self.assertEqual(result.status, S1H_NO_PLAUSIBLE_CANDIDATE)
        self.assertTrue(all(item.pruned for item in result.assessments))
        self.assertTrue(all(
            item.reason_codes == (H001_MIN_FINGER_PROXY_GE_6,)
            for item in result.assessments
        ))

    def test_five_distinct_positive_frets_is_borderline_but_retained(self):
        pitches = (41, 47, 53, 59, 64)
        candidate = (
            (41, 6, 1),
            (47, 5, 2),
            (53, 4, 3),
            (59, 3, 4),
            (64, 2, 5),
        )
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertIn(candidate, authority)
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        item = _assessment(result, candidate)
        self.assertEqual(item.classification, "BORDERLINE")
        self.assertFalse(item.pruned)
        self.assertEqual(item.reason_codes, (B001_FIVE_DISTINCT_POSITIVE_FRETS,))
        self.assertIn(candidate, result.retained_candidates)

    def test_open_strings_high_fret_and_internal_gap_do_not_prune_alone(self):
        cases = (
            ((59, 2, 0), (64, 1, 0)),
            ((64, 6, 24), (69, 5, 24)),
            ((56, 3, 1), (65, 1, 1)),
        )
        for candidate in cases:
            pitches = tuple(sorted(pitch for pitch, _, _ in candidate))
            with self.subTest(candidate=candidate):
                self.assertIn(tuple(sorted(candidate)), valid_chord_voicings(pitches, STANDARD_TUNING))
                result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
                item = _assessment(result, candidate)
                self.assertFalse(item.pruned)
                self.assertIn(item.classification, ("PLAUSIBLE", "BORDERLINE", "DOMINATED"))

    def test_dominance_is_diagnostic_only_and_compared_id_is_stable(self):
        wider = ((65, 1, 1), (67, 2, 8))
        narrower = ((65, 2, 6), (67, 1, 3))
        pitches = (65, 67)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertIn(wider, authority)
        self.assertIn(tuple(sorted(narrower)), authority)
        result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
        wider_item = _assessment(result, wider)
        narrower_item = _assessment(result, narrower)
        self.assertEqual(wider_item.classification, "DOMINATED")
        self.assertFalse(wider_item.pruned)
        self.assertEqual(wider_item.reason_codes, (D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY,))
        self.assertEqual(wider_item.compared_candidate_id, narrower_item.candidate_id)
        self.assertIn(tuple(sorted(wider)), result.retained_candidates)
        self.assertIn(tuple(sorted(narrower)), result.retained_candidates)

    def test_order_invariance_and_ten_of_ten_repeatability(self):
        pitches = (65, 67)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        expected = analyze_guitaristic_plausibility(pitches, STANDARD_TUNING, authority)
        reversed_result = analyze_guitaristic_plausibility(
            pitches, STANDARD_TUNING, tuple(reversed(authority))
        )
        self.assertEqual(reversed_result, expected)
        for _ in range(10):
            self.assertEqual(
                analyze_guitaristic_plausibility(pitches, STANDARD_TUNING, authority),
                expected,
            )

    def test_full_set_property_invariants_across_canonical_pitch_sets(self):
        pitch_sets = (
            (55, 60, 64),
            (60, 64, 67),
            (65, 67),
            (52, 55, 59, 64),
        )
        for pitches in pitch_sets:
            with self.subTest(pitches=pitches):
                authority = valid_chord_voicings(pitches, STANDARD_TUNING)
                result = analyze_valid_chord_voicings(pitches, STANDARD_TUNING)
                self.assertEqual(set(result.raw_candidates), set(authority))
                self.assertTrue(set(result.retained_candidates).issubset(set(authority)))
                self.assertTrue(all(item.candidate in authority for item in result.assessments))
                self.assertEqual(len(result.raw_candidates), len(result.assessments))

    def test_incomplete_authoritative_subset_fails_closed(self):
        pitches = (65, 67)
        authority = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertGreater(len(authority), 1)
        with self.assertRaisesRegex(ValueError, "exactly match authoritative"):
            analyze_guitaristic_plausibility(
                pitches,
                STANDARD_TUNING,
                authority[:-1],
            )

    def test_invalid_non_authoritative_candidate_and_duplicates_fail_closed(self):
        invalid = ((65, 1, 2), (67, 2, 8))
        with self.assertRaisesRegex(ValueError, "outside authoritative"):
            analyze_guitaristic_plausibility((65, 67), STANDARD_TUNING, (invalid,))
        valid = ((65, 1, 1), (67, 2, 8))
        with self.assertRaisesRegex(ValueError, "duplicates"):
            analyze_guitaristic_plausibility((65, 67), STANDARD_TUNING, (valid, valid))


if __name__ == "__main__":
    unittest.main()
