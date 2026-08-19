from __future__ import annotations

import unittest

from st_guitar_fingering_training.s2a_source_reservation import (
    AnimeTabTreeEntry,
    CONTINGENCY_DEVELOPMENT_FAMILIES,
    PRIMARY_DEVELOPMENT_FAMILIES,
    TOTAL_RESERVED_FAMILIES,
    UNTOUCHED_FINAL_FAMILIES,
    assign_reservation_roles,
    canonical_work_key,
    exposed_work_keys_from_filenames,
    family_id_for_work_key,
    fresh_work_groups,
    parse_full_track_tree_entries,
)


PINNED = "18c0993cbe0a0948cbf0b7768bcb09ff81c23a9a"


class S2ASourceReservationTests(unittest.TestCase):
    def test_canonical_key_collapses_obvious_arrangement_versions(self):
        variants = (
            "[エルフェンリート]Lilium.xml",
            "[エルフェンリート]Lilium 3.xml",
            "[エルフェンリート]Lilium (in Ab).xml",
            "[エルフェンリート]Lilium by Player.xml",
            "[エルフェンリート]Lilium tv.side.xml",
        )
        keys = {canonical_work_key(value) for value in variants}
        self.assertEqual(len(keys), 1)

    def test_canonical_key_does_not_collapse_distinct_titles_from_same_origin(self):
        first = canonical_work_key("[CLANNAD]欢乐岛.xml")
        second = canonical_work_key("[CLANNAD]团子大家族.xml")
        self.assertNotEqual(first, second)

    def test_tree_parser_accepts_only_entire_song_xml_blobs(self):
        rows = [
            {"path": "AnimeTAB/Entire songs/[A]Song.xml", "type": "blob", "sha": "a" * 40, "size": 100},
            {"path": "AnimeTAB/Clips/[A]Song.xml", "type": "blob", "sha": "b" * 40, "size": 100},
            {"path": "AnimeTAB/Entire songs/readme.txt", "type": "blob", "sha": "c" * 40, "size": 100},
            {"path": "AnimeTAB/Entire songs/subdir", "type": "tree", "sha": "d" * 40},
        ]
        parsed = parse_full_track_tree_entries(rows)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].filename, "[A]Song.xml")

    def test_all_variants_of_teacher_exposed_work_are_excluded(self):
        entries = (
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[A]Song.xml", "a" * 40, 100),
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[A]Song 2.xml", "b" * 40, 100),
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[B]Fresh.xml", "c" * 40, 100),
        )
        exposed = exposed_work_keys_from_filenames(["[A]Song.xml"])
        groups = fresh_work_groups(entries, pinned_commit=PINNED, exposed_work_keys=exposed)
        self.assertEqual([key for key, _ in groups], [canonical_work_key("[B]Fresh.xml")])

    def test_variant_and_work_order_is_deterministic(self):
        entries = (
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[A]Song 2.xml", "b" * 40, 100),
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[B]Fresh.xml", "c" * 40, 100),
            AnimeTabTreeEntry("AnimeTAB/Entire songs/[A]Song.xml", "a" * 40, 100),
        )
        first = fresh_work_groups(entries, pinned_commit=PINNED, exposed_work_keys=())
        second = fresh_work_groups(tuple(reversed(entries)), pinned_commit=PINNED, exposed_work_keys=())
        self.assertEqual(first, second)

    def test_role_assignment_is_exactly_predeclared_80_20_20(self):
        rows = []
        for index in range(TOTAL_RESERVED_FAMILIES):
            work_key = f"work{index:03d}"
            entry = AnimeTabTreeEntry(
                path=f"AnimeTAB/Entire songs/[X]Work {index:03d}.xml",
                blob_sha=f"{index:040x}"[-40:],
                size=100 + index,
            )
            rows.append((work_key, entry, f"{index + 1:064x}"[-64:], 20, 8))
        reserved = assign_reservation_roles(rows)
        self.assertEqual(len(reserved), TOTAL_RESERVED_FAMILIES)
        self.assertEqual(sum(item.role == "PRIMARY_DEVELOPMENT" for item in reserved), PRIMARY_DEVELOPMENT_FAMILIES)
        self.assertEqual(sum(item.role == "CONTINGENCY_DEVELOPMENT" for item in reserved), CONTINGENCY_DEVELOPMENT_FAMILIES)
        self.assertEqual(sum(item.role == "UNTOUCHED_FINAL" for item in reserved), UNTOUCHED_FINAL_FAMILIES)
        self.assertEqual(len({item.family_id for item in reserved}), TOTAL_RESERVED_FAMILIES)

    def test_role_assignment_fails_closed_below_120_qualified_works(self):
        entry = AnimeTabTreeEntry("AnimeTAB/Entire songs/[A]Song.xml", "a" * 40, 100)
        with self.assertRaisesRegex(ValueError, "at least 120 qualified works"):
            assign_reservation_roles([("work", entry, "f" * 64, 20, 8)])

    def test_family_id_contains_no_source_title(self):
        work_key = canonical_work_key("[A]Sensitive Song Name.xml")
        family_id = family_id_for_work_key(work_key)
        self.assertTrue(family_id.startswith("animetabs2a-"))
        self.assertNotIn("sensitive", family_id)
        self.assertNotIn("song", family_id)


if __name__ == "__main__":
    unittest.main()
