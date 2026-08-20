from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.s2a_prior_final_semantics import (
    load_prior_final_semantic_quarantine,
    reserved_semantic_overlaps,
    semantic_work_key,
)


MANIFEST = Path("evidence/stage7g_e3_s2a_prior_final_semantic_quarantine_v1.json")


class PriorFinalSemanticQuarantineTests(unittest.TestCase):
    def test_cross_encoding_and_origin_normalize_to_same_work(self):
        self.assertEqual(semantic_work_key("Canon_in_D.mxl"), "canonind")
        self.assertEqual(semantic_work_key("[Different Origin]Canon in D.xml"), "canonind")
        self.assertEqual(
            semantic_work_key("[Different Origin]Canon in D (arranged for guitar).musicxml"),
            "canonind",
        )
        self.assertEqual(semantic_work_key("[Other]In Da Club full version.xml"), "indaclub")

    def test_bare_trailing_numbers_remain_musically_meaningful(self):
        self.assertNotEqual(
            semantic_work_key("Prelude No. 2.xml"),
            semantic_work_key("Prelude No. 4.xml"),
        )

    def test_frozen_manifest_has_40_independent_prior_final_families(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        quarantine = load_prior_final_semantic_quarantine(payload)
        self.assertEqual(quarantine.family_count, 40)
        self.assertEqual(quarantine.semantic_key_count, 69)
        stage7e_rows = [row for row in payload["families"] if row["source_stage"] == "7E-R1"]
        stagee_rows = [row for row in payload["families"] if row["source_stage"] == "7G-E3-E-A1"]
        self.assertEqual(len(stage7e_rows), 8)
        self.assertEqual(len(stagee_rows), 32)
        self.assertEqual(sum(len(row["sealed_paths"]) for row in stage7e_rows), 16)
        self.assertEqual(payload["provenance"]["stage7e"]["corrected_semantic_families_with_ambiguous_events"], 8)
        self.assertTrue(payload["provenance"]["stage7e"]["corrected_sufficiency_gate_passed"])

    def test_same_work_in_different_file_or_origin_is_rejected(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        quarantine = load_prior_final_semantic_quarantine(payload)
        overlaps = reserved_semantic_overlaps(
            [
                "AnimeTAB/Entire songs/[Unrelated Franchise]Canon in D.xml",
                "AnimeTAB/Entire songs/[Another Franchise]In Da Club full version.xml",
            ],
            quarantine=quarantine,
        )
        self.assertEqual(len(overlaps), 2)
        self.assertEqual({row[2] for row in overlaps}, {"pachelbel_canon_d", "stage7e_in_da_club"})

    def test_duplicate_semantic_alias_across_families_fails_closed(self):
        payload = {
            "schema": "st-guitar-s2a-prior-final-semantic-quarantine-v1",
            "expected_family_count": 2,
            "families": [
                {"family_id": "a", "source_stage": "x", "aliases": ["Canon in D"]},
                {"family_id": "b", "source_stage": "y", "aliases": ["Canon_in_D.mxl"]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "more than one protected family"):
            load_prior_final_semantic_quarantine(payload)


if __name__ == "__main__":
    unittest.main()
