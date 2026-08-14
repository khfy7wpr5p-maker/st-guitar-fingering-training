from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "stage7g_b_r1_source_intake_manifest.json"
RESULT = ROOT / "evidence" / "stage7g_b_r1_source_intake_result.json"
FINAL_SEAL = ROOT / "evidence" / "stage7e_final_test_seal.json"
WORKFLOW = ROOT / ".github" / "workflows" / "stage7g_b_r1_source_intake.yml"
SCRIPT = ROOT / "scripts" / "extract_stage7g_b_r1_sources.py"


class Stage7GBR1SourceIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.result = json.loads(RESULT.read_text(encoding="utf-8"))
        self.final_seal = json.loads(FINAL_SEAL.read_text(encoding="utf-8"))

    def test_source_manifest_is_pinned_licensed_and_large_enough_for_pilot(self) -> None:
        corpus = self.manifest["external_corpus"]
        self.assertEqual(self.manifest["stage"], "7G-B-R1")
        self.assertEqual(self.manifest["status"], "SOURCE_INTAKE_PENDING")
        self.assertEqual(corpus["repository"], "CoderLine/alphaTab")
        self.assertEqual(corpus["license"], "MPL-2.0")
        self.assertEqual(len(corpus["repository_commit"]), 40)
        self.assertGreaterEqual(len(corpus["paths"]), 30)
        self.assertEqual(len(corpus["paths"]), len(set(corpus["paths"])))

    def test_only_allowlisted_feature_fixtures_enter_and_known_song_content_is_excluded(self) -> None:
        corpus = self.manifest["external_corpus"]
        prefix = corpus["path_prefix"]
        allowed = set(corpus["paths"])
        excluded = set(corpus["explicitly_excluded"])
        self.assertFalse(allowed & excluded)
        self.assertTrue(all(path.startswith(prefix) and path.endswith(".gp5") for path in allowed))
        self.assertNotIn(prefix + "canon.gp5", allowed)
        self.assertNotIn(prefix + "beat-text-lyrics.gp5", allowed)
        self.assertNotIn(prefix + "serenade.gp5", allowed)

    def test_stage7e_final_source_is_quarantined(self) -> None:
        stage7g_repo = self.manifest["external_corpus"]["repository"]
        stage7e_repo = self.final_seal["external_corpus"]["repository"]
        self.assertNotEqual(stage7g_repo, stage7e_repo)
        contract = self.manifest["contract"]
        self.assertFalse(contract["stage7e_final_sources_allowed"])
        self.assertEqual(self.result["intake"]["stage7e_final_blob_overlap"], 0)

    def test_source_intake_cannot_generate_labels_fit_models_or_promote(self) -> None:
        contract = self.manifest["contract"]
        safety = self.manifest["safety"]
        result_safety = self.result["safety"]
        self.assertFalse(contract["teacher_gold_labels_generated_in_source_intake"])
        self.assertFalse(contract["specialist_scoring_in_source_intake"])
        self.assertFalse(contract["source_observed_voicing_allowed_for_sampling"])
        self.assertFalse(safety["model_fit"])
        self.assertEqual(safety["teacher_gold_labels"], 0)
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(result_safety["contains_model_metrics"])
        self.assertEqual(result_safety["teacher_gold_labels_generated"], 0)
        self.assertFalse(result_safety["checkpoint_retained"])
        self.assertFalse(result_safety["production_integration"])

    def test_partial_pool_is_reported_honestly_and_training_gate_stays_closed(self) -> None:
        intake = self.result["intake"]
        readiness = self.result["readiness"]
        self.assertEqual(self.result["status"], "PARTIAL_SOURCE_POOL")
        self.assertEqual(intake["source_file_count"], 35)
        self.assertEqual(intake["families_with_eligible_ambiguous_chords"], 8)
        self.assertEqual(intake["eligible_ambiguous_chord_events"], 417)
        self.assertEqual(intake["observed_missing_from_deterministic_candidates"], 0)
        self.assertTrue(readiness["pilot_annotation_batch_possible"])
        self.assertFalse(readiness["full_teacher_gold_training_gate_met"])
        self.assertEqual(readiness["stage7g_minimum_independent_families"], 30)
        self.assertEqual(readiness["stage7g_minimum_teacher_labeled_ambiguous_events"], 600)
        self.assertEqual(readiness["stage7g_minimum_specialist_disagreement_events"], 100)

    def test_large_fixture_cannot_be_mistaken_for_family_diversity(self) -> None:
        families = self.result["eligible_families"]
        by_path = {item["source_path"]: item["eligible_events"] for item in families}
        self.assertEqual(by_path["packages/alphatab/test-data/guitarpro5/chord-name-overflow.gp5"], 384)
        self.assertEqual(len(families), 8)
        self.assertFalse(self.result["readiness"]["full_teacher_gold_training_gate_met"])

    def test_workflow_uses_pinned_parser_and_uploads_only_derived_artifact(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("PyGuitarPro==0.10.2", text)
        self.assertIn("d9a80f4c920bb66ee0b1c7dbe797006486d04cf153c79eafb6630259fa09dac2", text)
        self.assertIn("stage7g-b-r1-source-intake.json", text)
        self.assertNotIn("/tmp/stage7g-b-r1-gp5\n", text.split("path:", 1)[-1])

    def test_extractor_reports_no_model_metrics_or_teacher_gold(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"contains_model_metrics": False', text)
        self.assertIn('"contains_teacher_gold_labels": False', text)
        self.assertIn('"source_observed_voicing_used_for_sampling": False', text)
        self.assertIn("final_blob_hashes", text)
        self.assertNotIn("train_stateless_router(", text)
        self.assertNotIn("finalize_teacher_gold_record(", text)


if __name__ == "__main__":
    unittest.main()
