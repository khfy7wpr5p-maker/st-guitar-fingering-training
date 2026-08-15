from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7GE3BR1EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_e3_b_r1_curriculum_batch01_result.json"
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_schema_status_and_base(self):
        self.assertEqual(self.data["schema"], "st-guitar-stage7g-e3-b-r1-result-v1")
        self.assertEqual(self.data["status"], "SEALED_CURRICULUM_BATCH_READY_PENDING_MERGE")
        self.assertEqual(self.data["base_main_sha"], "5a8d38071a265eeb984a8560586dca31cf0b5eac")

    def test_inventory_reproduces_pinned_batch_and_excludes_old_tasks(self):
        inv = self.data["target_blind_inventory"]
        self.assertEqual(inv["source_files"], 40)
        self.assertEqual(inv["parsed_pitched_events"], 24066)
        self.assertEqual(inv["chord_events"], 13542)
        self.assertEqual(inv["ambiguous_events"], 12714)
        self.assertEqual(inv["open_low_compact_disagreements"], 5626)
        self.assertEqual(inv["previously_sealed_task_ids_excluded"], 600)
        self.assertEqual(inv["remaining_unlabeled_disagreements"], 5026)
        self.assertEqual(inv["level_counts"], {"L1": 788, "L2": 1482, "L3": 1202, "L4": 1554})

    def test_specialist_reconstruction_guard_is_exact(self):
        guard = self.data["specialist_reconstruction_guard"]
        self.assertEqual(guard["pairwise_tasks_checked"], 562)
        self.assertEqual(guard["both_options_match"], 562)
        self.assertEqual(guard["open_low_match"], 562)
        self.assertEqual(guard["compact_match"], 562)
        self.assertEqual(guard["open_low_training_events"], 480)
        self.assertEqual(guard["compact_training_events"], 480)
        self.assertEqual(guard["open_low_pairwise_matrix_shape"], [6900, 4])
        self.assertEqual(guard["compact_pairwise_matrix_shape"], [7708, 4])

    def test_quota_is_frozen_and_curriculum_weighted(self):
        quota = self.data["quota_freeze"]
        self.assertEqual({k: quota[k] for k in ("L1", "L2", "L3", "L4")}, {"L1": 140, "L2": 120, "L3": 80, "L4": 60})
        self.assertEqual(quota["total"], 400)
        self.assertEqual(self.data["selected"]["tasks"], 400)
        self.assertEqual(self.data["selected"]["families"], 40)
        self.assertEqual(self.data["selected"]["level_counts"], {"L1": 140, "L2": 120, "L3": 80, "L4": 60})

    def test_external_package_is_hashed_but_not_committed(self):
        package = self.data["external_package"]
        self.assertEqual(package["sha256"], "e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef")
        self.assertEqual(package["bytes"], 97856)
        self.assertFalse(package["raw_package_committed_to_git"])

    def test_scientific_boundaries_stay_closed(self):
        boundary = self.data["scientific_boundary"]
        for key in (
            "teacher_responses_used_for_generation",
            "old_556_labels_used_for_selection",
            "old_600_task_ids_reused",
            "stage7e_used",
            "model_fit",
            "checkpoint_retained",
            "production_integration",
            "rule_property_records_are_teacher_gold",
        ):
            self.assertFalse(boundary[key], key)
        self.assertEqual(boundary["new_teacher_labels_created"], 0)


if __name__ == "__main__":
    unittest.main()
