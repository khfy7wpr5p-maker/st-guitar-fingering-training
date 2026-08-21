from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_development import (
    DevelopmentEvent,
    DEVELOPMENT_PERFORMERS,
    canonical_candidate,
    enumerate_voicing_candidates,
    feature_vector,
    low_total_fret_key,
    select_negative_candidates,
    verify_sealed_json,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    assert_frozen_protocol,
)


class GuitarSetVoicingDevelopmentTests(unittest.TestCase):
    def test_preregistration_is_still_exactly_frozen(self):
        assert_frozen_protocol()
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, "1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d")
        self.assertEqual(EXPECTED_FEATURE_SCHEMA_SHA256, "05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38")
        self.assertEqual(DEVELOPMENT_PERFORMERS, ("00", "01", "04", "05"))

    def test_e_minor_observed_voicing_is_physical_candidate(self):
        pitches = (40, 47, 52, 55)
        expected = ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0))
        candidates = enumerate_voicing_candidates(pitches)
        self.assertIn(expected, candidates)
        self.assertEqual(len({string for _, string, _ in expected}), 4)
        self.assertTrue(all(pitch == {1:64,2:59,3:55,4:50,5:45,6:40}[string] + fret for pitch, string, fret in expected))

    def test_frozen_feature_vector_is_28d_and_finite(self):
        candidate = ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0))
        values = feature_vector(candidate)
        self.assertEqual(len(values), 28)
        self.assertAlmostEqual(values[0], 0.5)
        self.assertAlmostEqual(values[5], 0.0)
        self.assertAlmostEqual(values[6], 3 / 5)

    def test_negative_sampling_is_order_independent_and_capped(self):
        candidates = enumerate_voicing_candidates((52, 55, 59))
        observed = candidates[0]
        event_a = DevelopmentEvent("00", "r", "v", observed, candidates)
        event_b = DevelopmentEvent("00", "r", "v", observed, tuple(reversed(candidates)))
        selected_a = select_negative_candidates(event_a)
        selected_b = select_negative_candidates(event_b)
        self.assertEqual(selected_a, selected_b)
        self.assertLessEqual(len(selected_a), 32)
        self.assertNotIn(observed, selected_a)

    def test_baseline_has_canonical_tie_break(self):
        a = ((52, 4, 2), (55, 3, 0))
        b = ((52, 3, 9), (55, 2, 0))
        self.assertLess(low_total_fret_key(a), low_total_fret_key(b))
        self.assertEqual(canonical_candidate(a), "[[52,4,2],[55,3,0]]")

    def test_committed_development_evidence_and_model_are_sealed_and_nonproduction(self):
        root = Path(__file__).parents[1]
        evidence = json.loads((root / "evidence/stage7g_e3_guitarset_observed_voicing_development_v1.json").read_text(encoding="utf-8"))
        model = json.loads((root / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json").read_text(encoding="utf-8"))
        verify_sealed_json(evidence, "evidence_sha256")
        verify_sealed_json(model, "artifact_sha256")
        self.assertTrue(evidence["development_pass"])
        self.assertEqual(evidence["development_source_counts"]["ambiguous_voicings"], 7919)
        self.assertEqual(evidence["macro"]["top1_fold_wins"], 4)
        self.assertEqual(evidence["macro"]["mrr_fold_wins"], 4)
        self.assertFalse(evidence["validation_performer_opened"])
        self.assertFalse(evidence["untouched_final_performer_opened"])
        self.assertFalse(evidence["checkpoint_authorized"])
        self.assertFalse(evidence["runtime_connection_authorized"])
        self.assertEqual(evidence["sealed_development_model_artifact_sha256"], model["artifact_sha256"])
        self.assertTrue(model["validation_only_artifact"])
        self.assertFalse(model["checkpoint_authorized"])
        self.assertFalse(model["runtime_connection_authorized"])


if __name__ == "__main__":
    unittest.main()
