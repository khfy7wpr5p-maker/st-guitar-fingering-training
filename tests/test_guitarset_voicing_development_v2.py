import math
import unittest

from st_guitar_fingering_training.guitarset_voicing_development import DevelopmentEvent
from st_guitar_fingering_training.guitarset_voicing_development_v2 import (
    enumerate_voicing_candidates_v2,
    feature_vector_v2,
    select_negative_candidates_v2,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import GUITARSET_VOICING_MAX_FRET as V1_MAX_FRET
from st_guitar_fingering_training.guitarset_voicing_prereg_v2 import GUITARSET_VOICING_MAX_FRET as V2_MAX_FRET


class GuitarSetVoicingDevelopmentV2Tests(unittest.TestCase):
    def test_v1_is_unchanged_and_v2_domain_is_0_20(self):
        self.assertEqual(V1_MAX_FRET, 19)
        self.assertEqual(V2_MAX_FRET, 20)

    def test_candidate_enumeration_reaches_fret20_without_exceeding_it(self):
        candidates = enumerate_voicing_candidates_v2((79, 84))
        self.assertTrue(candidates)
        self.assertTrue(any(any(fret == 20 for _, _, fret in candidate) for candidate in candidates))
        self.assertTrue(all(0 <= fret <= 20 for candidate in candidates for _, _, fret in candidate))

    def test_feature_vector_accepts_fret20_and_is_finite(self):
        candidate = ((79, 2, 20), (84, 1, 20))
        features = feature_vector_v2(candidate)
        self.assertEqual(len(features), 28)
        self.assertTrue(all(math.isfinite(value) for value in features))
        self.assertEqual(features[2], 1.0)

    def test_negative_selection_is_deterministic_and_preserves_observed(self):
        candidates = enumerate_voicing_candidates_v2((64, 67, 71))
        self.assertGreaterEqual(len(candidates), 2)
        event = DevelopmentEvent(
            performer="00",
            recording_id="r",
            voicing_id="v",
            observed=candidates[0],
            candidates=candidates,
        )
        first = select_negative_candidates_v2(event)
        second = select_negative_candidates_v2(event)
        self.assertEqual(first, second)
        self.assertNotIn(event.observed, first)
        self.assertTrue(all(candidate in event.candidates for candidate in first))


if __name__ == "__main__":
    unittest.main()
