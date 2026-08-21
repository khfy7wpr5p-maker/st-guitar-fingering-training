from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_voicing_development import verify_sealed_json
from st_guitar_fingering_training.guitarset_voicing_final import (
    EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
    EXPECTED_VALIDATION_EVIDENCE_SHA256,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
)


class GuitarSetVoicingFinalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.evidence = json.loads(
            (root / "evidence/stage7g_e3_guitarset_observed_voicing_final_v1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_final_evidence_is_sealed_pass(self):
        verify_sealed_json(self.evidence, "evidence_sha256")
        self.assertEqual(
            self.evidence["evidence_sha256"],
            "c883fbbe076ea1bc098357cd70aca592a3a95a7fedf0174cab2bdf95dcb4e57e",
        )
        self.assertEqual(
            self.evidence["status"],
            "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY",
        )
        self.assertTrue(self.evidence["final_pass"])
        self.assertTrue(self.evidence["untouched_final_performer_opened"])
        self.assertEqual(self.evidence["untouched_final_performer"], "02")
        self.assertTrue(all(item["pass"] for item in self.evidence["gate"].values()))

    def test_final_identity_and_source_counts_are_exact(self):
        self.assertEqual(self.evidence["source_archive_sha256"], GUITARSET_SOURCE_ARCHIVE_SHA256)
        self.assertEqual(self.evidence["prereg_protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(self.evidence["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(
            self.evidence["accepted_validation_evidence_sha256"],
            EXPECTED_VALIDATION_EVIDENCE_SHA256,
        )
        self.assertEqual(
            self.evidence["sealed_development_model_artifact_sha256"],
            EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
        )
        counts = self.evidence["final_source_counts"]
        self.assertEqual(counts["recordings"], 30)
        self.assertEqual(counts["accepted_notes"], 7194)
        self.assertEqual(counts["quarantined_notes"], 33)
        self.assertEqual(counts["derived_voicings"], 2210)
        self.assertEqual(counts["ambiguous_voicings"], 1816)
        self.assertEqual(counts["single_candidate_voicings"], 394)

    def test_final_pass_is_not_checkpoint_or_runtime_authority(self):
        self.assertTrue(self.evidence["checkpoint_retention_review_eligible"])
        self.assertFalse(self.evidence["checkpoint_authorized"])
        self.assertFalse(self.evidence["runtime_connection_authorized"])
        self.assertFalse(self.evidence["production_authorized"])
        self.assertFalse(self.evidence["model_refit_performed"])
        self.assertFalse(self.evidence["hyperparameter_tuning_performed"])
        self.assertEqual(self.evidence["next_gate"], "CHECKPOINT_RETENTION_REVIEW")

    def test_final_metrics_clear_every_frozen_gate(self):
        metrics = self.evidence["metrics"]
        self.assertGreater(metrics["event_top1_delta"], 0.0)
        self.assertGreater(metrics["event_mrr_delta"], 0.0)
        self.assertGreater(metrics["recording_macro_top1_delta"], 0.0)
        self.assertGreater(metrics["recording_macro_mrr_delta"], 0.0)
        bootstrap = self.evidence["recording_block_bootstrap"]
        self.assertEqual(bootstrap["repetitions"], 2000)
        self.assertEqual(bootstrap["seed"], 0)
        self.assertEqual(bootstrap["lower_order_statistic_index_zero_based"], 49)
        self.assertEqual(bootstrap["upper_order_statistic_index_zero_based"], 1949)
        self.assertGreater(bootstrap["lower_bound"], 0.0)


if __name__ == "__main__":
    unittest.main()
