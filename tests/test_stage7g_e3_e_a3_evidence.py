from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "stage7g_e3_e_a3_disagreement_inventory.json"


class Stage7GE3EA3EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_identity_execution_and_reconstruction_guard_are_pinned(self) -> None:
        data = self.data
        self.assertEqual(data["schema"], "st-guitar-stage7g-e3-e-a3-disagreement-inventory-seal-v1")
        self.assertEqual(data["stage"], "7G-E3-E-A3")
        self.assertEqual(data["status"], "TARGET_BLIND_OPEN_LOW_COMPACT_INVENTORY_SEALED")
        self.assertEqual(data["base_main_sha"], "2ca1e18621fbdb8f99ad4e9e14d9236c49ffa750")
        self.assertEqual(data["execution"]["workflow_run_number"], 123)
        self.assertEqual(data["execution"]["workflow_run_id"], 31883699570)
        self.assertEqual(data["execution"]["job_id"], 95009720181)
        self.assertEqual(data["execution"]["unit_tests"], "SUCCESS")
        self.assertEqual(data["execution"]["compile_validation"], "SUCCESS")
        self.assertEqual(data["execution"]["stage7b_c2_workflow_step"], "SKIPPED")

        guard = data["specialist_reconstruction_guard"]
        self.assertEqual(guard["status"], "PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION")
        self.assertEqual(guard["balanced_synthetic_families"], 100)
        self.assertEqual(guard["open_low"]["training_events"], 480)
        self.assertEqual(guard["open_low"]["pairwise_matrix_shape"], [6900, 4])
        self.assertEqual(guard["open_low"]["stage7b_c2_macro_top1"], 1.0)
        self.assertEqual(guard["compact"]["training_events"], 480)
        self.assertEqual(guard["compact"]["pairwise_matrix_shape"], [7708, 4])
        self.assertEqual(guard["compact"]["stage7b_c2_macro_top1"], 1.0)
        self.assertFalse(guard["e3e_teacher_gold_used"])
        self.assertFalse(guard["checkpoint_retained"])

    def test_inventory_aggregates_match_pinned_live_result(self) -> None:
        inventory = self.data["inventory"]
        self.assertEqual(inventory["eligible_families"], 31)
        self.assertEqual(inventory["families_with_open_low_compact_disagreement"], 24)
        self.assertEqual(inventory["families_without_open_low_compact_disagreement"], 7)
        self.assertEqual(inventory["pitched_events"], 18664)
        self.assertEqual(inventory["chord_events"], 4159)
        self.assertEqual(inventory["zero_candidate_chords"], 647)
        self.assertEqual(inventory["single_candidate_chords"], 74)
        self.assertEqual(inventory["ambiguous_chords"], 3438)
        self.assertEqual(inventory["open_low_compact_disagreements"], 1937)
        self.assertAlmostEqual(inventory["disagreement_rate_among_ambiguous"], 1937 / 3438)
        self.assertEqual(inventory["ambiguous_candidate_count_min"], 2)
        self.assertEqual(inventory["ambiguous_candidate_count_max"], 165)
        self.assertAlmostEqual(inventory["ambiguous_candidate_count_mean"], 21.562536358347877)
        self.assertEqual(
            inventory["disagreement_event_id_set_digest_sha256"],
            "2d2d712b5c95b19f249aa950947062d78ab7f774a9b027b9b2386ef29d833ee1",
        )
        self.assertEqual(len(inventory["families"]), 31)

        sums = {
            key: sum(row[key] for row in inventory["families"].values())
            for key in (
                "pitched_events",
                "chord_events",
                "zero_candidate_chords",
                "single_candidate_chords",
                "ambiguous_chords",
                "open_low_compact_disagreements",
            )
        }
        for key, value in sums.items():
            self.assertEqual(value, inventory[key], key)
        self.assertEqual(
            sum(row["open_low_compact_disagreements"] > 0 for row in inventory["families"].values()),
            24,
        )

    def test_a3_does_not_posthoc_choose_validation_quota_or_open_scientific_boundaries(self) -> None:
        interpretation = self.data["interpretation"]
        self.assertEqual(interpretation["maximum_family_coverage_from_disagreement_only_pool"], 24)
        self.assertFalse(interpretation["numeric_e3e_validation_family_floor_pre_registered"])
        self.assertFalse(interpretation["numeric_e3e_event_quota_pre_registered"])
        self.assertFalse(interpretation["quota_or_family_coverage_decision_made_in_a3"])
        self.assertEqual(
            interpretation["next_gate"],
            "E3E_B_PREREGISTER_QUOTA_FAMILY_ALLOCATION_AND_BLIND_PACKAGE_BEFORE_TEACHER_LABELS",
        )

        boundary = self.data["scientific_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))

        # Persistent evidence is aggregate-only: no raw event-ID list or specialist top-1 rows.
        serialized = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn('"event_ids"', serialized)
        self.assertNotIn('"specialist_top1"', serialized)
        self.assertNotIn('"teacher_preferred"', serialized)


if __name__ == "__main__":
    unittest.main()
