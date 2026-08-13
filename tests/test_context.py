import unittest

from st_guitar_fingering_training.context import build_context_training_rows, transition_feature_vector
from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement


TUNING = (64, 59, 55, 50, 45, 40)


class ContextTests(unittest.TestCase):
    def _source(self):
        events = (
            GuitarEvent(
                family_id="fam_ctx",
                source_sha256="a" * 64,
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
                family_id="fam_ctx",
                source_sha256="a" * 64,
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
        return ParsedSource("fam_ctx", "a" * 64, "2.0", "test", "sounding_exact", TUNING, "2", events)

    def test_transition_features_encode_missing_previous_explicitly(self):
        candidate = ((60, 2, 1), (64, 1, 0))
        self.assertEqual(transition_feature_vector(candidate, None), (0.0,) * 10)

    def test_context_training_rows_add_previous_event_features_only_after_first_chord(self):
        rows = build_context_training_rows((self._source(),))
        by_event = {}
        for row in rows:
            by_event.setdefault(row.event_id, []).append(row)
        self.assertEqual(len(by_event), 2)
        groups = list(by_event.values())
        self.assertTrue(all(len(row.features) == 27 for row in rows))
        self.assertTrue(all(row.features[-10:] == (0.0,) * 10 for row in groups[0]))
        self.assertTrue(all(row.features[-10] == 1.0 for row in groups[1]))
        self.assertTrue(all(sum(row.observed for row in group) == 1 for group in groups))


if __name__ == "__main__":
    unittest.main()
