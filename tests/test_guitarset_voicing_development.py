from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from st_guitar_fingering_training.guitarset_voicing_development import (
    DevelopmentEvent,
    DEVELOPMENT_PERFORMERS,
    _development_member,
    build_training_matrix,
    canonical_candidate,
    enumerate_voicing_candidates,
    feature_vector,
    fit_preregistered_model,
    low_total_fret_key,
    run_development_fit,
    select_negative_candidates,
    verify_sealed_json,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_NEGATIVE_SAMPLE_CAP,
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
        self.assertTrue(np.isfinite(np.asarray(values, dtype=np.float64)).all())
        self.assertAlmostEqual(values[0], 0.5)
        self.assertAlmostEqual(values[5], 0.0)
        self.assertAlmostEqual(values[6], 3 / 5)

    def test_development_archive_reader_excludes_validation_and_final_members(self):
        self.assertTrue(_development_member("annotation/00_BN1-129-Eb_comp.jams"))
        self.assertTrue(_development_member("annotation/05_SS3-98-C_comp.jams"))
        self.assertFalse(_development_member("annotation/03_BN1-129-Eb_comp.jams"))
        self.assertFalse(_development_member("annotation/02_BN1-129-Eb_comp.jams"))

    def test_negative_sampling_is_order_independent_and_capped(self):
        candidates = enumerate_voicing_candidates((52, 55, 59))
        observed = candidates[0]
        event_a = DevelopmentEvent("00", "r", "v", observed, candidates)
        event_b = DevelopmentEvent("00", "r", "v", observed, tuple(reversed(candidates)))
        selected_a = select_negative_candidates(event_a)
        selected_b = select_negative_candidates(event_b)
        self.assertEqual(selected_a, selected_b)
        self.assertLessEqual(len(selected_a), GUITARSET_NEGATIVE_SAMPLE_CAP)
        self.assertNotIn(observed, selected_a)
        self.assertEqual(len(selected_a), len(set(selected_a)))

    def test_pairwise_rows_are_exactly_symmetric(self):
        candidates = enumerate_voicing_candidates((52, 55, 59))
        event = DevelopmentEvent("00", "r", "v2", candidates[0], candidates)
        X, y = build_training_matrix((event,))
        selected_count = len(select_negative_candidates(event))
        self.assertEqual(X.shape, (selected_count * 2, 28))
        self.assertEqual(y.tolist()[0::2], [1] * selected_count)
        self.assertEqual(y.tolist()[1::2], [0] * selected_count)
        for index in range(0, len(X), 2):
            np.testing.assert_allclose(X[index], -X[index + 1], rtol=0, atol=0)

    def test_frozen_model_configuration_is_used(self):
        candidates = enumerate_voicing_candidates((52, 55, 59))
        event = DevelopmentEvent("00", "r", "v3", candidates[0], candidates)
        X, y = build_training_matrix((event,))
        model = fit_preregistered_model(X, y)
        logistic = model.named_steps["logisticregression"]
        self.assertEqual(logistic.C, 1.0)
        self.assertFalse(logistic.fit_intercept)
        self.assertIsNone(logistic.class_weight)
        self.assertEqual(logistic.solver, "lbfgs")
        self.assertEqual(logistic.max_iter, 2000)
        self.assertEqual(logistic.random_state, 0)

    def test_baseline_has_canonical_tie_break(self):
        a = ((52, 4, 2), (55, 3, 0))
        b = ((52, 3, 9), (55, 2, 0))
        self.assertLess(low_total_fret_key(a), low_total_fret_key(b))
        self.assertEqual(canonical_candidate(a), "[[52,4,2],[55,3,0]]")

    def test_runner_refuses_non_preregistered_reproduction_count_before_archive_access(self):
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            run_development_fit("does-not-exist.zip", reproduction_runs=9)

    def test_committed_development_evidence_and_model_are_sealed_and_nonproduction(self):
        root = Path(__file__).parents[1]
        evidence = json.loads((root / "evidence/stage7g_e3_guitarset_observed_voicing_development_v1.json").read_text(encoding="utf-8"))
        model = json.loads((root / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json").read_text(encoding="utf-8"))
        verify_sealed_json(evidence, "evidence_sha256")
        verify_sealed_json(model, "artifact_sha256")
        self.assertEqual(evidence["status"], "DEVELOPMENT_PASS_MODEL_SEALED_VALIDATION_CLOSED")
        self.assertTrue(evidence["development_pass"])
        self.assertEqual(evidence["development_source_counts"]["ambiguous_voicings"], 7919)
        self.assertEqual(evidence["gate"]["deterministic_reproduction"]["observed_identical_runs"], 10)
        self.assertTrue(all(item["pass"] for item in evidence["gate"].values()))
        self.assertEqual(evidence["macro"]["top1_fold_wins"], 4)
        self.assertEqual(evidence["macro"]["mrr_fold_wins"], 4)
        self.assertGreaterEqual(evidence["macro"]["event_top1_delta"], 0.03)
        self.assertGreaterEqual(evidence["macro"]["event_mrr_delta"], 0.05)
        self.assertFalse(evidence["validation_performer_opened"])
        self.assertFalse(evidence["untouched_final_performer_opened"])
        self.assertFalse(evidence["validation_access_authorized"])
        self.assertFalse(evidence["final_access_authorized"])
        self.assertFalse(evidence["checkpoint_authorized"])
        self.assertFalse(evidence["runtime_connection_authorized"])
        self.assertEqual(evidence["sealed_development_model_artifact_sha256"], model["artifact_sha256"])
        self.assertTrue(model["validation_only_artifact"])
        self.assertFalse(model["checkpoint_authorized"])
        self.assertFalse(model["runtime_connection_authorized"])
        self.assertEqual(model["protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(model["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(evidence["next_gate"], "OBSERVED_VOICING_MODEL_VALIDATION_ONE_SHOT")


if __name__ == "__main__":
    unittest.main()
