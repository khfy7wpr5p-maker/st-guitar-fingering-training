from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.stage7g_e3_d_execution import (
    STAGE7G_E3_D_EXPECTED_AUDIT_SHA256,
    STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]


class Stage7GE3EA1ManifestTests(unittest.TestCase):
    def test_manifest_is_pinned_research_only_and_label_free(self) -> None:
        manifest = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["stage"], "7G-E3-E-A1")
        self.assertEqual(manifest["status"], "SOURCE_STRUCTURE_AUDIT_PENDING")

        corpus = manifest["external_corpus"]
        self.assertEqual(corpus["repository"], "musetrainer/library")
        self.assertEqual(corpus["repository_commit"], "9128876f6164d96997c877a2be843349a32bdabb")
        self.assertEqual(len(corpus["repository_commit"]), 40)
        self.assertFalse(corpus["provenance"]["commercial_or_production_clearance"])
        self.assertEqual(
            corpus["provenance"]["research_use_status"],
            "RESEARCH_ONLY_FROM_REPOSITORY_PUBLIC_DOMAIN_CLAIM",
        )

        paths = corpus["paths"]
        self.assertGreaterEqual(len(paths), 30)
        self.assertEqual(len({row["path"] for row in paths}), len(paths))
        self.assertEqual(len({row["family_key"] for row in paths}), len(paths))
        self.assertEqual(len({row["git_blob_sha1"] for row in paths}), len(paths))
        self.assertTrue(all(row["path"].startswith("scores/") for row in paths))
        self.assertTrue(all(row["path"].endswith(".mxl") for row in paths))
        self.assertTrue(all(len(row["git_blob_sha1"]) == 40 for row in paths))
        self.assertTrue(all(int(row["bytes"]) > 0 for row in paths))

        quarantine = manifest["quarantine_inputs"]
        self.assertEqual(
            quarantine["development_package_sha256"],
            STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256,
        )
        self.assertEqual(
            quarantine["development_audit_sha256"],
            STAGE7G_E3_D_EXPECTED_AUDIT_SHA256,
        )
        self.assertEqual(quarantine["development_family_count"], 40)

        boundary = manifest["scientific_boundary"]
        self.assertFalse(boundary["teacher_gold_labels_available_to_audit"])
        self.assertFalse(boundary["teacher_gold_answers_required"])
        self.assertFalse(boundary["specialist_scoring"])
        self.assertFalse(boundary["router_scoring"])
        self.assertFalse(boundary["model_fit"])
        self.assertFalse(boundary["threshold_selection"])
        self.assertFalse(boundary["checkpoint_retained"])
        self.assertFalse(boundary["production_integration"])
        self.assertFalse(boundary["raw_external_mxl_committed_to_training_repo"])

    def test_manifest_repository_is_disjoint_from_sealed_stage7e_repository(self) -> None:
        manifest = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text(encoding="utf-8")
        )
        stage7e = json.loads(
            (ROOT / "evidence" / "stage7e_final_test_seal.json").read_text(encoding="utf-8")
        )
        self.assertNotEqual(
            manifest["external_corpus"]["repository"],
            stage7e["external_corpus"]["repository"],
        )


if __name__ == "__main__":
    unittest.main()
