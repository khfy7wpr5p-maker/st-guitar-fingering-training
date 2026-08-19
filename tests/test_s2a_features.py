from __future__ import annotations

import unittest

from st_guitar_fingering_training.finger_assignments import StandardFingering
from st_guitar_fingering_training.s2a_features import (
    S2A_FEATURE_LIST_SHA256,
    S2A_FEATURE_NAMES,
    assignment_feature_vector,
)


class S2AFeatureTests(unittest.TestCase):
    def test_feature_contract_is_exactly_30_and_distinguishes_open_from_unused(self):
        assignment = StandardFingering(
            assignment_id="fingering-sha256:test-open",
            placements=((64, 1, 0, 0), (60, 2, 1, 1)),
            barres=(),
        )
        values = assignment_feature_vector(assignment)

        self.assertEqual(len(S2A_FEATURE_NAMES), 30)
        self.assertEqual(len(values), 30)
        self.assertEqual(len(S2A_FEATURE_LIST_SHA256), 64)
        self.assertEqual(values[0:3], (1.0, 0.0, 0.0))
        self.assertEqual(values[3:6], (1.0, 1.0 / 24.0, 0.25))
        self.assertEqual(values[6:9], (0.0, 0.0, 0.0))
        self.assertEqual(values[18], 0.5)
        self.assertEqual(values[23], 0.25)

    def test_barre_override_and_cross_finger_mechanics_follow_frozen_semantics(self):
        assignment = StandardFingering(
            assignment_id="fingering-sha256:test-barre",
            placements=((65, 1, 1, 1), (62, 2, 3, 2), (56, 3, 1, 1)),
            barres=((1, 1, 1, 3),),
        )
        values = assignment_feature_vector(assignment)

        self.assertAlmostEqual(values[24], 0.25)
        self.assertAlmostEqual(values[25], 2.0 / 5.0)
        self.assertAlmostEqual(values[26], 2.0 / 20.0)
        self.assertAlmostEqual(values[27], 1.0 / 3.0)
        self.assertAlmostEqual(values[28], 2.0 / 24.0)
        self.assertAlmostEqual(values[29], 0.0)

    def test_same_fret_distinct_fingers_are_described_not_rejected(self):
        assignment = StandardFingering(
            assignment_id="fingering-sha256:test-same-fret",
            placements=((65, 1, 1, 1), (56, 3, 1, 2)),
            barres=(),
        )
        values = assignment_feature_vector(assignment)

        self.assertEqual(values[28], 0.0)
        self.assertAlmostEqual(values[29], 1.0 / 6.0)

    def test_invalid_s1hc_lineage_shape_fails_closed(self):
        bad = StandardFingering(
            assignment_id="not-an-s1hc-id",
            placements=((65, 1, 1, 1),),
            barres=(),
        )
        with self.assertRaises(ValueError):
            assignment_feature_vector(bad)

        reused_finger = StandardFingering(
            assignment_id="fingering-sha256:bad-finger",
            placements=((65, 1, 1, 1), (62, 2, 3, 1)),
            barres=(),
        )
        with self.assertRaises(ValueError):
            assignment_feature_vector(reused_finger)


if __name__ == "__main__":
    unittest.main()
