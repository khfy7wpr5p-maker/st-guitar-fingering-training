from __future__ import annotations

import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "evidence/stage7g_c_r1_animetab_batch01_manifest.json").read_text(encoding="utf-8"))
RESULT = json.loads((ROOT / "evidence/stage7g_c_r1_animetab_batch01_result.json").read_text(encoding="utf-8"))


class Stage7GCR1AnimeTABEvidenceTests(unittest.TestCase):
    def test_batch_is_pinned_unique_and_keeps_raw_scores_out_of_git(self) -> None:
        self.assertEqual(MANIFEST["schema"], "st-guitar-stage7g-c-r1-animetab-batch01-manifest-v1")
        self.assertEqual(MANIFEST["status"], "PINNED_RESEARCH_SOURCE_BATCH")
        self.assertEqual(MANIFEST["family_count"], 40)
        self.assertEqual(len(MANIFEST["sources"]), 40)
        self.assertEqual(len({row["family_id"] for row in MANIFEST["sources"]}), 40)
        self.assertEqual(len({row["filename"] for row in MANIFEST["sources"]}), 40)
        self.assertEqual(len({row["sha256"] for row in MANIFEST["sources"]}), 40)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in MANIFEST["sources"]))
        self.assertFalse(MANIFEST["raw_musicxml_committed_to_git"])
        self.assertFalse(MANIFEST["commercial_or_production_rights_verified"])

    def test_development_and_final_quarantines_remain_disjoint(self) -> None:
        quarantine = MANIFEST["historical_development_quarantine"]
        self.assertEqual(quarantine["source_hash_count"], 42)
        self.assertEqual(quarantine["family_key_count"], 29)
        self.assertEqual(quarantine["batch_source_hash_overlap_count"], 0)
        self.assertEqual(quarantine["batch_family_key_overlap_count"], 0)
        self.assertFalse(MANIFEST["stage7e_quarantine"]["reused"])
        identity = RESULT["batch_identity"]
        self.assertEqual(identity["historical_development_hash_overlap"], 0)
        self.assertEqual(identity["historical_development_family_key_overlap"], 0)
        self.assertFalse(identity["stage7e_final_reuse"])

    def test_staff2_target_free_intake_is_physical_and_large_enough(self) -> None:
        audit = RESULT["source_encoding_audit"]
        self.assertEqual(MANIFEST["staff_id"], "2")
        self.assertEqual(MANIFEST["pitch_mode"], "sounding_exact")
        self.assertEqual(MANIFEST["tuning_midi"], [64, 59, 55, 50, 45, 40])
        self.assertEqual(audit["single_part_files"], 40)
        self.assertEqual(audit["staff2_standard_six_string_tuning_files"], 40)
        self.assertEqual(audit["staff2_xml_minus_physical_pitch_relation_exact_zero_files"], 40)
        self.assertTrue(audit["technical_string_fret_used_only_for_encoding_audit"])
        self.assertFalse(audit["technical_string_fret_used_for_sampling_or_labels"])

        intake = RESULT["target_free_staff2_intake"]
        self.assertEqual(intake["chord_events"], 13542)
        self.assertEqual(intake["ambiguous_chord_events"], 12714)
        self.assertEqual(intake["families_with_ambiguous_events"], 40)
        self.assertEqual(intake["single_candidate_chord_events_excluded"], 826)
        self.assertEqual(intake["zero_candidate_chord_events_excluded"], 2)
        self.assertTrue(intake["grace_notes_excluded_by_stage7g_c_v1"])

    def test_frozen_specialist_guard_exactly_reproduces_stage7b_c2(self) -> None:
        guard = RESULT["frozen_specialist_reconstruction_guard"]
        self.assertTrue(guard["pairwise_specialists_rebuilt_in_memory_only"])
        self.assertTrue(guard["matches_stage7b_c2"])
        expected = {
            "open_low": 1.0,
            "compact": 1.0,
            "mid_position": 0.9458333333333332,
            "high_position": 0.9541666666666668,
            "common_tone": 0.9217391304347828,
        }
        for style, value in expected.items():
            self.assertTrue(math.isclose(guard["macro_top1"][style], value, rel_tol=0.0, abs_tol=1e-15))
        self.assertFalse(guard["checkpoint_retained"])

    def test_disagreement_pool_is_sufficient_but_teacher_gold_gate_stays_closed(self) -> None:
        disagreement = RESULT["stateless_specialist_disagreement"]
        self.assertEqual(disagreement["specialists"], ["open_low", "compact", "mid_position", "high_position"])
        self.assertFalse(disagreement["common_tone_included"])
        self.assertEqual(disagreement["eligible_ambiguous_events"], 12714)
        self.assertEqual(disagreement["open_low_compact_disagreement_events"], 5626)
        self.assertEqual(disagreement["any_stateless_disagreement_events"], 12358)
        self.assertEqual(disagreement["four_specialist_consensus_events"], 356)
        self.assertEqual(disagreement["any_stateless_disagreement_events"] + disagreement["four_specialist_consensus_events"], 12714)
        self.assertEqual(disagreement["families_with_open_low_compact_disagreement"], 40)
        self.assertGreaterEqual(disagreement["minimum_open_low_compact_disagreement_per_family"], 15)

        readiness = RESULT["annotation_readiness"]
        self.assertGreaterEqual(readiness["available_independent_families"], readiness["stage7g_required_independent_families"])
        self.assertGreaterEqual(readiness["available_unlabeled_ambiguous_tasks"], readiness["stage7g_required_teacher_gold_ambiguous_events"])
        self.assertGreaterEqual(readiness["available_unlabeled_specialist_disagreement_tasks"], readiness["stage7g_required_specialist_disagreement_events"])
        preview = readiness["deterministic_600_task_sampling_preview"]
        self.assertEqual(preview["selected_families"], 40)
        self.assertEqual(preview["selected_open_low_compact_disagreement"], 600)
        self.assertFalse(preview["tier1_or_consensus_needed"])
        self.assertEqual(readiness["teacher_gold_labels_created"], 0)
        self.assertFalse(readiness["teacher_gold_corpus_gate_passed"])
        self.assertTrue(readiness["source_pool_ready_for_annotation"])
        self.assertFalse(readiness["training_authorized"])

    def test_checkpoint_and_production_remain_closed(self) -> None:
        safety = RESULT["safety"]
        self.assertFalse(safety["raw_musicxml_committed_to_git"])
        self.assertFalse(safety["observed_source_voicing_used_for_sampling"])
        self.assertEqual(safety["teacher_gold_labels_created"], 0)
        self.assertFalse(safety["teacher_gold_model_fit"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["stage7e_final_corpus_reused"])


if __name__ == "__main__":
    unittest.main()
