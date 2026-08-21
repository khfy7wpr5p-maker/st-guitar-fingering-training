from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    FEATURE_SPECS,
    assert_frozen_protocol,
    feature_schema_sha256,
    protocol_payload,
    protocol_sha256,
)


class GuitarSetObservedVoicingPreregTests(unittest.TestCase):
    def test_frozen_hashes_and_authorization_boundary(self):
        assert_frozen_protocol()
        self.assertEqual(feature_schema_sha256(), EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(protocol_sha256(), EXPECTED_PROTOCOL_SHA256)
        protocol = protocol_payload()
        self.assertFalse(protocol["training_authorized"])
        self.assertFalse(protocol["checkpoint_authorized"])
        self.assertFalse(protocol["runtime_connection_authorized"])
        self.assertFalse(protocol["final_access_authorized"])

    def test_feature_schema_is_exact_28d_static_geometry(self):
        self.assertEqual(len(FEATURE_SPECS), 28)
        names = [name for name, _ in FEATURE_SPECS]
        self.assertEqual(len(names), len(set(names)))
        forbidden_fragments = ("teacher", "performer", "style", "previous", "next", "finger", "barre", "score")
        for name in names:
            self.assertFalse(any(fragment in name.lower() for fragment in forbidden_fragments))

    def test_candidate_contract_preserves_exact_e_minor_geometry(self):
        protocol = protocol_payload()
        tuning_map = protocol["candidate_set"]["tuning_midi_by_string"]
        tuning = tuple(tuning_map[str(string)] for string in range(1, 7))
        observed = ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0))
        candidates = tuple(
            candidate
            for candidate in valid_chord_voicings((40, 47, 52, 55), tuning)
            if max(fret for _, _, fret in candidate) <= protocol["candidate_set"]["max_fret"]
        )
        self.assertIn(observed, candidates)
        for candidate in candidates:
            self.assertEqual(tuple(sorted(pitch for pitch, _, _ in candidate)), (40, 47, 52, 55))
            self.assertEqual(len({string for _, string, _ in candidate}), len(candidate))
            self.assertTrue(all(0 <= fret <= 19 for _, _, fret in candidate))

    def test_training_and_final_roles_remain_separated(self):
        protocol = protocol_payload()
        self.assertEqual(protocol["development"]["roles"], ["DEVELOPMENT"])
        self.assertEqual(protocol["validation"]["performer"], "03")
        self.assertEqual(protocol["final"]["performer"], "02")
        self.assertTrue(protocol["final"]["no_refit_after_validation"])
        self.assertTrue(protocol["final"]["no_tuning_after_open"])
        self.assertEqual(
            protocol["final"]["pass_semantics"],
            "ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY",
        )

    def test_repository_evidence_matches_code_protocol_exactly(self):
        evidence_path = (
            Path(__file__).parents[1]
            / "evidence"
            / "stage7g_e3_guitarset_observed_voicing_model_prereg_v1.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "PREREGISTERED_TRAINING_CLOSED")
        self.assertEqual(evidence["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(evidence["protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(evidence["protocol"], protocol_payload())
        self.assertFalse(evidence["training_authorized"])
        self.assertFalse(evidence["final_access_authorized"])

    def test_thresholds_are_frozen_before_fit(self):
        protocol = protocol_payload()
        dev = protocol["development"]["pass"]
        validation = protocol["validation"]["pass"]
        final = protocol["final"]["pass"]
        self.assertEqual(dev["macro_event_top1_delta_vs_baseline_gte"], 0.03)
        self.assertEqual(dev["macro_event_mrr_delta_vs_baseline_gte"], 0.05)
        self.assertEqual(validation["event_top1_delta_vs_baseline_gte"], 0.02)
        self.assertEqual(validation["event_mrr_delta_vs_baseline_gte"], 0.05)
        self.assertEqual(validation["recording_block_bootstrap"]["repetitions"], 2000)
        self.assertEqual(validation["recording_block_bootstrap"]["seed"], 0)
        self.assertGreater(final["recording_block_bootstrap"]["lower_bound_gt"], -1e-12)


if __name__ == "__main__":
    unittest.main()
