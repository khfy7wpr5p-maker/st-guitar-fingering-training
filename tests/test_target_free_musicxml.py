from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml
from st_guitar_fingering_training.teacher_gold import STATELESS_SPECIALISTS
from st_guitar_fingering_training.teacher_task_sampling import build_annotation_sampling_pool


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _score(*, pitches=(60, 64, 67), include_technical=False, two_parts=False) -> str:
    def note_xml(pitch: int, chord: bool, string: int) -> str:
        names = {0: ("C", 0), 4: ("E", 0), 7: ("G", 0)}
        pc = pitch % 12
        step, alter = names[pc]
        octave = pitch // 12 - 1
        technical = (
            f"<notations><technical><string>{string}</string><fret>7</fret></technical></notations>"
            if include_technical
            else ""
        )
        return (
            "<note>"
            + ("<chord/>" if chord else "")
            + f"<pitch><step>{step}</step>{'<alter>'+str(alter)+'</alter>' if alter else ''}<octave>{octave}</octave></pitch>"
            + "<duration>1</duration><voice>1</voice>"
            + technical
            + "</note>"
        )

    notes = "".join(note_xml(pitch, index > 0, index + 1) for index, pitch in enumerate(pitches))
    parts = f'<part id="P1"><measure number="1">{notes}</measure></part>'
    part_list = '<score-part id="P1"><part-name>Guitar</part-name></score-part>'
    if two_parts:
        parts += f'<part id="P2"><measure number="1">{notes}</measure></part>'
        part_list += '<score-part id="P2"><part-name>Other</part-name></score-part>'
    return (
        '<score-partwise version="4.0">'
        '<identification><encoding><software>target-free-test</software></encoding></identification>'
        f'<part-list>{part_list}</part-list>{parts}'
        '</score-partwise>'
    )


class _FakeSpecialist:
    def __init__(self, reverse: bool = False) -> None:
        self.reverse = reverse

    def decision_function(self, features):
        values = np.arange(len(features), dtype=np.float64)
        return -values if self.reverse else values


class TargetFreeMusicXMLTests(unittest.TestCase):
    def _parse(self, xml: str, *, pitch_mode: str = "sounding_exact", part_id: str | None = None):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.musicxml"
            path.write_text(xml, encoding="utf-8")
            return parse_target_free_musicxml(
                path,
                family_id="family_001",
                tuning=STANDARD_TUNING,
                pitch_mode=pitch_mode,
                part_id=part_id,
            )

    def test_normal_musicxml_without_tab_becomes_physical_candidate_task(self) -> None:
        source = self._parse(_score())
        self.assertEqual(source.pitch_mode, "sounding_exact")
        self.assertEqual(len(source.events), 1)
        event = source.events[0]
        self.assertEqual(event.pitches_midi, (60, 64, 67))
        self.assertTrue(event.is_chord)
        self.assertFalse(hasattr(event, "placements"))

        models = {
            style: _FakeSpecialist(reverse=(style == "compact"))
            for style in STATELESS_SPECIALISTS
        }
        pool = build_annotation_sampling_pool(
            (source,),
            source_origins={source.source_sha256: "stage7g://target-free/family_001"},
            specialist_models=models,
        )
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool[0].task.pitches_midi, (60, 64, 67))
        self.assertEqual(pool[0].task.candidates, valid_chord_voicings((60, 64, 67), STANDARD_TUNING))

    def test_written_octave_plus_12_is_explicitly_converted_to_sounding_pitch(self) -> None:
        source = self._parse(_score(pitches=(72, 76, 79)), pitch_mode="written_octave_plus_12")
        self.assertEqual(source.events[0].pitches_midi, (60, 64, 67))

    def test_pitch_mode_must_be_explicit_and_supported(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.musicxml"
            path.write_text(_score(), encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_target_free_musicxml(
                    path,
                    family_id="family_001",
                    tuning=STANDARD_TUNING,
                    pitch_mode="auto",
                )

    def test_multiple_parts_require_explicit_part_selection(self) -> None:
        with self.assertRaises(ValueError):
            self._parse(_score(two_parts=True))
        selected = self._parse(_score(two_parts=True), part_id="P1")
        self.assertEqual(selected.part_id, "P1")

    def test_technical_string_fret_metadata_does_not_change_pitch_events(self) -> None:
        plain = self._parse(_score(include_technical=False))
        contaminated = self._parse(_score(include_technical=True))
        self.assertEqual(
            [(event.measure, event.onset, event.voice, event.pitches_midi) for event in plain.events],
            [(event.measure, event.onset, event.voice, event.pitches_midi) for event in contaminated.events],
        )
        self.assertNotEqual(plain.source_sha256, contaminated.source_sha256)


if __name__ == "__main__":
    unittest.main()
