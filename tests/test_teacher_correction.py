import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.teacher_correction import (
    TCV1_PROTOCOL_VERSION,
    _canonical_sha,
    build_teacher_correction_manifest,
    build_teacher_correction_task,
    filter_quarantined_tasks,
    merge_rejections_into_quarantine,
    render_teacher_correction_html,
    validate_teacher_correction_export,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def empty_quarantine():
    payload = {
        "schema": "st-guitar-teacher-correction-v1-permanent-quarantine",
        "protocol_version": TCV1_PROTOCOL_VERSION,
        "status": "ACTIVE",
        "rejected_task_ids": [],
        "rejected_task_fingerprints": [],
        "reason_counts": {},
        "source_exports": [],
        "policy": {
            "append_only": True,
            "rejected_tasks_never_training": True,
            "rejected_tasks_never_repeat": True,
            "rejected_tasks_never_metrics": True,
            "rejected_tasks_never_future_batches": True,
        },
    }
    payload["manifest_sha256"] = _canonical_sha(payload)
    return payload


class TeacherCorrectionV1Tests(unittest.TestCase):
    def _tasks(self):
        a = build_teacher_correction_task(
            event_id="event-a",
            pitches_midi=(60, 64, 67),
            tuning=STANDARD_TUNING,
        )
        b = build_teacher_correction_task(
            event_id="event-b",
            pitches_midi=(59, 62, 67),
            tuning=STANDARD_TUNING,
        )
        return a, b

    def test_task_contains_only_exact_hc_solutions_and_stable_identity(self):
        first = build_teacher_correction_task(
            event_id="event-a",
            pitches_midi=(60, 64, 67),
            tuning=STANDARD_TUNING,
        )
        second = build_teacher_correction_task(
            event_id="event-a",
            pitches_midi=(60, 64, 67),
            tuning=STANDARD_TUNING,
        )
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["solution_count"], 2)
        self.assertEqual(first["solution_count"], len(first["solutions"]))
        self.assertEqual(len({row["assignment_id"] for row in first["solutions"]}), first["solution_count"])
        self.assertIn(first["initial_assignment_id"], {row["assignment_id"] for row in first["solutions"]})

    def test_quarantine_filters_task_id_or_fingerprint_before_batch(self):
        a, b = self._tasks()
        quarantine = empty_quarantine()
        quarantine["rejected_task_ids"] = [a["task_id"]]
        quarantine["rejected_task_fingerprints"] = [b["task_fingerprint"]]
        quarantine.pop("manifest_sha256")
        quarantine["manifest_sha256"] = _canonical_sha(quarantine)
        self.assertEqual(filter_quarantined_tasks((a, b), quarantine), ())

    def test_reject_export_is_never_coerced_to_assignment_and_becomes_permanent(self):
        a, b = self._tasks()
        quarantine = empty_quarantine()
        manifest = build_teacher_correction_manifest(
            batch_id="PILOT",
            session_id="PILOT",
            tasks=(a, b),
            quarantine=quarantine,
        )
        payload = {
            "schema": "st-guitar-teacher-correction-v1-export-v1",
            "protocol_version": TCV1_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": "teacher_001",
            "decisions": [
                {
                    "task_id": a["task_id"],
                    "task_fingerprint": a["task_fingerprint"],
                    "decision": "ACCEPTED_PROPOSAL",
                    "selected_assignment_id": a["initial_assignment_id"],
                },
                {
                    "task_id": b["task_id"],
                    "task_fingerprint": b["task_fingerprint"],
                    "decision": "REJECTED_PERMANENT",
                    "selected_assignment_id": None,
                },
            ],
        }
        summary = validate_teacher_correction_export(payload, manifest)
        self.assertEqual(summary["rejected_permanent_count"], 1)
        updated = merge_rejections_into_quarantine(quarantine, payload, manifest)
        self.assertIn(b["task_id"], updated["rejected_task_ids"])
        self.assertIn(b["task_fingerprint"], updated["rejected_task_fingerprints"])
        self.assertEqual(filter_quarantined_tasks((b,), updated), ())

    def test_rejected_task_cannot_smuggle_selected_assignment(self):
        a, _ = self._tasks()
        quarantine = empty_quarantine()
        manifest = build_teacher_correction_manifest(
            batch_id="PILOT",
            session_id="PILOT",
            tasks=(a,),
            quarantine=quarantine,
        )
        payload = {
            "schema": "st-guitar-teacher-correction-v1-export-v1",
            "protocol_version": TCV1_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": "teacher_001",
            "decisions": [{
                "task_id": a["task_id"],
                "task_fingerprint": a["task_fingerprint"],
                "decision": "REJECTED_PERMANENT",
                "selected_assignment_id": a["initial_assignment_id"],
            }],
        }
        with self.assertRaises(ValueError):
            validate_teacher_correction_export(payload, manifest)

    def test_html_next_unanswered_skips_any_saved_decision_and_persists_global_reject(self):
        a, _ = self._tasks()
        quarantine = empty_quarantine()
        manifest = build_teacher_correction_manifest(
            batch_id="PILOT",
            session_id="PILOT",
            tasks=(a,),
            quarantine=quarantine,
        )
        rendered = render_teacher_correction_html(manifest)
        self.assertIn("ELE / REDDET", rendered)
        self.assertIn("if(!decisions[tasks[i].task_id])", rendered)
        self.assertIn("st_guitar_tcv1_permanent_quarantine", rendered)
        self.assertIn("REJECTED_PERMANENT", rendered)
        self.assertIn("selected_assignment_id:null", rendered)

    def test_repository_quarantine_manifest_is_canonical_and_empty_before_first_export(self):
        path = Path("evidence/teacher_correction_v1_permanent_quarantine.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored = payload.pop("manifest_sha256")
        self.assertEqual(_canonical_sha(payload), stored)
        self.assertEqual(payload["rejected_task_ids"], [])
        self.assertEqual(payload["rejected_task_fingerprints"], [])
        self.assertTrue(payload["policy"]["rejected_tasks_never_future_batches"])
        self.assertTrue(payload["policy"]["rejected_tasks_never_training"])

    def test_old_batch02_is_superseded_without_imported_labels_or_training_authority(self):
        path = Path("evidence/stage7g_e3_s2a_batch02_supersession_v1.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored = payload.pop("manifest_sha256")
        self.assertEqual(_canonical_sha(payload), stored)
        self.assertEqual(payload["status"], "SUPERSEDED_WITHOUT_IMPORTED_LABELS")
        self.assertEqual(payload["superseded_batch_id"], "S2A_BATCH02")
        self.assertEqual(payload["replacement_protocol"], "TEACHER_CORRECTION.v1")
        self.assertEqual(payload["imported_teacher_response_count"], 0)
        self.assertFalse(payload["old_batch_training_authorized"])
        self.assertFalse(payload["old_batch_repeat_authorized"])
        self.assertFalse(payload["old_batch_model_selection_authorized"])
        self.assertFalse(payload["old_batch_metrics_authorized"])


if __name__ == "__main__":
    unittest.main()
