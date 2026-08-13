import unittest

from st_guitar_fingering_training.dataset import valid_single_note_candidates, split_families
from st_guitar_fingering_training.intake import ParsedSource


class DatasetTests(unittest.TestCase):
    def test_standard_tuning_candidates_for_e4(self):
        tuning = (64, 59, 55, 50, 45, 40)
        candidates = valid_single_note_candidates(64, tuning)
        self.assertIn((1, 0), candidates)
        self.assertIn((2, 5), candidates)
        self.assertIn((3, 9), candidates)
        self.assertIn((4, 14), candidates)
        self.assertIn((5, 19), candidates)
        self.assertIn((6, 24), candidates)

    def test_split_keeps_multiple_sources_of_one_family_together(self):
        def src(family, digest):
            return ParsedSource(
                family_id=family,
                source_sha256=digest * 64,
                musicxml_version="2.0",
                software="x",
                pitch_mode="sounding_exact",
                tuning=(64, 59, 55, 50, 45, 40),
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
