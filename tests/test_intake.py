from pathlib import Path
import tempfile
import unittest

from st_guitar_fingering_training.intake import parse_guitar_musicxml

FIXTURE = '''<?xml version="1.0"?>
<score-partwise version="2.0"><identification><encoding><software>fixture</software></encoding></identification>
<part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes>
<clef><sign>TAB</sign><line>5</line></clef><staff-details><staff-lines>6</staff-lines>
<staff-tuning line="1"><tuning-step>E</tuning-step><tuning-octave>2</tuning-octave></staff-tuning>
<staff-tuning line="2"><tuning-step>A</tuning-step><tuning-octave>2</tuning-octave></staff-tuning>
<staff-tuning line="3"><tuning-step>D</tuning-step><tuning-octave>3</tuning-octave></staff-tuning>
<staff-tuning line="4"><tuning-step>G</tuning-step><tuning-octave>3</tuning-octave></staff-tuning>
<staff-tuning line="5"><tuning-step>B</tuning-step><tuning-octave>3</tuning-octave></staff-tuning>
<staff-tuning line="6"><tuning-step>E</tuning-step><tuning-octave>4</tuning-octave></staff-tuning></staff-details></attributes>
<note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><notations><technical><string>1</string><fret>3</fret></technical></notations></note>
</measure></part></score-partwise>'''


class IntakeTests(unittest.TestCase):
    def test_exact_physical_pitch(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.xml"
            p.write_text(FIXTURE)
            src = parse_guitar_musicxml(p)
            self.assertEqual(src.pitch_mode, "sounding_exact")
            self.assertEqual(src.events[0].placements[0].sounding_midi, 67)
            self.assertEqual((src.events[0].placements[0].string, src.events[0].placements[0].fret), (1, 3))

    def test_unresolved_pitch_relation_fails(self):
        bad = FIXTURE.replace('<step>G</step><octave>4</octave>', '<step>A</step><octave>4</octave>')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.xml"
            p.write_text(bad)
            with self.assertRaises(ValueError):
                parse_guitar_musicxml(p)

    def test_identical_same_string_duplicate_collapses(self):
        dup = FIXTURE.replace(
            '</measure>',
            '<note><chord/><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><notations><technical><string>1</string><fret>3</fret></technical></notations></note></measure>'
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.xml"
            p.write_text(dup)
            src = parse_guitar_musicxml(p)
            self.assertEqual(len(src.events), 1)
            self.assertEqual(len(src.events[0].placements), 1)


if __name__ == "__main__":
    unittest.main()
