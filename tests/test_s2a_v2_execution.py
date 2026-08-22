from __future__ import annotations

import unittest
from unittest.mock import patch

from st_guitar_fingering_training.s2a_v2_execution import execute_after_teacher_session


class S2AV2ExecutionTests(unittest.TestCase):
    def test_final_loader_is_not_called_when_development_gate_fails(self):
        opened = []

        def final_loader():
            opened.append(True)
            return {"unexpected": True}

        with patch(
            "st_guitar_fingering_training.s2a_v2_execution.fit_and_seal_development_model",
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

    def test_final_loader_runs_only_after_sealed_model(self):
        order = []
        model = {
            "model_sealed": True,
            "final_access_authorized": True,
            "artifact_sha256": "a" * 64,
        }
        final_result = {"status": "PASS", "result_sha256": "b" * 64}

        def final_loader():
            order.append("final_loader")
            return {"schema": "fake-final"}

        def fake_fit(*args, **kwargs):
            order.append("fit_and_seal")
            return model

        def fake_final(*args, **kwargs):
            order.append("evaluate_final")
            return final_result

        with patch(
            "st_guitar_fingering_training.s2a_v2_execution.fit_and_seal_development_model",
            side_effect=fake_fit,
        ), patch(
            "st_guitar_fingering_training.s2a_v2_execution.evaluate_untouched_final",
            side_effect=fake_final,
        ):
            _, result, execution = execute_after_teacher_session(
                manifest={"manifest_sha256": "m"},
                internal_audit={"rows": []},
                development_export={"decisions": []},
                final_loader=final_loader,
            )

        self.assertEqual(order, ["fit_and_seal", "final_loader", "evaluate_final"])
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(execution["final_file_opened_only_after_development_model_seal"])
        self.assertFalse(execution["checkpoint_retention_authorized"])
        self.assertFalse(execution["runtime_connection_authorized"])
        self.assertFalse(execution["production_authorized"])


if __name__ == "__main__":
    unittest.main()
