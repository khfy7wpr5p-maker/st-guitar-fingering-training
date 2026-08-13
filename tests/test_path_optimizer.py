import unittest

import numpy as np

from st_guitar_fingering_training.path_optimizer import _viterbi_indices


class PathOptimizerTests(unittest.TestCase):
    def test_viterbi_prefers_global_path_over_greedy_first_state(self):
        initial = [0.0, -0.1]
        transitions = [np.asarray([[0.0, 0.0], [2.0, 0.0]])]
        self.assertEqual(_viterbi_indices(initial, transitions), (1, 0))

    def test_viterbi_ties_are_deterministic(self):
        initial = [0.0, 0.0]
        transitions = [np.zeros((2, 2), dtype=float)]
        self.assertEqual(_viterbi_indices(initial, transitions), (0, 0))

    def test_viterbi_rejects_transition_shape_mismatch(self):
        with self.assertRaises(ValueError):
            _viterbi_indices([0.0, 0.0], [np.zeros((3, 2), dtype=float)])


if __name__ == "__main__":
    unittest.main()
