from __future__ import annotations

import json
import unittest

from st_guitar_fingering_training.teacher_gold import build_teacher_annotation_task
from st_guitar_fingering_training.teacher_pairwise import (
    PAIRWISE_CHOICE_SCHEMA,
    build_pairwise_teacher_manifests,
    validate_pairwise_choice_export,
)
from st_guitar_fingering_training.teacher_task_sampling import (
    AnnotationSamplingDiagnostic,
    TeacherAnnotationBatch,
)


TUNING = (64, 59, 55, 50, 45, 40)


def _batch() -> TeacherAnnotationBatch:
    task_a = build_teacher_annotation_task(
        source_sha256="a" * 64,
        source_origin="hidden/source-a",
        family_id="family-a",
        event_id="aaaaaaaaaaaaaaaa:1:0:1:0",
        pitches_midi=(55, 60),
        tuning=TUNING,
    )
    task_b = build_teacher_annotation_task(
        source_sha256="b" * 64,
        source_origin="hidden/source-b",
        family_id="family-b",
        event_id="bbbbbbbbbbbbbbbb:2:0:1:0",
        pitches_midi=(57, 62),
        tuning=TUNING,
    )

    def diagnostic(task, source_sha, origin, family):
        open_low = task.candidates[0]
        compact = task.candidates[-1]
        return AnnotationSamplingDiagnostic(
            family_id=family,
            source_sha256=source_sha,
            source_origin=origin,
            event_id=task.event_id,
            candidate_count=len(task.candidates),
            open_low_compact_disagreement=True,
            any_specialist_disagreement=True,
            specialist_top1=(
                ("open_low", open_low),
                ("compact", compact),
                ("mid_position", open_low),
                ("high_position", compact),
            ),
        )

    diag_a = diagnostic(task_a, "a" * 64, "hidden/source-a", "family-a")
    diag_b = diagnostic(task_b, "b" * 64, "hidden/source-b", "family-b")
    return TeacherAnnotationBatch(
        tasks=(task_a, task_b),
        diagnostics=(diag_a, diag_b),
        eligible_events=2,
        eligible_families=2,
        selected_families=2,
        open_low_compact_disagreement_selected=2,
        any_specialist_disagreement_selected=2,
    )


class TeacherPairwiseTests(unittest.TestCase):
    def test_teacher_manifest_shows_only_two_blind_physical_options(self):
        teacher, audit = build_pairwise_teacher_manifests(_batch())
        self.assertEqual(teacher["task_count"], 2)
        self.assertTrue(teacher["annotation_blinded"])
        self.assertEqual(teacher["allowed_responses"], ["A", "B", "EQUAL_OR_UNSURE"])
        self.assertTrue(all(len(row["options"]) == 2 for row in teacher["tasks"]))
        serialized = json.dumps(teacher, sort_keys=True)
        self.assertNotIn("open_low", serialized)
        self.assertNotIn("compact", serialized)
        self.assertNotIn("hidden/source", serialized)
        self.assertIn("open_low", json.dumps(audit, sort_keys=True))
        self.assertIn("compact", json.dumps(audit, sort_keys=True))
        self.assertFalse(audit["target_voicing_used_for_pair_construction"])
        self.assertFalse(audit["observed_string_fret_used_for_pair_construction"])

    def test_completed_full_candidate_choices_are_excluded_without_reselection(self):
        batch = _batch()
        completed = {batch.tasks[0].event_id}
        teacher, audit = build_pairwise_teacher_manifests(batch, completed_task_ids=completed)
        self.assertEqual(teacher["task_count"], 1)
        self.assertEqual(audit["completed_full_candidate_tasks_excluded"], 1)
        self.assertEqual(teacher["tasks"][0]["task_id"], batch.tasks[1].event_id)
        with self.assertRaisesRegex(ValueError, "outside the sealed batch"):
            build_pairwise_teacher_manifests(batch, completed_task_ids={"not-a-real-task"})

    def test_pairwise_export_accepts_a_b_or_unsure_and_rejects_duplicates(self):
        teacher, _ = build_pairwise_teacher_manifests(_batch())
        task_ids = [row["task_id"] for row in teacher["tasks"]]
        payload = {
            "schema": PAIRWISE_CHOICE_SCHEMA,
            "annotation_blinded": True,
            "annotator_id": "teacher_001",
            "choices": [
                {"task_id": task_ids[0], "response": "A"},
                {"task_id": task_ids[1], "response": "EQUAL_OR_UNSURE"},
            ],
        }
        self.assertEqual(len(validate_pairwise_choice_export(payload, teacher)), 2)
        payload["choices"].append({"task_id": task_ids[0], "response": "B"})
        with self.assertRaisesRegex(ValueError, "duplicate task_id"):
            validate_pairwise_choice_export(payload, teacher)


if __name__ == "__main__":
    unittest.main()
