import unittest

from st_guitar_fingering_training.dataset import (
    build_voicing_candidate_rows,
    split_families,
    valid_chord_voicings,
    valid_single_note_candidates,
)
from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


class DatasetTests(unittest.TestCase):
    def test_standard_tuning_candidates_for_e4(self):
        candidates = valid_single_note_candidates(64, STANDARD_TUNING)
        self.assertIn((1, 0), candidates)
        self.assertIn((2, 5), candidates)
        self.assertIn((3, 9), candidates)
        self.assertIn((4, 14), candidates)
        self.assertIn((5, 19), candidates)
        self.assertIn((6, 24), candidates)

    def test_chord_candidates_include_observed_open_c_voicing(self):
        candidates = valid_chord_voicings((55, 60, 64), STANDARD_TUNING)
        observed = ((55, 3, 0), (60, 2, 1), (64, 1, 0))
        self.assertIn(observed, candidates)
        for candidate in candidates:
            strings = [string for _, string, _ in candidate]
            self.assertEqual(len(strings), len(set(strings)))

    def test_duplicate_pitch_voicings_are_deduplicated(self):
        candidates = valid_chord_voicings((64, 64), STANDARD_TUNING)
        # E4 is playable on all six strings (0,5,9,14,19,24), so two
        # identical E4 notes have C(6, 2)=15 distinct two-string voicings.
        self.assertEqual(len(candidates), 15)
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_voicing_rows_have_exactly_one_observed_candidate(self):
        placements = (
            Placement(sounding_midi=55, xml_midi=55, string=3, fret=0),
            Placement(sounding_midi=60, xml_midi=60, string=2, fret=1),
            Placement(sounding_midi=64, xml_midi=64, string=1, fret=0),
        )
        event = GuitarEvent(
            family_id="family",
            source_sha256="a" * 64,
            musicxml_version="2.0",
            software="test",
            pitch_mode="sounding_exact",
            tuning=STANDARD_TUNING,
            measure="1",
            onset=0,
            duration=4,
            voice="1",
            placements=placements,
        )
        source = ParsedSource(
            family_id="family",
            source_sha256="a" * 64,
            musicxml_version="2.0",
            software="test",
            pitch_mode="sounding_exact",
            tuning=STANDARD_TUNING,
            selected_staff="2",
            events=(event,),
        )
        rows = build_voicing_candidate_rows((source,))
        self.assertGreater(len(rows), 1)
        self.assertEqual(sum(row.observed for row in rows), 1)
        self.assertTrue(all(len(row.features) == 17 for row in rows))

    def test_split_keeps_multiple_sources_of_one_family_together(self):
        def src(family, digest):
            return ParsedSource(
                family_id=family,
                source_sha256=digest * 64,
                musicxml_version="2.0",
                software="x",
                pitch_mode="sounding_exact",
                tuning=STANDARD_TUNING,
                selected_staff=None,
                events=(),
            )

        sources = (src("same-work", "a"), src("same-work", "b"), src("other-work", "c"), src("third-work", "d"))
        train, val = split_families(sources, validation_count=1)
        self.assertFalse({s.family_id for s in train} & {s.family_id for s in val})
        same = [s for s in sources if s.family_id == "same-work"]
        self.assertTrue(all(s in train for s in same) or all(s in val for s in same))


if __name__ == "__main__":
    unittest.main()
