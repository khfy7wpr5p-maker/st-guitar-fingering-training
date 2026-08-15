from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "evidence" / "stage7g_e3_e_b_validation_batch_seal.json"


class Stage7GE3EBEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(SEAL.read_text(encoding="utf-8"))

    def test_identity_and_selected_batch_are_exact(self) -> None:
        data = self.data
        self.assertEqual(data["schema"], "st-guitar-stage7g-e3-e-b-validation-batch-seal-v1")
        self.assertEqual(
            data["status"],
            "BLIND_240_TASK_UNTOUCHED_VALIDATION_BATCH_SEALED_NO_TEACHER_ANSWERS",
        )
        self.assertEqual(data["base_main_sha"], "555e7a8c26954d638e1c4fb06372bb519d94180b")
        self.assertEqual(data["inputs"]["a3_inventory"]["disagreement_events"], 1937)
        self.assertEqual(data["inputs"]["a3_inventory"]["disagreement_families"], 24)
        self.assertEqual(
            data["inputs"]["a3_inventory"]["event_id_set_sha256"],
            "2d2d712b5c95b19f249aa950947062d78ab7f774a9b027b9b2386ef29d833ee1",
        )
        selection = data["selection"]
        self.assertEqual(selection["selected_tasks"], 240)
        self.assertEqual(selection["selected_families"], 24)
        self.assertEqual(selection["selected_family_task_count_min"], 1)
        self.assertEqual(selection["selected_family_task_count_max"], 12)
        self.assertEqual(selection["curriculum_level_diagnostic_counts"], {"L1": 25, "L2": 135, "L3": 43, "L4": 37})
        self.assertEqual(
            selection["selected_event_id_set_sha256"],
            "293ac5116a9c4b94993f150640c5113deaf213b7d59ddd6cebfdbec82cc9c7d7",
        )

    def test_external_artifact_hashes_are_frozen_without_raw_answers_in_git(self) -> None:
        artifacts = self.data["sealed_artifacts"]
        self.assertEqual(
            artifacts["teacher_manifest"]["sha256"],
            "17cf5513d1068b18b975a579da591540126e50c8fd9c89b59baaaee3e22ae352",
        )
        self.assertEqual(
            artifacts["internal_audit"]["sha256"],
            "75440e8e97c1ab80c27d93f8f37d1545a776e7fc8d9d0ddc6de5fdad9d98f7ee",
        )
        self.assertEqual(
            artifacts["response_template"]["sha256"],
            "00054dc4b669822ba885d5db7c8f2dcb46e29667b0b793148029006d23ffa550",
        )
        self.assertEqual(artifacts["teacher_package"]["bytes"], 373739)
        self.assertEqual(
            artifacts["teacher_package"]["sha256"],
            "d9c74e247d9fcab684b4965a7c0018ccb8beafb8fbfc92c09687ff3d494c858f",
        )
        self.assertFalse(artifacts["teacher_package"]["committed_to_git"])
        self.assertFalse(artifacts["teacher_package"]["contains_internal_audit"])
        self.assertFalse(artifacts["response_template"]["contains_answers"])

    def test_gate_is_preregistered_and_distinguishes_insufficient_from_negative(self) -> None:
        gate = self.data["untouched_evaluation_gate"]
        self.assertTrue(gate["frozen_before_teacher_answers"])
        self.assertEqual(gate["required_completed_tasks"], 240)
        self.assertEqual(gate["evidence_sufficiency"]["minimum_decisive_events"], 200)
        self.assertEqual(gate["evidence_sufficiency"]["minimum_evaluable_families"], 20)
        self.assertEqual(
            gate["evidence_sufficiency"]["if_not_met"],
            "INSUFFICIENT_UNTOUCHED_EVIDENCE_NO_PROMOTION",
        )
        finalization = gate["development_only_finalization"]
        self.assertEqual(finalization["fit_rows"], 399)
        self.assertEqual(finalization["compact_probability_threshold"], 0.5)
        self.assertFalse(finalization["threshold_selected_from_e3e_labels"])
        self.assertFalse(finalization["threshold_search_on_e3e"])
        requirements = gate["positive_requirements"]
        self.assertGreater(requirements["compact_precision_gte"], 0.66)
        self.assertTrue(gate["all_positive_requirements_must_pass"])
        self.assertTrue(gate["no_posthoc_rescue_or_retuning"])
        self.assertFalse(gate["authorizes_checkpoint"])
        self.assertFalse(gate["authorizes_production"])

    def test_scientific_boundaries_remain_closed_until_teacher_collection(self) -> None:
        boundary = self.data["scientific_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))
        self.assertTrue(self.data["provenance_and_rights"]["research_only"])
        self.assertFalse(self.data["provenance_and_rights"]["commercial_or_production_clearance"])
        self.assertEqual(
            self.data["next_gate"],
            "E3E_C_BLIND_TEACHER_GOLD_COLLECTION_AFTER_SEAL_MERGE",
        )


if __name__ == "__main__":
    unittest.main()
