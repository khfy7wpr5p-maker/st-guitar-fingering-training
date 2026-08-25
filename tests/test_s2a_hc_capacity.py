from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest

from st_guitar_fingering_training.s2a_hc_capacity import (
    S2A_HC_CAPACITY_RULE_VERSION,
    audit_hc_capacity,
    audit_to_dict,
)


TUNING = (64, 59, 55, 50, 45, 40)


def _event(
    index: int,
    *,
    chord: bool = True,
    pitches=(60, 64, 67),
    measure: str | None = None,
):
    return SimpleNamespace(
        measure=str(index + 1) if measure is None else measure,
        onset=str(index),
        voice="1",
        pitches_midi=tuple(pitches),
        tuning=TUNING,
        is_chord=chord,
    )


def _generated(count: int, *, duplicate: bool = False):
    assignments = []
    for index in range(count):
        assignment_id = "same" if duplicate else f"assignment-{index}"
        assignments.append(SimpleNamespace(assignment_id=assignment_id))
    return SimpleNamespace(
        candidates=(SimpleNamespace(assignments=tuple(assignments)),),
        total_assignment_count=count,
    )


class S2AHCCapacityTests(unittest.TestCase):
    def test_passes_at_eight_events_with_two_distinct_assignments(self):
        events = tuple(_event(index) for index in range(12))
        audit = audit_hc_capacity(events, generation_fn=lambda pitches, tuning: _generated(2))
        self.assertEqual(audit.rule_version, S2A_HC_CAPACITY_RULE_VERSION)
        self.assertTrue(audit.passed)
        self.assertEqual(audit.eligible_event_count, 8)
        self.assertEqual(audit.checked_chord_event_count, 8)
        self.assertFalse(audit.source_scan_exhausted)
        self.assertEqual(audit.reason, "S2A_HC_000_MIN_CAPACITY_REACHED")

    def test_preserves_musicxml_measure_identifiers_without_numeric_coercion(self):
        for measure in ("A1", "12A", "X", "001"):
            with self.subTest(measure=measure):
                audit = audit_hc_capacity(
                    (_event(0, measure=measure),),
                    min_eligible_events=1,
                    generation_fn=lambda pitches, tuning: _generated(2),
                )
                self.assertTrue(audit.passed)
                self.assertEqual(audit.qualifying_events[0].measure, measure)
                serialized = audit_to_dict(audit)
                self.assertEqual(serialized["qualifying_events"][0]["measure"], measure)

    def test_fails_only_after_source_exhaustion_below_eight(self):
        events = tuple(_event(index) for index in range(7))
        audit = audit_hc_capacity(events, generation_fn=lambda pitches, tuning: _generated(2))
        self.assertFalse(audit.passed)
        self.assertEqual(audit.eligible_event_count, 7)
        self.assertTrue(audit.source_scan_exhausted)
        self.assertEqual(audit.reason, "S2A_HC_001_INSUFFICIENT_ELIGIBLE_EVENTS")

    def test_one_assignment_event_is_not_s2a_hc_eligible(self):
        events = tuple(_event(index) for index in range(9))
        calls = {"count": 0}

        def generation(pitches, tuning):
            calls["count"] += 1
            return _generated(1 if calls["count"] <= 2 else 2)

        audit = audit_hc_capacity(events, generation_fn=generation)
        self.assertFalse(audit.passed)
        self.assertEqual(audit.eligible_event_count, 7)
        self.assertEqual(audit.one_assignment_event_count, 2)
        self.assertTrue(audit.source_scan_exhausted)

    def test_non_chord_and_more_than_six_pitches_are_skipped(self):
        events = (
            _event(0, chord=False),
            _event(1, pitches=(40, 45, 50, 55, 60, 64, 67)),
        ) + tuple(_event(index + 2) for index in range(8))
        audit = audit_hc_capacity(events, generation_fn=lambda pitches, tuning: _generated(2))
        self.assertTrue(audit.passed)
        self.assertEqual(audit.skipped_non_chord_or_wide_event_count, 2)
        self.assertEqual(audit.checked_chord_event_count, 8)

    def test_duplicate_assignment_id_fails_closed(self):
        audit = audit_hc_capacity(
            (_event(0),),
            min_eligible_events=1,
            generation_fn=lambda pitches, tuning: _generated(2, duplicate=True),
        )
        self.assertFalse(audit.passed)
        self.assertTrue(audit.reason.startswith("S2A_HC_002_GENERATION_ERROR:"))
        self.assertFalse(audit.source_scan_exhausted)

    def test_ten_of_ten_repeatability(self):
        events = tuple(_event(index) for index in range(10))
        expected = audit_hc_capacity(events, generation_fn=lambda pitches, tuning: _generated(3))
        for _ in range(10):
            self.assertEqual(
                audit_hc_capacity(events, generation_fn=lambda pitches, tuning: _generated(3)),
                expected,
            )

    def test_hc_workflow_uploads_evidence_even_after_a_failed_audit_step(self):
        workflow = Path(".github/workflows/s2a_hc_capacity_audit.yml").read_text(encoding="utf-8")
        marker = "      - name: Upload H-C capacity audit evidence"
        self.assertIn(marker, workflow)
        upload_block = workflow.split(marker, 1)[1].split("\n      - ", 1)[0]
        self.assertIn("\n        if: always()", upload_block)
        self.assertIn("if-no-files-found: error", upload_block)


if __name__ == "__main__":
    unittest.main()
