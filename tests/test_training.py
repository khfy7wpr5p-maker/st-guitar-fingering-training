import unittest

import numpy as np

from st_guitar_fingering_training.dataset import VoicingCandidateRow
from st_guitar_fingering_training.training import (
    deterministic_family_folds,
    evaluate_low_total_fret_voicing_baseline,
    evaluate_ranker,
    filter_ambiguous_ranking_rows,
)


class _FakeModel:
    def predict_proba(self, X):
        scores = X[:, 0]
        return np.column_stack((1.0 - scores, scores))


class TrainingTests(unittest.TestCase):
    def _row(self, event_id, placements, observed, score):
        pitches = tuple(p for p, _, _ in placements)
        return VoicingCandidateRow(
            family_id="fam",
            event_id=event_id,
            pitches_midi=pitches,
            placements=tuple(placements),
            observed=observed,
            features=(score,) + (0.0,) * 16,
        )

    def test_learned_ranker_accepts_voicing_rows(self):
        rows = (
            self._row("e1", ((60, 2, 1), (64, 1, 0)), 1, 0.9),
            self._row("e1", ((60, 3, 5), (64, 2, 5)), 0, 0.1),
            self._row("e2", ((55, 3, 0), (60, 2, 1)), 0, 0.2),
            self._row("e2", ((55, 4, 5), (60, 3, 5)), 1, 0.8),
        )
        metrics = evaluate_ranker(_FakeModel(), rows)
        self.assertEqual(metrics.events, 2)
        self.assertEqual(metrics.top1_accuracy, 1.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 1.0)

    def test_low_total_fret_baseline_is_deterministic(self):
        rows = (
            self._row("e1", ((60, 2, 1), (64, 1, 0)), 1, 0.0),
            self._row("e1", ((60, 3, 5), (64, 2, 5)), 0, 0.0),
        )
        metrics = evaluate_low_total_fret_voicing_baseline(rows)
        self.assertEqual(metrics.events, 1)
        self.assertEqual(metrics.top1_accuracy, 1.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 1.0)

    def test_filter_ambiguous_ranking_rows_excludes_trivial_events(self):
        rows = (
            self._row("single", ((60, 2, 1), (64, 1, 0)), 1, 0.9),
            self._row("ambiguous", ((60, 2, 1), (64, 1, 0)), 1, 0.9),
            self._row("ambiguous", ((60, 3, 5), (64, 2, 5)), 0, 0.1),
        )
        filtered = filter_ambiguous_ranking_rows(rows)
        self.assertEqual({row.event_id for row in filtered}, {"ambiguous"})
        self.assertEqual(len(filtered), 2)

    def test_deterministic_family_folds_are_stable_balanced_and_exhaustive(self):
        families = [f"fam-{index}" for index in range(25)]
        first = deterministic_family_folds(families, folds=5)
        second = deterministic_family_folds(reversed(families), folds=5)
        self.assertEqual(first, second)
        self.assertEqual([len(fold) for fold in first], [5, 5, 5, 5, 5])
        flattened = [family for fold in first for family in fold]
        self.assertEqual(set(flattened), set(families))
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_deterministic_family_folds_reject_invalid_fold_count(self):
        with self.assertRaises(ValueError):
            deterministic_family_folds(["a", "b"], folds=1)
        with self.assertRaises(ValueError):
            deterministic_family_folds(["a", "b"], folds=3)


if __name__ == "__main__":
    unittest.main()
