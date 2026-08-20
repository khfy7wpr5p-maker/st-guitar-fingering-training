from __future__ import annotations

import unittest

from st_guitar_fingering_training.s2a_source_isolation import (
    canonical_origin_key,
    evaluate_source_isolation,
    exposed_origin_keys_from_filenames,
    historical_origin_quarantine,
    origin_group_key,
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


if __name__ == "__main__":
    unittest.main()
