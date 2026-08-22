from __future__ import annotations

import unittest
from unittest.mock import patch

from st_guitar_fingering_training.s2a_v3_consensus_tournament import (
    MAX_FEATURES,
    MIN_SAMPLES_LEAF,
    RANDOM_STATE,
    REPEAT_MINIMUM,
    TREE_COUNT,
    _build_model,
    consensus_quarantine_report,
    development_gate_report,
    execute_after_teacher_session,
)


class S2AV3ConsensusTournamentTests(unittest.TestCase):
    def test_model_contract_is_frozen(self):
        model = _build_model()
        params = model.get_params(deep=False)
        self.assertEqual(TREE_COUNT, 250)
        self.assertEqual(MIN_SAMPLES_LEAF, 4)
        self.assertEqual(MAX_FEATURES, "sqrt")
        self.assertEqual(RANDOM_STATE, 0)
        self.assertEqual(REPEAT_MINIMUM, 0.80)
        self.assertEqual(params["n_estimators"], 250)
        self.assertEqual(params["min_samples_leaf"], 4)
        self.assertEqual(params["max_features"], "sqrt")
        self.assertEqual(params["random_state"], 0)
        self.assertEqual(params["n_jobs"], 1)
        self.assertFalse(params["bootstrap"])

    def test_repeat_disagreement_is_quarantined_not_trainable(self):
        pairs = []
        choices = {}
        semantics = {}
        for index in range(5):
            original = f"o{index}"
            repeat = f"r{index}"
            semantic = f"s{index}"
            pairs.append({
                "original_task_id": original,
                "repeat_task_id": repeat,
                "semantic_fingerprint": semantic,
            })
            semantics[original] = semantic
            semantics[repeat] = semantic
            choices[original] = {
                "decision": "SELECT_ASSIGNMENT",
                "selected_assignment_id": f"a{index}",
            }
            choices[repeat] = {
                "decision": "SELECT_ASSIGNMENT",
                "selected_assignment_id": f"a{index}" if index < 4 else "different",
            }

        def fake_manifest_task(_manifest, task_id):
            return {"semantic_fingerprint": semantics[task_id]}

        with patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.validate_choice_export",
            return_value=choices,
        ), patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.manifest_task",
            side_effect=fake_manifest_task,
        ):
            report = consensus_quarantine_report(
                {},
                {"repeat_pairs": pairs},
                {},
            )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["stable_repeat_pairs"], 4)
        self.assertEqual(report["quarantined_repeat_pairs"], 1)
        self.assertEqual(report["quarantined_semantic_fingerprints"], ["s4"])
        self.assertFalse(report["quarantined_repeat_rows_trainable"])
        self.assertFalse(report["final_opened_during_protocol_adaptation"])

    def test_development_gate_requires_all_frozen_checks(self):
        consensus = {
            "status": "PASS",
            "quarantined_semantic_fingerprints": ["q1"],
            "quarantined_repeat_pairs": 1,
        }
        records = tuple(
            {"family_id": f"f{index % 20}"}
            for index in range(160)
        )
        cv = {
            "signature": "stable",
            "top1_accuracy": 0.65,
            "mrr": 0.78,
            "macro_family_top1": 0.66,
            "macro_family_top1_delta": 0.20,
            "family_wins": 16,
            "family_losses": 1,
        }
        with patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.consensus_quarantine_report",
            return_value=consensus,
        ), patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament._records",
            return_value=records,
        ), patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament._pair_matrix",
            return_value=(None, None, 300),
        ), patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament._cv_once",
            return_value=cv,
        ):
            report = development_gate_report({}, {}, {})

        self.assertEqual(report["status"], "PASS")
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(len(report["determinism_signatures"]), 10)

    def test_final_loader_is_never_called_when_v3_development_gate_fails(self):
        opened = []

        def final_loader():
            opened.append(True)
            return {"unexpected": True}

        with patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.fit_and_seal_development_model",
            side_effect=RuntimeError("development gate closed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "development gate closed"):
                execute_after_teacher_session(
                    manifest={},
                    internal_audit={},
                    development_export={},
                    final_loader=final_loader,
                )
        self.assertEqual(opened, [])

    def test_final_loader_runs_only_after_v3_model_seal(self):
        order = []
        model = object()
        artifact = {
            "model_sealed": True,
            "final_access_authorized": True,
            "artifact_sha256": "a" * 64,
        }
        final_result = {"status": "PASS", "result_sha256": "b" * 64}

        def fake_fit(*args, **kwargs):
            order.append("fit")
            return model, artifact

        def final_loader():
            order.append("final_loader")
            return {"schema": "fake-final"}

        def fake_eval(*args, **kwargs):
            order.append("final_eval")
            return final_result

        with patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.fit_and_seal_development_model",
            side_effect=fake_fit,
        ), patch(
            "st_guitar_fingering_training.s2a_v3_consensus_tournament.evaluate_untouched_final",
            side_effect=fake_eval,
        ):
            _, result, execution = execute_after_teacher_session(
                manifest={"manifest_sha256": "m"},
                internal_audit={},
                development_export={},
                final_loader=final_loader,
            )

        self.assertEqual(order, ["fit", "final_loader", "final_eval"])
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(execution["final_file_opened_only_after_v3_development_model_seal"])
        self.assertTrue(execution["v2_failure_preserved"])
        self.assertFalse(execution["checkpoint_retention_authorized"])
        self.assertFalse(execution["runtime_connection_authorized"])
        self.assertFalse(execution["production_authorized"])


if __name__ == "__main__":
    unittest.main()
