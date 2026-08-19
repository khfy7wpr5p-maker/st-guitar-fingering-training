from __future__ import annotations

import unittest

from st_guitar_fingering_training.s2a_teacher import (
    S2A_CHOICE_EXPORT_SCHEMA,
    S2A_FIRST_PASS_PROVENANCE,
    S2A_REPEAT_PROVENANCE,
    build_s2a_repeat_package,
    build_s2a_teacher_package,
    evaluate_s2a_repeat_reliability,
    validate_s2a_choice_export,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)
PITCHES = (55, 60, 64)


def _response_for_assignment(task: dict, assignment_id: str) -> str:
    for option in task["options"]:
        if option["assignment_id"] == assignment_id:
            return option["option_id"]
    raise AssertionError("assignment not present in task")


class S2ATeacherPackageTests(unittest.TestCase):
    def _first_package(self):
        return build_s2a_teacher_package(
            family_id="family-new-001",
            event_id="event-new-001",
            pitches_midi=PITCHES,
            tuning=STANDARD_TUNING,
            provenance=S2A_FIRST_PASS_PROVENANCE,
        )

    def test_pair_package_is_blind_bounded_and_deterministic(self):
        manifest, audit = self._first_package()
        self.assertGreaterEqual(manifest["task_count"], 2)
        self.assertLessEqual(manifest["task_count"], 6)
        self.assertEqual(manifest["task_count"], audit["task_count"])
        self.assertEqual(manifest["source_identity"], "withheld")
        self.assertEqual(manifest["family_identity"], "withheld")
        self.assertEqual(manifest["feature_values"], "withheld")
        self.assertNotIn("family-new-001", str(manifest))

        task_ids = {row["task_id"] for row in manifest["tasks"]}
        self.assertEqual(task_ids, {row["task_id"] for row in audit["rows"]})
        for row in audit["rows"]:
            self.assertIn(row["pair_type"], ("FINGER_ONLY", "MIXED"))
            self.assertIn(row["distance_stratum"], ("NEAR", "MID", "FAR"))
            self.assertEqual(len(row["A_features"]), 30)
            self.assertEqual(len(row["B_features"]), 30)

        expected = (manifest, audit)
        for _ in range(10):
            self.assertEqual(self._first_package(), expected)

    def test_choice_export_requires_exact_provenance_complete_manifest_and_utc(self):
        manifest, _ = self._first_package()
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
        validated = validate_s2a_choice_export(payload, manifest)
        self.assertEqual(set(validated), {task["task_id"] for task in manifest["tasks"]})

        wrong = dict(payload)
        wrong["provenance"] = S2A_REPEAT_PROVENANCE
        with self.assertRaises(ValueError):
            validate_s2a_choice_export(wrong, manifest)

        partial = dict(payload)
        partial["choices"] = payload["choices"][:-1]
        with self.assertRaises(ValueError):
            validate_s2a_choice_export(partial, manifest)

    def test_repeat_package_reverses_exactly_half_and_semantic_agreement_passes(self):
        first_manifest, first_audit = self._first_package()
        repeat_manifest, repeat_audit = build_s2a_repeat_package(
            first_manifest,
            first_audit,
            repeat_count=2,
        )
        self.assertEqual(repeat_manifest["provenance"], S2A_REPEAT_PROVENANCE)
        self.assertEqual(repeat_audit["reversed_count"], 1)
        self.assertFalse(repeat_audit["old_answers_included"])

        first_task_by_id = {task["task_id"]: task for task in first_manifest["tasks"]}
        first_audit_by_id = {row["task_id"]: row for row in first_audit["rows"]}
        repeated_first_ids = {row["first_task_id"] for row in repeat_audit["rows"]}

        first_choices = []
        chosen_by_first_task = {}
        for index, task in enumerate(first_manifest["tasks"]):
            row = first_audit_by_id[task["task_id"]]
            canonical = sorted((row["A_assignment_id"], row["B_assignment_id"]))
            target_assignment = canonical[index % 2]
            response = _response_for_assignment(task, target_assignment)
            first_choices.append({"task_id": task["task_id"], "response": response})
            chosen_by_first_task[task["task_id"]] = target_assignment

        repeat_task_by_id = {task["task_id"]: task for task in repeat_manifest["tasks"]}
        repeat_choices = []
        for row in repeat_audit["rows"]:
            repeat_task = repeat_task_by_id[row["repeat_task_id"]]
            target_assignment = chosen_by_first_task[row["first_task_id"]]
            response = _response_for_assignment(repeat_task, target_assignment)
            repeat_choices.append({"task_id": repeat_task["task_id"], "response": response})

        first_payload = {
            "schema": S2A_CHOICE_EXPORT_SCHEMA,
            "annotation_blinded": True,
            "provenance": S2A_FIRST_PASS_PROVENANCE,
            "annotator_id": "teacher-1",
            "collected_at_utc": "2026-08-19T12:00:00Z",
            "choices": first_choices,
        }
        repeat_payload = {
            "schema": S2A_CHOICE_EXPORT_SCHEMA,
            "annotation_blinded": True,
            "provenance": S2A_REPEAT_PROVENANCE,
            "annotator_id": "teacher-1",
            "collected_at_utc": "2026-08-21T12:00:00Z",
            "choices": repeat_choices,
        }
        report = evaluate_s2a_repeat_reliability(
            first_manifest,
            first_payload,
            repeat_manifest,
            repeat_audit,
            repeat_payload,
        )
        self.assertEqual(report["three_class_exact_agreement"], 1.0)
        self.assertEqual(report["repeat_interval_hours"], 48.0)
        self.assertTrue(report["presentation_reversal_exactly_50_percent"])
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(repeated_first_ids, {row["first_task_id"] for row in repeat_audit["rows"]})


if __name__ == "__main__":
    unittest.main()
