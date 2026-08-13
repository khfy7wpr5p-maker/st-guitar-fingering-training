import unittest

import numpy as np

from st_guitar_fingering_training.normalized_path_optimizer import _normalize_positive_scores


class NormalizedPathOptimizerTests(unittest.TestCase):
    def test_group_normalization_sums_to_one(self):
        scores = _normalize_positive_scores([0.2, 0.3, 0.5])
        self.assertAlmostEqual(float(np.exp(scores).sum()), 1.0)

    def test_group_normalization_is_invariant_to_common_scale(self):
        a = _normalize_positive_scores([0.2, 0.8])
        b = _normalize_positive_scores([2.0, 8.0])
        np.testing.assert_allclose(a, b)

    def test_group_normalization_rejects_nonfinite_or_negative_scores(self):
        with self.assertRaises(ValueError):
            _normalize_positive_scores([0.2, float("nan")])
        with self.assertRaises(ValueError):
            _normalize_positive_scores([0.2, -0.1])


if __name__ == "__main__":
    unittest.main()
