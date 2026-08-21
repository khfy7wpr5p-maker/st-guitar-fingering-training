from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from st_guitar_fingering_training.guitarset_observed_gold import (
    GS001_UNSAFE_ARCHIVE,
    GS102_BAD_DATA_SOURCE,
    GS106_NEGATIVE_FRET,
    STRUM_CLUSTER_WINDOW_SECONDS,
    build_manifest,
    derive_strum_voicings,
    extract_comp_jams,
    import_guitarset_comp_archive,
    sanitize_note_row,
)


def _jams(rows_by_source: dict[int, list[dict]]) -> bytes:
    annotations = []
    for source in sorted(rows_by_source):
        annotations.append({
            "namespace": "note_midi",
            "annotation_metadata": {"data_source": str(source)},
            "data": rows_by_source[source],
        })
    return json.dumps({"annotations": annotations}).encode("utf-8")


def _empty_six_sources() -> dict[int, list[dict]]:
    return {index: [] for index in range(6)}


class GuitarSetObservedGoldTests(unittest.TestCase):
    def test_data_source_maps_low_to_high_strings_and_physical_fret(self):
        rows = _empty_six_sources()
        rows[0] = [{"time": 0.0, "duration": 0.5, "value": 42.02}]
        rows[5] = [{"time": 0.1, "duration": 0.5, "value": 64.01}]
        notes, rejected = extract_comp_jams("annotation/00_Test-100-C_comp.jams", _jams(rows))
        self.assertEqual(rejected, ())
        by_source = {item.data_source: item for item in notes}
        self.assertEqual((by_source[0].string, by_source[0].fret, by_source[0].midi), (6, 2, 42))
        self.assertEqual((by_source[5].string, by_source[5].fret, by_source[5].midi), (1, 0, 64))

    def test_negative_fret_is_quarantined_not_coerced(self):
        result = sanitize_note_row(
            source_member="annotation/00_Test-100-C_comp.jams",
            data_source=2,
            source_note_index=0,
            row={"time": 1.0, "duration": 0.2, "value": 49.1},
        )
        self.assertEqual(result.reason_code, GS106_NEGATIVE_FRET)

    def test_missing_data_source_fails_closed(self):
        rows = _empty_six_sources()
        del rows[4]
        with self.assertRaisesRegex(ValueError, GS102_BAD_DATA_SOURCE):
            extract_comp_jams("annotation/00_Test-100-C_comp.jams", _jams(rows))

    def test_strum_cluster_preserves_exact_string_fret_geometry(self):
        rows = _empty_six_sources()
        # Low E open, A2, D2, G open within 30 ms: an observed E-minor geometry.
        rows[0] = [{"time": 1.000, "duration": 0.5, "value": 40.02}]
        rows[1] = [{"time": 1.010, "duration": 0.5, "value": 47.01}]
        rows[2] = [{"time": 1.020, "duration": 0.5, "value": 52.02}]
        rows[3] = [{"time": 1.030, "duration": 0.5, "value": 55.00}]
        notes, rejected = extract_comp_jams("annotation/00_Test-100-E_comp.jams", _jams(rows))
        self.assertEqual(rejected, ())
        voicings = derive_strum_voicings(notes)
        self.assertEqual(len(voicings), 1)
        self.assertLessEqual(voicings[0].onset_spread_seconds, STRUM_CLUSTER_WINDOW_SECONDS)
        self.assertEqual(
            voicings[0].placements,
            ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0)),
        )

    def test_same_string_ambiguity_is_not_promoted_to_voicing_gold(self):
        rows = _empty_six_sources()
        rows[0] = [
            {"time": 1.000, "duration": 0.1, "value": 40.0},
            {"time": 1.020, "duration": 0.1, "value": 42.0},
        ]
        rows[1] = [{"time": 1.010, "duration": 0.1, "value": 47.0}]
        notes, _ = extract_comp_jams("annotation/00_Test-100-E_comp.jams", _jams(rows))
        self.assertEqual(derive_strum_voicings(notes), ())

    def test_archive_rejects_duplicate_member_names(self):
        rows = _empty_six_sources()
        payload = _jams(rows)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("annotation/00_Test-100-E_comp.jams", payload)
                    archive.writestr("annotation/00_Test-100-E_comp.jams", payload)
            with self.assertRaisesRegex(ValueError, GS001_UNSAFE_ARCHIVE):
                import_guitarset_comp_archive(path)

    def test_archive_rejects_path_traversal_comp_member(self):
        rows = _empty_six_sources()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traversal.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("annotation/../evil_comp.jams", _jams(rows))
            with self.assertRaisesRegex(ValueError, GS001_UNSAFE_ARCHIVE):
                import_guitarset_comp_archive(path)

    def test_archive_uses_comp_only_and_is_deterministic(self):
        rows = _empty_six_sources()
        rows[0] = [{"time": 0.0, "duration": 0.5, "value": 40.0}]
        rows[1] = [{"time": 0.01, "duration": 0.5, "value": 47.0}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guitarset.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("annotation/00_Test-100-E_comp.jams", _jams(rows))
                archive.writestr("annotation/00_Test-100-E_solo.jams", _jams(rows))
                archive.writestr("__MACOSX/annotation/._00_Test-100-E_comp.jams", b"junk")
            expected = import_guitarset_comp_archive(path)
            for _ in range(10):
                self.assertEqual(import_guitarset_comp_archive(path), expected)
            notes, rejected, voicings = expected
            manifest = build_manifest(path, notes, rejected, voicings)
            self.assertEqual(manifest["comp_recording_count"], 1)
            self.assertEqual(manifest["accepted_note_count"], 2)
            self.assertEqual(manifest["derived_strum_voicing_count"], 1)
            self.assertFalse(manifest["left_hand_finger_labels_present"])
            self.assertFalse(manifest["training_authorized"])


if __name__ == "__main__":
    unittest.main()
