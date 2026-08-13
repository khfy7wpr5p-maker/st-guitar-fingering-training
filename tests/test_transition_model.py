import unittest

import numpy as np

from st_guitar_fingering_training.dataset import VoicingCandidateRow
from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement
from st_guitar_fingering_training.transition_model import (
    _group_log_probabilities,
    _rank_combined_rows,
    build_transition_training_rows,
)


TUNING = (64, 59, 55, 50, 45, 40)


class _FeatureScoreModel:
    def decision_function(self, X):
        X = np.asarray(X, dtype=float)
        return X[:, 0]


class TransitionModelTests(unittest.TestCase):
    def _source(self):
        events = (
            GuitarEvent(
                family_id="fam_transition",
                source_sha256="b" * 64,
                musicxml_version="2.0",
                software="test",
                pitch_mode="sounding_exact",
                tuning=TUNING,
                measure="1",
                onset=0,
                duration=4,
                voice="1",
                placements=(Placement(60, 60, 2, 1), Placement(64, 64, 1, 0)),
            ),
            GuitarEvent(
                family_id="fam_transition",
                source_sha256="b" * 64,
                musicxml_version="2.0",
                software="test",
                pitch_mode="sounding_exact",
                tuning=TUNING,
                measure="2",
                onset=0,
                duration=4,
                voice="1",
                placements=(Placement(64, 64, 2, 5), Placement(67, 67, 1, 3)),
            ),
        )
        return ParsedSource("fam_transition", "b" * 64, "2.0", "test", "sounding_exact", TUNING, "2", events)

    def test_transition_training_skips_first_chord_and_has_one_positive(self):
        rows = build_transition_training_rows((self._source(),))
        self.assertTrue(rows)
        event_ids = {row.event_id for row in rows}
        self.assertEqual(len(event_ids), 1)
        self.assertTrue(all(event_id.endswith(":transition") for event_id in event_ids))
        self.assertEqual(sum(row.observed for row in rows), 1)
        self.assertTrue(all(len(row.features) == 10 for row in rows))

    def test_group_log_probabilities_are_normalized(self):
        rows = (
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 2, 1), (64, 1, 0)), 1, (2.0,)),
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 3, 5), (64, 2, 5)), 0, (1.0,)),
        )
        logp = _group_log_probabilities(_FeatureScoreModel(), rows)
        self.assertAlmostEqual(float(np.exp(logp).sum()), 1.0, places=12)
        self.assertGreater(logp[0], logp[1])

    def test_zero_transition_weight_preserves_unary_ranking(self):
        sequence_rows = (
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 2, 1), (64, 1, 0)), 1, (2.0,)),
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 3, 5), (64, 2, 5)), 0, (1.0,)),
        )
        transition_rows = (
            VoicingCandidateRow("fam", "e:t", (60, 64), sequence_rows[0].placements, 1, (-10.0,)),
            VoicingCandidateRow("fam", "e:t", (60, 64), sequence_rows[1].placements, 0, (10.0,)),
        )
        ranked = _rank_combined_rows(
            _FeatureScoreModel(),
            _FeatureScoreModel(),
            sequence_rows,
            transition_rows,
            0.0,
        )
        self.assertEqual(ranked[0].placements, sequence_rows[0].placements)

    def test_transition_weight_is_bounded(self):
        rows = (
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 2, 1), (64, 1, 0)), 1, (1.0,)),
            VoicingCandidateRow("fam", "e", (60, 64), ((60, 3, 5), (64, 2, 5)), 0, (0.0,)),
        )
        with self.assertRaises(ValueError):
            _rank_combined_rows(_FeatureScoreModel(), _FeatureScoreModel(), rows, rows, 1.01)


if __name__ == "__main__":
    unittest.main()
