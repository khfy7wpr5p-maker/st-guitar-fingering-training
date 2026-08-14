import unittest

import numpy as np

from st_guitar_fingering_training.synthetic import generate_synthetic_family
from st_guitar_fingering_training.synthetic_balanced import balanced_family_indices
from st_guitar_fingering_training.synthetic_behavior import BehaviorRow, _feature_vector, deterministic_style_folds
from st_guitar_fingering_training.synthetic_pairwise import (
    build_pairwise_training_matrix,
    evaluate_pairwise_behavior_ranker,
    pairwise_coefficient_report,
    train_pairwise_behavior_ranker,
)


class SyntheticBalanceTests(unittest.TestCase):
    def test_default_100_is_balanced_20_by_5(self):
        indices = balanced_family_indices(100)
        families = [generate_synthetic_family(index, events_per_family=4) for index in indices]
        styles = {}
        progressions = {}
        for family in families:
            styles[family.style] = styles.get(family.style, 0) + 1
            key = tuple(family.progression)
            progressions[key] = progressions.get(key, 0) + 1
        self.assertEqual(sorted(styles.values()), [20] * 5)
        self.assertEqual(sorted(progressions.values()), [20] * 5)
        self.assertEqual(len(set(indices)), 100)

    def test_invalid_balance_size_fails_closed(self):
        with self.assertRaises(ValueError):
            balanced_family_indices(99)

    def test_behavior_folds_are_family_isolated(self):
        family_ids = [f"family_{index:02d}" for index in range(20)]
        folds = deterministic_style_folds(family_ids, folds=5)
        self.assertEqual([len(fold) for fold in folds], [4] * 5)
        flattened = [family_id for fold in folds for family_id in fold]
        self.assertEqual(set(flattened), set(family_ids))
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_only_common_tone_requires_previous_voicing(self):
        previous = ((60, 2, 1), (64, 3, 2), (67, 4, 3))
        current = ((60, 2, 1), (65, 3, 3), (67, 4, 3))
        self.assertEqual(len(_feature_vector("open_low", current, None)), 4)
        with self.assertRaises(ValueError):
            _feature_vector("common_tone", current, None)
        features = _feature_vector("common_tone", current, previous)
        self.assertAlmostEqual(features[0], 2 / 3)
        self.assertAlmostEqual(features[2], 1.0)

    def test_pairwise_training_matrix_is_exactly_symmetric(self):
        rows = (
            BehaviorRow("family_a", "event_a", 1, (0.1, 0.2, 0.3, 0.4)),
            BehaviorRow("family_a", "event_a", 0, (0.5, 0.2, 0.3, 0.4)),
            BehaviorRow("family_a", "event_a", 0, (0.8, 0.2, 0.3, 0.4)),
        )
        X, y = build_pairwise_training_matrix(rows)
        self.assertEqual(X.shape, (4, 4))
        self.assertEqual(y.tolist(), [1, 0, 1, 0])
        np.testing.assert_allclose(X[0], -X[1])
        np.testing.assert_allclose(X[2], -X[3])

    def test_pairwise_compact_fixture_ranks_preferred_and_learns_span_direction(self):
        rows = (
            BehaviorRow("family_a", "event_a", 1, (0.10, 0.30, 0.40, 0.0)),
            BehaviorRow("family_a", "event_a", 0, (0.50, 0.30, 0.40, 0.0)),
            BehaviorRow("family_a", "event_a", 0, (0.80, 0.30, 0.40, 0.0)),
            BehaviorRow("family_b", "event_b", 1, (0.20, 0.50, 0.60, 0.0)),
            BehaviorRow("family_b", "event_b", 0, (0.70, 0.50, 0.60, 0.0)),
            BehaviorRow("family_b", "event_b", 0, (0.90, 0.50, 0.60, 0.0)),
        )
        model = train_pairwise_behavior_ranker(rows)
        metrics = evaluate_pairwise_behavior_ranker(model, rows)
        report = pairwise_coefficient_report(model, "compact")
        self.assertEqual(metrics.events, 2)
        self.assertEqual(metrics.top1_accuracy, 1.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 1.0)
        self.assertLess(report["coefficients"]["fret_span"], 0.0)
        self.assertTrue(report["focus_direction_match"])
        self.assertEqual(report["feature_space"], "standardized_pairwise_differences")


if __name__ == "__main__":
    unittest.main()
