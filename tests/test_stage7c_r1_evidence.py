from __future__ import annotations

import json
from pathlib import Path
import unittest


class Stage7CR1EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).parents[1] / "evidence" / "stage7c_r1_real_transfer_summary.json"
        self.report = json.loads(path.read_text(encoding="utf-8"))

    def test_real_transfer_evidence_keeps_training_and_production_closed(self) -> None:
        safety = self.report["safety"]
        self.assertEqual(safety["real_training_rows"], 0)
        self.assertFalse(safety["real_model_fit"])
        self.assertFalse(safety["checkpoint_retained"])
        self.assertFalse(safety["production_integration"])
        self.assertFalse(safety["real_xml_committed_to_git"])

    def test_corpus_identity_matches_historical_stage6_boundary(self) -> None:
        corpus = self.report["corpus"]
        self.assertEqual(corpus["unique_admitted_xml"], 33)
        self.assertEqual(corpus["families"], 25)
        self.assertEqual(corpus["chord_events"], 1879)
        crosscheck = corpus["historical_stage6_chord_crosscheck"]
        self.assertEqual(crosscheck["train_raw_chord_events"] + crosscheck["validation_raw_chord_events"], 1879)
        self.assertTrue(crosscheck["matches"])

    def test_specialist_coverage_is_explicitly_non_deployable(self) -> None:
        coverage = self.report["specialist_coverage"]
        self.assertEqual(coverage["meaning"], "oracle_like_diagnostic_not_deployment_policy")
        self.assertGreater(coverage["top1_coverage"], 0.0)
        self.assertLessEqual(coverage["top1_coverage"], 1.0)

    def test_real_candidate_range_was_not_silently_clipped(self) -> None:
        audit = self.report["range_audit"]
        self.assertTrue(audit["real_candidate_range_was_not_truncated"])
        self.assertGreater(audit["candidate_set_above_synthetic_fret_12_events"], 0)


if __name__ == "__main__":
    unittest.main()
