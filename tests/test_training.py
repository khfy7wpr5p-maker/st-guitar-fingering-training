import unittest

import numpy as np

from st_guitar_fingering_training.dataset import VoicingCandidateRow
from st_guitar_fingering_training.training import (
    evaluate_low_total_fret_voicing_baseline,
    evaluate_ranker,
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


if __name__ == "__main__":
    unittest.main()
