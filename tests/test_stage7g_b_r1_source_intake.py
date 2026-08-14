from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "stage7g_b_r1_source_intake_manifest.json"
FINAL_SEAL = ROOT / "evidence" / "stage7e_final_test_seal.json"
WORKFLOW = ROOT / ".github" / "workflows" / "stage7g_b_r1_source_intake.yml"
SCRIPT = ROOT / "scripts" / "extract_stage7g_b_r1_sources.py"


class Stage7GBR1SourceIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
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

    def test_source_intake_cannot_generate_labels_fit_models_or_promote(self) -> None:
        contract = self.manifest["contract"]
        safety = self.manifest["safety"]
        self.assertFalse(contract["teacher_gold_labels_generated_in_source_intake"])
        self.assertFalse(contract["specialist_scoring_in_source_intake"])
        self.assertFalse(contract["source_observed_voicing_allowed_for_sampling"])
        self.assertFalse(safety["model_fit"])
        self.assertEqual(safety["teacher_gold_labels"], 0)
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])

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
