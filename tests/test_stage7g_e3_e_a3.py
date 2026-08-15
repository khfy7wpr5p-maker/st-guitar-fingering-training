from __future__ import annotations

import unittest

from st_guitar_fingering_training.stage7g_e3_e_a3 import (
    build_open_low_compact_disagreement_inventory,
    reconstruct_frozen_open_low_compact_specialists,
)
from st_guitar_fingering_training.target_free_musicxml import TargetFreeEvent, TargetFreeSource


class Stage7GE3EA3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.models, cls.guard = reconstruct_frozen_open_low_compact_specialists()

    def test_reconstruction_guard_matches_frozen_stage7b_c2(self) -> None:
        self.assertEqual(
            self.guard["status"],
            "PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION",
        )
        self.assertEqual(self.guard["balanced_synthetic_families"], 100)
        self.assertEqual(self.guard["specialists"]["open_low"]["synthetic_families"], 20)
        self.assertEqual(self.guard["specialists"]["compact"]["synthetic_families"], 20)
        self.assertEqual(self.guard["specialists"]["open_low"]["training_events"], 480)
        self.assertEqual(self.guard["specialists"]["compact"]["training_events"], 480)
        self.assertEqual(
            self.guard["specialists"]["open_low"]["pairwise_matrix_shape"],
            [6900, 4],
        )
        self.assertEqual(
            self.guard["specialists"]["compact"]["pairwise_matrix_shape"],
            [7708, 4],
        )
        self.assertEqual(self.guard["specialists"]["open_low"]["stage7b_c2_macro_top1"], 1.0)
        self.assertEqual(self.guard["specialists"]["compact"]["stage7b_c2_macro_top1"], 1.0)
        self.assertFalse(self.guard["teacher_gold_used"])
        self.assertFalse(self.guard["checkpoint_retained"])

    def test_inventory_is_aggregate_target_blind_and_has_no_teacher_gold(self) -> None:
        tuning = (64, 59, 55, 50, 45, 40)
        source = TargetFreeSource(
            family_id="fixture_family",
            source_sha256="1" * 64,
            musicxml_version="3.1",
            software="fixture",
            pitch_mode="sounding_exact",
            tuning=tuning,
            part_id="P1",
            selected_staff="1",
            events=(
                TargetFreeEvent(
                    family_id="fixture_family",
                    source_sha256="1" * 64,
                    musicxml_version="3.1",
                    software="fixture",
                    pitch_mode="sounding_exact",
                    tuning=tuning,
                    measure="1",
                    onset=0,
                    duration=4,
                    voice="1",
                    pitches_midi=(48, 52, 55),
                ),
                TargetFreeEvent(
                    family_id="fixture_family",
                    source_sha256="1" * 64,
                    musicxml_version="3.1",
                    software="fixture",
                    pitch_mode="sounding_exact",
                    tuning=tuning,
                    measure="2",
                    onset=0,
                    duration=4,
                    voice="1",
                    pitches_midi=(64,),
                ),
            ),
        )
        report = build_open_low_compact_disagreement_inventory(
            (source,),
            specialist_models=self.models,
        )
        self.assertEqual(report["eligible_families"], 1)
        self.assertEqual(report["pitched_events"], 2)
        self.assertEqual(report["chord_events"], 1)
        self.assertGreater(report["ambiguous_chords"], 0)
        self.assertEqual(len(report["disagreement_event_id_set_digest_sha256"]), 64)
        self.assertFalse(report["teacher_gold_generated"])
        self.assertFalse(report["teacher_gold_answers_read"])
        self.assertFalse(report["router_scored"])
        self.assertFalse(report["e3e_model_fit"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])
        self.assertNotIn("events", report["families"]["fixture_family"])

    def test_inventory_rejects_wrong_specialist_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly frozen open_low and compact"):
            build_open_low_compact_disagreement_inventory((), specialist_models={"open_low": object()})


if __name__ == "__main__":
    unittest.main()
