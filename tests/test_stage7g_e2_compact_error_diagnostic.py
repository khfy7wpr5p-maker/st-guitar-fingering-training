from __future__ import annotations

import unittest

from st_guitar_fingering_training.teacher_pairwise_diagnostic import (
    STAGE7G_E2_DELTA_NAMES,
    STAGE7G_E2_GEOMETRY_NAMES,
    TeacherPairwiseDiagnosticRow,
    stage7g_e2_diagnostic_report,
    stage7g_e2_fixed_strata,
    teacher_pairwise_geometry_delta,
)


class Stage7GE2DiagnosticTests(unittest.TestCase):
    def test_geometry_delta_is_compact_minus_open_and_target_blind(self):
        open_low = ((52, 6, 12), (55, 4, 5), (60, 3, 5))
        compact = ((52, 5, 7), (55, 4, 5), (60, 3, 5))
        delta = teacher_pairwise_geometry_delta(open_low, compact)
        self.assertEqual(len(delta), len(STAGE7G_E2_GEOMETRY_NAMES))
        self.assertEqual(len(delta), len(STAGE7G_E2_DELTA_NAMES))
        self.assertTrue(all(isinstance(value, float) for value in delta))

    def test_identical_proposals_are_rejected(self):
        voicing = ((52, 5, 7), (55, 4, 5))
        with self.assertRaises(ValueError):
            teacher_pairwise_geometry_delta(voicing, voicing)

    def test_fixed_strata_are_deterministic(self):
        row = TeacherPairwiseDiagnosticRow(
            family_id="family-a",
            event_id="event-a",
            chord_size=3,
            candidate_count=15,
            teacher_prefers_compact=1,
            oof_predicted_compact=0,
            geometry_delta=(0.0, 0.0, 1.0, -2.0, -1.0, -1.0, 0.0, 1.0, 0.0, 0.0, -1.0),
        )
        strata = stage7g_e2_fixed_strata(row)
        self.assertEqual(strata["chord_size"], "3")
        self.assertEqual(strata["candidate_count"], "13_16")
        self.assertEqual(strata["mean_positive_fret_delta"], "negative")
        self.assertEqual(strata["positive_fret_span_delta"], "negative")
        self.assertEqual(strata["same_fret_barre_proxy_delta"], "positive")
        self.assertEqual(strata["internal_string_gaps_delta"], "negative")

    def test_report_is_aggregate_only_and_does_not_fit_model(self):
        rows = (
            TeacherPairwiseDiagnosticRow("family-a", "event-a", 3, 10, 0, 0, (0.0,) * 11),
            TeacherPairwiseDiagnosticRow("family-a", "event-b", 3, 10, 1, 0, (1.0,) * 11),
            TeacherPairwiseDiagnosticRow("family-b", "event-c", 4, 18, 0, 1, (-1.0,) * 11),
            TeacherPairwiseDiagnosticRow("family-b", "event-d", 4, 18, 1, 1, (0.0,) * 11),
        )
        report = stage7g_e2_diagnostic_report(rows)
        self.assertEqual(report["event_count"], 4)
        self.assertEqual(report["family_count"], 2)
        self.assertEqual(report["confusion"]["compact_false_negative"], 1)
        self.assertEqual(report["confusion"]["compact_false_positive"], 1)
        self.assertFalse(report["model_fit_performed"])
        self.assertFalse(report["hyperparameter_search"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])
        self.assertNotIn("event-a", str(report))
        self.assertNotIn("event-b", str(report))

    def test_duplicate_event_ids_fail_closed(self):
        rows = (
            TeacherPairwiseDiagnosticRow("family-a", "same", 3, 10, 0, 0, (0.0,) * 11),
            TeacherPairwiseDiagnosticRow("family-b", "same", 3, 10, 1, 1, (0.0,) * 11),
        )
        with self.assertRaises(ValueError):
            stage7g_e2_diagnostic_report(rows)


if __name__ == "__main__":
    unittest.main()
