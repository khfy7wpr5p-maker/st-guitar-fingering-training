import unittest

from st_guitar_fingering_training.context import context_feature_vector
from st_guitar_fingering_training.intake import GuitarEvent, Placement
from st_guitar_fingering_training.sequence_context import lookahead_feature_vector, sequence_feature_vector


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def event(placements):
    return GuitarEvent(
        family_id="fam",
        source_sha256="a" * 64,
        musicxml_version="4.0",
        software="test",
        pitch_mode="sounding_exact",
        tuning=STANDARD_TUNING,
        measure="1",
        onset=0,
        duration=1,
        voice="1",
        placements=tuple(placements),
    )


class SequenceContextTests(unittest.TestCase):
    def test_lookahead_does_not_depend_on_future_observed_string_fret(self):
        current = ((55, 3, 0), (60, 2, 1))
        next_a = event((
            Placement(60, 60, 2, 1),
            Placement(64, 64, 1, 0),
        ))
        next_b = event((
            Placement(60, 60, 3, 5),
            Placement(64, 64, 2, 5),
        ))
        self.assertEqual(
            lookahead_feature_vector(current, next_a),
            lookahead_feature_vector(current, next_b),
        )

    def test_terminal_event_has_zero_lookahead_block(self):
        current = ((55, 3, 0), (60, 2, 1))
        features = lookahead_feature_vector(current, None)
        self.assertEqual(len(features), 14)
        self.assertEqual(features, (0.0,) * 14)

    def test_sequence_features_extend_stage6d_without_replacing_it(self):
        current = ((55, 3, 0), (60, 2, 1))
        previous = ((52, 4, 2), (57, 3, 2))
        next_event = event((
            Placement(60, 60, 2, 1),
            Placement(64, 64, 1, 0),
        ))
        stage6d = context_feature_vector(current, previous)
        stage6e = sequence_feature_vector(current, previous, next_event)
        self.assertEqual(stage6e[:len(stage6d)], stage6d)
        self.assertEqual(len(stage6e), len(stage6d) + 14)


if __name__ == "__main__":
    unittest.main()
