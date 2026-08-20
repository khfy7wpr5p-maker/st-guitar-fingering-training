from __future__ import annotations

from collections import Counter, defaultdict
import unittest

from st_guitar_fingering_training.s2a_source_isolation import (
    QualifiedIsolatedSource,
    assign_origin_isolated_roles,
    canonical_origin_key,
    evaluate_source_isolation,
    exposed_origin_keys_from_filenames,
    historical_origin_quarantine,
    origin_family_id,
    origin_group_key,
)


PINNED = "18c0993cbe0a0948cbf0b7768bcb09ff81c23a9a"


def _qualified(origin_index: int, work_index: int) -> QualifiedIsolatedSource:
    origin = canonical_origin_key(f"Fresh Franchise {origin_index:03d}")
    serial = origin_index * 10 + work_index + 1
    return QualifiedIsolatedSource(
        canonical_work_key=f"work-{origin_index:03d}-{work_index:02d}",
        origin_group_key=origin,
        path=f"AnimeTAB/Entire songs/[Fresh Franchise {origin_index:03d}]Song {work_index:02d}.xml",
        blob_sha=f"{serial:040x}"[-40:],
        raw_sha256=f"{serial:064x}"[-64:],
        byte_size=1000 + serial,
        pitched_event_count=20,
        chord_event_count=8,
    )


class S2ASourceIsolationTests(unittest.TestCase):
    def test_origin_key_uses_explicit_bracketed_identity(self):
        self.assertEqual(origin_group_key("[NARUTO -ナルト-]Alone.xml"), canonical_origin_key("NARUTO -ナルト-"))
        with self.assertRaisesRegex(ValueError, "no explicit bracketed origin"):
            origin_group_key("Unknown Song.xml")

    def test_historical_exact_origin_is_rejected_even_for_different_work(self):
        exposed = exposed_origin_keys_from_filenames(["[CLANNAD]欢乐岛.xml"])
        quarantine = historical_origin_quarantine(exposed_origin_keys=exposed, alias_groups=())
        decision = evaluate_source_isolation(
            "[CLANNAD]团子大家族.xml",
            historical_quarantine=quarantine,
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "S2A_SRC_004_FRANCHISE_ORIGIN_OVERLAP")

    def test_multilingual_alias_closure_rejects_same_franchise(self):
        exposed = exposed_origin_keys_from_filenames(["[SLAM DUNK]好想大声说爱你.xml"])
        quarantine = historical_origin_quarantine(
            exposed_origin_keys=exposed,
            alias_groups=(("SLAM DUNK", "灌篮高手"),),
        )
        decision = evaluate_source_isolation(
            "[灌篮高手]直到世界的尽头.xml",
            historical_quarantine=quarantine,
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "S2A_SRC_004_FRANCHISE_ORIGIN_OVERLAP")

    def test_known_air_alias_is_quarantined(self):
        exposed = exposed_origin_keys_from_filenames(["[エアー]鸟之诗.xml"])
        quarantine = historical_origin_quarantine(
            exposed_origin_keys=exposed,
            alias_groups=(("エアー", "AIR"),),
        )
        decision = evaluate_source_isolation("[AIR]青空.xml", historical_quarantine=quarantine)
        self.assertFalse(decision.accepted)

    def test_missing_origin_is_ambiguous_and_rejected(self):
        decision = evaluate_source_isolation("Lilium modified.xml", historical_quarantine=())
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "S2A_SRC_005_IDENTITY_AMBIGUOUS")

    def test_reserved_origin_cannot_reenter_under_another_work(self):
        origin = origin_group_key("[Fresh Franchise]Song A.xml")
        decision = evaluate_source_isolation(
            "[Fresh Franchise]Song B.xml",
            historical_quarantine=(),
            already_reserved_origins=(origin,),
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "S2A_SRC_006_RESERVED_ORIGIN_REUSE")

    def test_distinct_explicit_origin_is_eligible(self):
        decision = evaluate_source_isolation(
            "[Fresh Franchise]Song.xml",
            historical_quarantine=(canonical_origin_key("Old Franchise"),),
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reason, "S2A_SRC_000_DISTINCT_ORIGIN")

    def test_alias_group_must_be_nontrivial(self):
        exposed = exposed_origin_keys_from_filenames(["[A]Song.xml"])
        with self.assertRaisesRegex(ValueError, "at least two distinct aliases"):
            historical_origin_quarantine(exposed_origin_keys=exposed, alias_groups=(("A", "A"),))

    def test_origin_family_id_is_shared_by_multiple_works(self):
        first = _qualified(1, 0)
        second = _qualified(1, 1)
        self.assertEqual(origin_family_id(first.origin_group_key), origin_family_id(second.origin_group_key))

    def test_role_assignment_keeps_origin_families_disjoint_and_sources_80_20_20(self):
        rows = tuple(_qualified(origin, work) for origin in range(100) for work in range(2))
        reserved = assign_origin_isolated_roles(rows, pinned_commit=PINNED)
        counts = Counter(row.role for row in reserved)
        self.assertEqual(
            counts,
            {
                "PRIMARY_DEVELOPMENT": 80,
                "CONTINGENCY_DEVELOPMENT": 20,
                "UNTOUCHED_FINAL": 20,
            },
        )
        roles_by_origin = defaultdict(set)
        for row in reserved:
            roles_by_origin[row.origin_group_key].add(row.role)
        self.assertTrue(all(len(roles) == 1 for roles in roles_by_origin.values()))
        primary_families = {row.family_id for row in reserved if row.role == "PRIMARY_DEVELOPMENT"}
        contingency_families = {row.family_id for row in reserved if row.role == "CONTINGENCY_DEVELOPMENT"}
        final_families = {row.family_id for row in reserved if row.role == "UNTOUCHED_FINAL"}
        self.assertEqual(len(primary_families), 60)
        self.assertEqual(len(contingency_families), 20)
        self.assertEqual(len(final_families), 20)
        self.assertFalse(primary_families & contingency_families)
        self.assertFalse(primary_families & final_families)
        self.assertFalse(contingency_families & final_families)

    def test_role_assignment_fails_closed_below_80_origin_families(self):
        rows = tuple(_qualified(origin, work) for origin in range(79) for work in range(2))
        with self.assertRaisesRegex(ValueError, "at least 80 qualified origin families"):
            assign_origin_isolated_roles(rows, pinned_commit=PINNED)


if __name__ == "__main__":
    unittest.main()
