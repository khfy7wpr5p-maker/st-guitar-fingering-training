from __future__ import annotations

import unittest

import numpy as np

from st_guitar_fingering_training.finger_assignments import generate_standard_fingerings
from st_guitar_fingering_training.s2a_ranker import (
    build_s2a_corpus,
    build_s2a_pairwise_training_matrix,
    build_s2a_ranker_model,
    development_cv_report,
    fit_s2a_ranker,
    rank_s2a_assignments,
    s2a_fit_gate_report,
)
from st_guitar_fingering_training.s2a_teacher import (
    S2A_CHOICE_EXPORT_SCHEMA,
    S2A_FIRST_PASS_PROVENANCE,
    build_s2a_teacher_package,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)
PITCHES = (55, 60, 64)


class S2ARankerHarnessTests(unittest.TestCase):
    def _tiny_corpus(self):
        manifest, audit = build_s2a_teacher_package(
            family_id="fresh-family-001",
            event_id="fresh-event-001",
            pitches_midi=PITCHES,
            tuning=STANDARD_TUNING,
            provenance=S2A_FIRST_PASS_PROVENANCE,
        )
        payload = {
            "schema": S2A_CHOICE_EXPORT_SCHEMA,
            "annotation_blinded": True,
            "provenance": S2A_FIRST_PASS_PROVENANCE,
            "annotator_id": "teacher-1",
            "collected_at_utc": "2026-08-19T12:00:00Z",
            "choices": [
                {"task_id": task["task_id"], "response": "A"}
                for task in manifest["tasks"]
            ],
        }
        return build_s2a_corpus(
            ((manifest, audit, payload),),
            expected_provenance=S2A_FIRST_PASS_PROVENANCE,
        )

    def test_corpus_recomputes_hc_lineage_and_pair_matrix_is_exactly_mirrored(self):
        corpus = self._tiny_corpus()
        self.assertGreater(len(corpus.rows), 0)
        self.assertEqual(corpus.equal_or_unsure_count, 0)

        X, y = build_s2a_pairwise_training_matrix(corpus.rows)
        self.assertEqual(X.shape, (2 * len(corpus.rows), 30))
        self.assertEqual(set(y.tolist()), {0, 1})
        for index in range(0, len(X), 2):
            np.testing.assert_array_equal(X[index], -X[index + 1])
            self.assertEqual(y[index], 1 - y[index + 1])

    def test_model_family_matches_frozen_no_intercept_contract(self):
        model = build_s2a_ranker_model()
        self.assertEqual(model.penalty, "l2")
        self.assertEqual(model.C, 1.0)
        self.assertFalse(model.fit_intercept)
        self.assertIsNone(model.class_weight)
        self.assertEqual(model.solver, "lbfgs")
        self.assertEqual(model.max_iter, 2000)
        self.assertEqual(model.random_state, 0)

    def test_tiny_or_forged_evidence_cannot_open_real_fit_or_cv(self):
        corpus = self._tiny_corpus()
        forged = {
            "repeat_tasks": 10000,
            "three_class_exact_agreement": 1.0,
            "decisive_cohen_kappa": 1.0,
            "repeat_interval_24_to_72h": True,
            "presentation_reversal_exactly_50_percent": True,
            "old_answers_included": False,
            "status": "PASS",
        }
        gate = s2a_fit_gate_report(corpus, forged)
        self.assertEqual(gate["status"], "FAIL")
        self.assertFalse(gate["checks"]["development_families_gte_40"])
        self.assertFalse(gate["checks"]["decisive_first_pass_pairs_gte_600"])

        with self.assertRaises(RuntimeError):
            fit_s2a_ranker(corpus, forged)
        with self.assertRaises(RuntimeError):
            development_cv_report(corpus, forged)

    def test_trained_test_model_can_only_rank_exact_hc_assignment_set(self):
        corpus = self._tiny_corpus()
        X, y = build_s2a_pairwise_training_matrix(corpus.rows)
        model = build_s2a_ranker_model()
        model.fit(X, y)

        ranked = rank_s2a_assignments(model, PITCHES, STANDARD_TUNING)
        generated = generate_standard_fingerings(PITCHES, STANDARD_TUNING)
        expected_ids = {
            assignment.assignment_id
            for candidate in generated.candidates
            for assignment in candidate.assignments
        }
        self.assertEqual({row["assignment_id"] for row in ranked}, expected_ids)
        self.assertEqual(len(ranked), len(expected_ids))
        self.assertEqual(
            [row["score"] for row in ranked],
            sorted((row["score"] for row in ranked), reverse=True),
        )


if __name__ == "__main__":
    unittest.main()
