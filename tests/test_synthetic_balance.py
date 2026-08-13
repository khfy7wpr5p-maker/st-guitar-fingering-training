import unittest

from st_guitar_fingering_training.synthetic import generate_synthetic_family
from st_guitar_fingering_training.synthetic_balanced import balanced_family_indices
from st_guitar_fingering_training.synthetic_behavior import _feature_vector, deterministic_style_folds


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


if __name__ == "__main__":
    unittest.main()
