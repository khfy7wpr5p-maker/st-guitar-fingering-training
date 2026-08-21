from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.guitarset_shadow_integration import (
    STANDARD_TUNING,
    build_shadow_observation,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json"
FINAL = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_final_v1.json"
RETENTION = ROOT / "evidence/stage7g_e3_guitarset_observed_voicing_checkpoint_retention_v1.json"


def run_shadow(pitches, candidates, selected=None, *, tuning=STANDARD_TUNING, retention=RETENTION):
    return build_shadow_observation(
        pitches_midi=pitches,
        tuning=tuning,
        authoritative_candidates=candidates,
        authoritative_selected_candidate=selected,
        model_path=MODEL,
        final_evidence_path=FINAL,
        retention_decision_path=retention,
    )


class GuitarSetShadowIntegrationTests(unittest.TestCase):
    def test_complete_in_domain_authority_set_can_be_scored_without_changing_authoritative_choice(self):
        pitches = (44, 51)
        candidates = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(all(fret <= 19 for candidate in candidates for _, _, fret in candidate))
        authoritative = candidates[0]

        report = run_shadow(pitches, candidates, authoritative)

        self.assertEqual(report["status"], "SHADOW_SCORED_NON_AUTHORITATIVE")
        self.assertTrue(report["shadow_scored"])
        self.assertTrue(report["model_domain_complete"])
        self.assertEqual(report["authoritative_candidate_count"], len(candidates))
        self.assertEqual(
            report["authoritative_selected_candidate"],
            [list(row) for row in authoritative],
        )
        self.assertEqual(len(report["candidate_scores"]), len(candidates))
        self.assertEqual(sorted(row["rank"] for row in report["candidate_scores"]), list(range(1, len(candidates) + 1)))
        for key in (
            "authoritative_decision_effect_authorized",
            "checkpoint_mutation_authorized",
            "refit_authorized",
            "tuning_authorized",
            "runtime_connection_authorized",
            "production_authorized",
        ):
            self.assertFalse(report[key], key)

    def test_incomplete_authoritative_candidate_subset_fails_closed_before_scoring(self):
        pitches = (44, 51)
        candidates = valid_chord_voicings(pitches, STANDARD_TUNING)
        with self.assertRaisesRegex(ValueError, "complete exact"):
            run_shadow(pitches, candidates[:-1])

    def test_injected_non_authoritative_candidate_fails_closed(self):
        pitches = (44, 51)
        candidates = list(valid_chord_voicings(pitches, STANDARD_TUNING))
        candidates.append(((44, 6, 4), (51, 1, 0)))
        with self.assertRaisesRegex(ValueError, "complete exact"):
            run_shadow(pitches, candidates)

    def test_engine_candidates_above_fret_19_are_not_truncated_or_scored(self):
        pitches = (60, 64)
        candidates = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertTrue(any(fret > 19 for candidate in candidates for _, _, fret in candidate))

        report = run_shadow(pitches, candidates, candidates[0])

        self.assertEqual(report["status"], "SHADOW_NOT_SCORED_MODEL_DOMAIN_INCOMPLETE")
        self.assertFalse(report["shadow_scored"])
        self.assertFalse(report["model_domain_complete"])
        self.assertGreater(report["out_of_model_domain_candidate_count"], 0)
        self.assertIsNone(report["shadow_model_top_candidate"])
        self.assertEqual(report["candidate_scores"], [])
        self.assertEqual(report["authoritative_candidate_count"], len(candidates))

    def test_nonstandard_tuning_is_rejected_instead_of_silently_remapped(self):
        pitches = (44, 51)
        drop_d = (64, 59, 55, 50, 45, 38)
        candidates = valid_chord_voicings(pitches, drop_d)
        with self.assertRaisesRegex(ValueError, "standard tuning"):
            run_shadow(pitches, candidates, tuning=drop_d)

    def test_tampered_checkpoint_retention_decision_fails_closed(self):
        payload = json.loads(RETENTION.read_text(encoding="utf-8"))
        payload["shadow_integration_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retention.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            pitches = (44, 51)
            candidates = valid_chord_voicings(pitches, STANDARD_TUNING)
            with self.assertRaises(ValueError):
                run_shadow(pitches, candidates, retention=path)

    def test_duplicate_authoritative_candidates_fail_closed(self):
        pitches = (44, 51)
        candidates = list(valid_chord_voicings(pitches, STANDARD_TUNING))
        candidates.append(candidates[0])
        with self.assertRaisesRegex(ValueError, "duplicates"):
            run_shadow(pitches, candidates)


if __name__ == "__main__":
    unittest.main()
