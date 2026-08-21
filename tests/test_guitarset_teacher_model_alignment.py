from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_teacher_model_alignment import (
    ALIGNMENT_SCHEMA,
    analyze_teacher_model_alignment,
)
from st_guitar_fingering_training.guitarset_teacher_voicing import (
    DECISION_SELECT_OPTION,
    TEACHER_VOICING_AUDIT_SCHEMA,
    TEACHER_VOICING_EXPORT_SCHEMA,
    TEACHER_VOICING_PILOT_VERSION,
    build_teacher_voicing_manifest,
    candidate_id,
)
from st_guitar_fingering_training.guitarset_teacher_voicing_blind import (
    build_complete_blinded_teacher_voicing_task,
)


OBSERVED = ((43, 6, 3), (50, 4, 0))


def _fixture():
    task, row_audit = build_complete_blinded_teacher_voicing_task(
        event_id="alignment-regression-event",
        pitches_midi=(43, 50),
        observed_placements=OBSERVED,
        option_cap=6,
    )
    manifest = build_teacher_voicing_manifest(
        batch_id="ALIGNMENT_TEST",
        session_id="alignment-test",
        tasks=[task],
    )
    audit = {
        "schema": TEACHER_VOICING_AUDIT_SCHEMA,
        "protocol_version": TEACHER_VOICING_PILOT_VERSION,
        "source_role": "DEVELOPMENT_ONLY",
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "rows": [row_audit],
        "validation_performer_opened": False,
        "untouched_final_performer_opened": False,
        "training_authorized": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    observed_id = candidate_id(OBSERVED)
    choices = {
        "schema": TEACHER_VOICING_EXPORT_SCHEMA,
        "protocol_version": TEACHER_VOICING_PILOT_VERSION,
        "manifest_sha256": manifest["manifest_sha256"],
        "annotator_id": manifest["annotator_id"],
        "decisions": [
            {
                "task_id": task["task_id"],
                "semantic_fingerprint": task["semantic_fingerprint"],
                "selected_candidate_id": observed_id,
                "manual_voicing": None,
                "decision": DECISION_SELECT_OPTION,
            }
        ],
    }
    root = Path(__file__).parents[1]
    model = json.loads(
        (root / "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json").read_text(
            encoding="utf-8"
        )
    )
    return task, manifest, audit, choices, model


class GuitarSetTeacherModelAlignmentTests(unittest.TestCase):
    def test_sealed_model_alignment_regression_is_diagnostic_and_nonpromoting(self):
        task, manifest, audit, choices, model = _fixture()
        report = analyze_teacher_model_alignment(
            choices=choices,
            choices_sha256="0" * 64,
            manifest=manifest,
            internal_audit=audit,
            model_artifact=model,
        )
        self.assertEqual(report["schema"], ALIGNMENT_SCHEMA)
        self.assertEqual(report["task_count"], 1)
        self.assertEqual(report["decisive_teacher_task_count"], 1)
        self.assertEqual(report["agreement"]["teacher_vs_observed_guitarist"]["exact"], 1)
        self.assertEqual(report["agreement"]["model_vs_observed_guitarist"]["exact"], 0)
        self.assertEqual(report["agreement"]["model_vs_teacher"]["exact"], 0)
        self.assertEqual(report["agreement"]["baseline_vs_observed_guitarist"]["exact"], 1)
        self.assertEqual(report["triple_agreement_counts"]["teacher_observed_same_model_diff"], 1)
        self.assertTrue(report["interpretation_guard"]["model_vs_observed_is_in_sample"])
        self.assertFalse(report["interpretation_guard"]["independent_model_validation_claim_authorized"])
        self.assertFalse(report["raw_teacher_choices_embedded"])
        self.assertFalse(report["raw_task_ids_embedded"])
        self.assertFalse(report["validation_performer_opened_by_this_analysis"])
        self.assertFalse(report["untouched_final_performer_opened_by_this_analysis"])
        self.assertFalse(report["checkpoint_authorized"])
        self.assertFalse(report["runtime_connection_authorized"])
        self.assertFalse(report["final_access_authorized"])
        self.assertNotIn(task["task_id"], json.dumps(report, sort_keys=True))

    def test_tampered_sealed_model_fails_closed(self):
        _, manifest, audit, choices, model = _fixture()
        tampered = copy.deepcopy(model)
        tampered["parameters"]["logistic_coef_hex"][0] = "0x0.0p+0"
        with self.assertRaisesRegex(ValueError, "sealed JSON SHA-256 mismatch"):
            analyze_teacher_model_alignment(
                choices=choices,
                choices_sha256="1" * 64,
                manifest=manifest,
                internal_audit=audit,
                model_artifact=tampered,
            )

    def test_final_access_or_validation_opening_is_rejected(self):
        _, manifest, audit, choices, model = _fixture()
        manifest_open = copy.deepcopy(manifest)
        manifest_open["final_access_authorized"] = True
        with self.assertRaisesRegex(ValueError, "final_access_authorized=false"):
            analyze_teacher_model_alignment(
                choices=choices,
                choices_sha256="2" * 64,
                manifest=manifest_open,
                internal_audit=audit,
                model_artifact=model,
            )

        audit_open = copy.deepcopy(audit)
        audit_open["validation_performer_opened"] = True
        with self.assertRaisesRegex(ValueError, "must not open validation performer"):
            analyze_teacher_model_alignment(
                choices=choices,
                choices_sha256="3" * 64,
                manifest=manifest,
                internal_audit=audit_open,
                model_artifact=model,
            )

    def test_partial_candidate_display_is_rejected(self):
        _, manifest, audit, choices, model = _fixture()
        partial = copy.deepcopy(manifest)
        partial["tasks"][0]["options"] = partial["tasks"][0]["options"][:1]
        partial["tasks"][0]["option_count"] = 1
        selected = partial["tasks"][0]["options"][0]["candidate_id"]
        choices_partial = copy.deepcopy(choices)
        choices_partial["decisions"][0]["selected_candidate_id"] = selected
        with self.assertRaisesRegex(ValueError, "partial candidate display"):
            analyze_teacher_model_alignment(
                choices=choices_partial,
                choices_sha256="4" * 64,
                manifest=partial,
                internal_audit=audit,
                model_artifact=model,
            )

    def test_choices_hash_requires_lowercase_sha256_hex(self):
        _, manifest, audit, choices, model = _fixture()
        with self.assertRaisesRegex(ValueError, "lowercase"):
            analyze_teacher_model_alignment(
                choices=choices,
                choices_sha256="A" * 64,
                manifest=manifest,
                internal_audit=audit,
                model_artifact=model,
            )


if __name__ == "__main__":
    unittest.main()
