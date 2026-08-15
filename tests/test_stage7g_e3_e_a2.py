from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from st_guitar_fingering_training.stage7g_e3_e_a2 import (
    PITCH_MODE,
    STANDARD_TUNING_MIDI,
    select_target_free_part_staff,
)


def _note(step: str, octave: int, *, staff: str | None = None, grace: bool = False) -> str:
    staff_xml = "" if staff is None else f"<staff>{staff}</staff>"
    grace_xml = "<grace/>" if grace else ""
    duration = "" if grace else "<duration>1</duration>"
    return (
        f"<note>{grace_xml}<pitch><step>{step}</step><octave>{octave}</octave></pitch>"
        f"{duration}<voice>1</voice>{staff_xml}</note>"
    )


def _part(part_id: str, notes: list[str]) -> str:
    return f'<part id="{part_id}"><measure number="1">{"".join(notes)}</measure></part>'


def _score(parts: list[str]) -> bytes:
    part_list = "".join(
        f'<score-part id="P{index}"><part-name>P{index}</part-name></score-part>'
        for index in range(1, len(parts) + 1)
    )
    return (
        '<score-partwise version="4.0">'
        f"<part-list>{part_list}</part-list>"
        + "".join(parts)
        + "</score-partwise>"
    ).encode("utf-8")


def _mxl(xml_bytes: bytes) -> bytes:
    container = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="score.musicxml" '
        'media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>'
    ).encode("utf-8")
    out = BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("score.musicxml", xml_bytes)
    return out.getvalue()


class Stage7GE3EA2SelectionTests(unittest.TestCase):
    def _write(self, xml_bytes: bytes) -> tuple[TemporaryDirectory, Path]:
        tmp = TemporaryDirectory()
        path = Path(tmp.name) / "source.mxl"
        path.write_bytes(_mxl(xml_bytes))
        return tmp, path

    def test_policy_constants_are_frozen_for_new_musetrainer_validation(self) -> None:
        self.assertEqual(STANDARD_TUNING_MIDI, (64, 59, 55, 50, 45, 40))
        self.assertEqual(PITCH_MODE, "sounding_exact")

    def test_selects_largest_part_then_largest_staff_without_targets(self) -> None:
        xml = _score(
            [
                _part("P1", [_note("C", 4, staff="1")]),
                _part(
                    "P2",
                    [
                        _note("C", 4, staff="2"),
                        _note("D", 4, staff="1"),
                        _note("E", 4, staff="1"),
                    ],
                ),
            ]
        )
        tmp, path = self._write(xml)
        self.addCleanup(tmp.cleanup)
        result = select_target_free_part_staff(path)
        self.assertEqual(result.part_id, "P2")
        self.assertEqual(result.staff_id, "1")
        self.assertEqual(result.selected_part_pitched_notes, 3)
        self.assertEqual(result.selected_staff_pitched_notes, 2)

    def test_ties_break_lexically_and_grace_notes_do_not_influence_choice(self) -> None:
        xml = _score(
            [
                _part("P2", [_note("C", 4, staff="2"), _note("D", 4, staff="1")]),
                _part(
                    "P1",
                    [
                        _note("E", 4, staff="2"),
                        _note("F", 4, staff="1"),
                        _note("G", 4, staff="9", grace=True),
                    ],
                ),
            ]
        )
        tmp, path = self._write(xml)
        self.addCleanup(tmp.cleanup)
        result = select_target_free_part_staff(path)
        self.assertEqual(result.part_id, "P1")
        self.assertEqual(result.staff_id, "1")
        self.assertEqual(result.selected_part_pitched_notes, 2)

    def test_unstaffed_selected_part_uses_none(self) -> None:
        xml = _score([_part("P1", [_note("C", 4), _note("E", 4)])])
        tmp, path = self._write(xml)
        self.addCleanup(tmp.cleanup)
        result = select_target_free_part_staff(path)
        self.assertEqual(result.part_id, "P1")
        self.assertIsNone(result.staff_id)
        self.assertEqual(result.selected_staff_pitched_notes, 2)

    def test_mixed_explicit_and_unstaffed_pitched_notes_fail_closed(self) -> None:
        xml = _score([_part("P1", [_note("C", 4, staff="1"), _note("E", 4)])])
        tmp, path = self._write(xml)
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "mixes explicit and missing staff ids"):
            select_target_free_part_staff(path)


if __name__ == "__main__":
    unittest.main()
