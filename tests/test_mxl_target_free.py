from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from st_guitar_fingering_training.mxl_target_free import (
    inspect_target_free_mxl,
    parse_target_free_mxl,
    read_mxl_musicxml_bytes,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _score(*, two_staffs: bool = False, technical: bool = False) -> bytes:
    staff1 = "<staff>1</staff>" if two_staffs else ""
    staff2 = "<staff>2</staff>" if two_staffs else ""
    tech = (
        "<notations><technical><string>2</string><fret>1</fret></technical></notations>"
        if technical
        else ""
    )
    return (
        '<score-partwise version="4.0">'
        '<identification><encoding><software>mxl-test</software></encoding></identification>'
        '<part-list><score-part id="P1"><part-name>Score</part-name></score-part></part-list>'
        '<part id="P1"><measure number="1">'
        f'<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice>{staff1}{tech}</note>'
        f'<note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice>{staff1}</note>'
        f'<note><chord/><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice>{staff1}</note>'
        + (
            f'<note><pitch><step>A</step><octave>3</octave></pitch><duration>1</duration><voice>2</voice>{staff2}</note>'
            if two_staffs
            else ""
        )
        + '</measure></part></score-partwise>'
    ).encode("utf-8")


def _mxl(
    xml_bytes: bytes,
    *,
    root_path: str = "score.musicxml",
    root_paths: tuple[str, ...] | None = None,
    extra_members: tuple[tuple[str, bytes], ...] = (),
) -> bytes:
    declared = root_paths if root_paths is not None else (root_path,)
    rootfiles = "".join(
        f'<rootfile full-path="{path}" media-type="application/vnd.recordare.musicxml+xml"/>'
        for path in declared
    )
    container = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        f'<rootfiles>{rootfiles}</rootfiles></container>'
    ).encode("utf-8")
    out = BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", container)
        archive.writestr(root_path, xml_bytes)
        for name, payload in extra_members:
            archive.writestr(name, payload)
    return out.getvalue()


class MxlTargetFreeTests(unittest.TestCase):
    def _write(self, payload: bytes) -> tuple[TemporaryDirectory, Path]:
        tmp = TemporaryDirectory()
        path = Path(tmp.name) / "source.mxl"
        path.write_bytes(payload)
        return tmp, path

    def test_safe_mxl_parses_through_target_free_contract_and_keeps_outer_hash(self) -> None:
        payload = _mxl(_score())
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)

        outer, inner, root_path = read_mxl_musicxml_bytes(path)
        self.assertEqual(outer, payload)
        self.assertEqual(inner, _score())
        self.assertEqual(root_path, "score.musicxml")

        source = parse_target_free_mxl(
            path,
            family_id="e3e_family_001",
            tuning=STANDARD_TUNING,
            pitch_mode="sounding_exact",
        )
        expected_sha = sha256(payload).hexdigest()
        self.assertEqual(source.source_sha256, expected_sha)
        self.assertTrue(source.events)
        self.assertTrue(all(event.source_sha256 == expected_sha for event in source.events))
        self.assertFalse(hasattr(source.events[0], "placements"))

    def test_structure_audit_reports_parts_staffs_and_only_counts_technical_metadata(self) -> None:
        payload = _mxl(_score(two_staffs=True, technical=True))
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)

        audit = inspect_target_free_mxl(path)
        self.assertEqual(audit.part_ids, ("P1",))
        self.assertEqual(audit.staff_ids_by_part, (("P1", ("1", "2")),))
        self.assertEqual(audit.pitched_notes_by_part, (("P1", 4),))
        self.assertEqual(audit.technical_string_or_fret_elements, 2)
        self.assertEqual(audit.software, "mxl-test")

    def test_container_path_traversal_is_rejected(self) -> None:
        payload = _mxl(_score(), root_path="../score.musicxml")
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "traversal"):
            read_mxl_musicxml_bytes(path)

    def test_multiple_rootfiles_are_rejected(self) -> None:
        payload = _mxl(_score(), root_paths=("score.musicxml", "other.musicxml"))
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "exactly one rootfile"):
            read_mxl_musicxml_bytes(path)

    def test_duplicate_member_names_are_rejected(self) -> None:
        payload = _mxl(_score(), extra_members=(("score.musicxml", _score()),))
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "duplicate normalized"):
            read_mxl_musicxml_bytes(path)

    def test_high_compression_ratio_extra_member_is_rejected_before_parse(self) -> None:
        payload = _mxl(_score(), extra_members=(("padding.bin", b"0" * 1024 * 1024),))
        tmp, path = self._write(payload)
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "compression ratio"):
            read_mxl_musicxml_bytes(path)


if __name__ == "__main__":
    unittest.main()
