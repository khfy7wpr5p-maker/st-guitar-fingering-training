from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "evidence" / "stage7g_c_target_free_musicxml_contract.json"
TARGET_FREE = ROOT / "src" / "st_guitar_fingering_training" / "target_free_musicxml.py"
SAMPLING = ROOT / "src" / "st_guitar_fingering_training" / "teacher_task_sampling.py"


class Stage7GCTargetFreeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_keeps_labels_training_checkpoint_and_production_closed(self) -> None:
        self.assertEqual(self.contract["stage"], "7G-C")
        self.assertEqual(self.contract["status"], "TARGET_FREE_MUSICXML_INTAKE_IMPLEMENTED")
        safety = self.contract["safety"]
        self.assertEqual(safety["teacher_gold_labels"], 0)
        self.assertFalse(safety["model_fit"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])

    def test_target_free_intake_is_explicit_and_does_not_require_tab_targets(self) -> None:
        contract = self.contract["input_contract"]
        self.assertTrue(contract["six_string_tuning_explicit"])
        self.assertTrue(contract["pitch_mode_explicit"])
        self.assertEqual(
            contract["supported_pitch_modes"],
            ["sounding_exact", "written_octave_plus_12"],
        )
        self.assertFalse(contract["technical_string_fret_required"])
        self.assertFalse(contract["technical_string_fret_used"])
        self.assertTrue(contract["multi_part_requires_explicit_part_id"])
        self.assertTrue(contract["multi_staff_requires_explicit_staff_id"])

    def test_deterministic_candidate_authority_and_final_quarantine_remain_unchanged(self) -> None:
        candidate = self.contract["candidate_contract"]
        self.assertEqual(candidate["physical_candidate_authority"], "deterministic valid_chord_voicings()")
        self.assertEqual(candidate["minimum_candidates_for_annotation"], 2)
        self.assertFalse(candidate["specialist_predictions_teacher_facing"])
        self.assertFalse(candidate["source_observed_voicing_used"])
        self.assertFalse(self.contract["quarantine"]["stage7e_final_sources_allowed"])

    def test_implementation_has_no_teacher_gold_finalization_or_model_fit_seam(self) -> None:
        target_text = TARGET_FREE.read_text(encoding="utf-8")
        sampling_text = SAMPLING.read_text(encoding="utf-8")
        self.assertNotIn("finalize_teacher_gold_record", target_text)
        self.assertNotIn("fit(", target_text)
        self.assertNotIn("train_", target_text)
        self.assertIn("valid_chord_voicings", sampling_text)
        self.assertIn("forbidden_source_hashes", sampling_text)
        self.assertIn("forbidden_source_origins", sampling_text)


if __name__ == "__main__":
    unittest.main()
