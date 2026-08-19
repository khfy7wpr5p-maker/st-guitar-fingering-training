from __future__ import annotations

import json
from pathlib import Path
import unittest


class S2ABatch01SealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_e3_s2a_batch01_seal.json"
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def test_batch_identity_and_balance_are_frozen(self):
        self.assertEqual(self.data["schema"], "st-guitar-stage7g-e3-s2a-batch01-seal-v1")
        self.assertEqual(self.data["status"], "SEALED_BLIND_FIRST_PASS_PACKAGE_READY_FOR_COLLECTION")
        batch = self.data["batch"]
        self.assertEqual(batch["task_count"], 720)
        self.assertEqual(batch["family_count"], 40)
        self.assertEqual(batch["event_count"], 320)
        self.assertEqual(batch["min_tasks_per_family"], 18)
        self.assertEqual(batch["max_tasks_per_family"], 18)
        self.assertEqual(batch["pair_type_counts"], {"FINGER_ONLY": 360, "MIXED": 360})
        self.assertEqual(batch["distance_stratum_counts"], {"NEAR": 240, "MID": 240, "FAR": 240})
        self.assertTrue(all(value == 120 for value in batch["cell_counts"].values()))
        self.assertEqual(batch["session_task_counts"], [120] * 6)
        self.assertEqual(len(set(batch["session_manifest_sha256"])), 6)

    def test_historical_answers_are_not_reclassified(self):
        source = self.data["source"]
        self.assertFalse(source["historical_teacher_responses_reused"])
        self.assertTrue(source["source_family_identities_reused_as_label_free_music_sources"])
        self.assertFalse(source["raw_source_bytes_retained"])
        self.assertTrue(source["research_only_until_rights_review"])
        self.assertFalse(source["commercial_or_production_rights_verified"])

    def test_teacher_surface_is_blind_but_fingering_is_explicit(self):
        blind = self.data["blinding"]
        for key in (
            "teacher_sees_family_identity",
            "teacher_sees_pair_type",
            "teacher_sees_distance_stratum",
            "teacher_sees_feature_values",
            "teacher_sees_model_scores",
            "teacher_sees_historical_responses",
        ):
            self.assertFalse(blind[key], key)
        self.assertTrue(blind["teacher_sees_exact_pitch_string_fret_finger"])
        self.assertTrue(blind["teacher_sees_barre_metadata"])

    def test_collection_does_not_preapprove_fit_or_promotion(self):
        boundary = self.data["scientific_boundary"]
        for value in boundary.values():
            self.assertFalse(value)
        self.assertEqual(
            self.data["next_gate"],
            "COLLECT_ALL_SIX_FIRST_PASS_SESSIONS_THEN_VALIDATE_AND_BUILD_REPEAT",
        )


if __name__ == "__main__":
    unittest.main()
