from __future__ import annotations

import unittest

from st_guitar_fingering_training.s2a_final import (
    family_block_bootstrap_ci,
    evaluate_s2a_untouched_final,
)
from st_guitar_fingering_training.s2a_ranker import build_s2a_corpus
from st_guitar_fingering_training.s2a_teacher import (
    S2A_CHOICE_EXPORT_SCHEMA,
    S2A_FINAL_PROVENANCE,
    build_s2a_teacher_package,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)
PITCHES = (55, 60, 64)


class _NoModelUse:
    def decision_function(self, _):
        raise AssertionError("model must not be touched while final preflight is closed")


class S2AFinalGateTests(unittest.TestCase):
    def _tiny_final_corpus(self):
        manifest, audit = build_s2a_teacher_package(
            family_id="untouched-family-001",
            event_id="untouched-event-001",
            pitches_midi=PITCHES,
            tuning=STANDARD_TUNING,
            provenance=S2A_FINAL_PROVENANCE,
        )
        payload = {
            "schema": S2A_CHOICE_EXPORT_SCHEMA,
            "annotation_blinded": True,
            "provenance": S2A_FINAL_PROVENANCE,
            "annotator_id": "teacher-final",
            "collected_at_utc": "2026-08-19T12:00:00Z",
            "choices": [
                {"task_id": task["task_id"], "response": "A"}
                for task in manifest["tasks"]
            ],
        }
        return build_s2a_corpus(
            ((manifest, audit, payload),),
            expected_provenance=S2A_FINAL_PROVENANCE,
        )

    def test_family_block_bootstrap_is_deterministic_and_family_level(self):
        deltas = {f"family-{index:02d}": 0.10 + (index % 3) * 0.01 for index in range(20)}
        expected = family_block_bootstrap_ci(deltas)
        self.assertGreater(expected[0], 0.0)
        self.assertGreaterEqual(expected[1], expected[0])
        for _ in range(10):
            self.assertEqual(family_block_bootstrap_ci(deltas), expected)

    def test_final_stays_closed_if_development_did_not_pass(self):
        corpus = self._tiny_final_corpus()
        report = {
            "stage": "7G-E3-S2-A",
            "protocol_version": "S2-A.v1",
            "status": "FAIL",
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
            "comparator_selection": {"selected": "LOW_FRET_BASELINE"},
        }
        with self.assertRaises(RuntimeError):
            evaluate_s2a_untouched_final(
                _NoModelUse(),
                corpus,
                report,
                development_family_ids=("development-family-001",),
            )

    def test_final_minimums_fail_before_model_is_touched(self):
        corpus = self._tiny_final_corpus()
        report = {
            "stage": "7G-E3-S2-A",
            "protocol_version": "S2-A.v1",
            "status": "PASS",
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
            "comparator_selection": {"selected": "LOW_FRET_BASELINE"},
        }
        with self.assertRaises(RuntimeError):
            evaluate_s2a_untouched_final(
                _NoModelUse(),
                corpus,
                report,
                development_family_ids=("development-family-001",),
            )

    def test_final_rejects_development_family_overlap_before_model_use(self):
        corpus = self._tiny_final_corpus()
        report = {
            "stage": "7G-E3-S2-A",
            "protocol_version": "S2-A.v1",
            "status": "PASS",
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
            "comparator_selection": {"selected": "COMPACT_BASELINE"},
        }
        with self.assertRaises(RuntimeError):
            evaluate_s2a_untouched_final(
                _NoModelUse(),
                corpus,
                report,
                development_family_ids=("untouched-family-001",),
            )


if __name__ == "__main__":
    unittest.main()
