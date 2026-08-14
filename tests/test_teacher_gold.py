from __future__ import annotations

from dataclasses import fields, replace
import unittest

from st_guitar_fingering_training.teacher_gold import (
    STATELESS_SPECIALISTS,
    STAGE7G_MINIMUM_INDEPENDENT_FAMILIES,
    STAGE7G_MINIMUM_SPECIALIST_DISAGREEMENT_EVENTS,
    STAGE7G_MINIMUM_TEACHER_LABELED_AMBIGUOUS_EVENTS,
    TeacherGoldRecord,
    build_teacher_annotation_task,
    finalize_teacher_gold_record,
    is_specialist_disagreement,
    validate_teacher_gold_corpus,
    validate_teacher_gold_record,
)


TUNING = (64, 59, 55, 50, 45, 40)
SOURCE_HASH = "a" * 64


class TeacherGoldContractTests(unittest.TestCase):
    def make_task(self, *, family_id: str = "family-1", event_id: str = "event-1"):
        return build_teacher_annotation_task(
            source_sha256=SOURCE_HASH,
            source_origin=f"teacher-source:{family_id}",
            family_id=family_id,
            event_id=event_id,
            pitches_midi=(48, 52, 55),
            tuning=TUNING,
        )

    def specialist_predictions(self, task, *, disagreement: bool = False):
        predictions = {style: task.candidates[0] for style in STATELESS_SPECIALISTS}
        if disagreement:
            predictions["compact"] = task.candidates[1]
        return predictions

    def make_record(self, *, disagreement: bool = False):
        task = self.make_task()
        return finalize_teacher_gold_record(
            task,
            teacher_preferred=task.candidates[0],
            annotator_id="teacher-001",
            specialist_top1=self.specialist_predictions(task, disagreement=disagreement),
        )

    def test_annotation_task_is_target_and_specialist_blind_with_full_physical_candidates(self) -> None:
        task = self.make_task()
        names = {field.name for field in fields(task)}
        self.assertNotIn("observed", names)
        self.assertNotIn("teacher_preferred", names)
        self.assertNotIn("specialist_top1", names)
        self.assertGreaterEqual(len(task.candidates), 2)

    def test_teacher_gold_record_requires_physical_teacher_choice_and_exact_stateless_specialists(self) -> None:
        record = self.make_record(disagreement=True)
        validate_teacher_gold_record(record)
        self.assertTrue(record.annotation_blinded_to_specialists)
        self.assertEqual(record.label_semantics, "TEACHER_GOLD")
        self.assertEqual({style for style, _ in record.specialist_top1}, set(STATELESS_SPECIALISTS))
        self.assertTrue(is_specialist_disagreement(record))

        bad = replace(record, teacher_preferred=((127, 1, 63),))
        with self.assertRaisesRegex(ValueError, "teacher-preferred voicing"):
            validate_teacher_gold_record(bad)

    def test_finalize_fails_closed_on_extra_or_missing_specialist_keys(self) -> None:
        task = self.make_task()
        extra = self.specialist_predictions(task)
        extra["common_tone"] = task.candidates[0]
        with self.assertRaisesRegex(ValueError, "exactly the four stateless specialists"):
            finalize_teacher_gold_record(
                task,
                teacher_preferred=task.candidates[0],
                annotator_id="teacher-001",
                specialist_top1=extra,
            )

        missing = self.specialist_predictions(task)
        missing.pop("high_position")
        with self.assertRaisesRegex(ValueError, "exactly the four stateless specialists"):
            finalize_teacher_gold_record(
                task,
                teacher_preferred=task.candidates[0],
                annotator_id="teacher-001",
                specialist_top1=missing,
            )

    def test_final_test_hash_and_origin_are_quarantined(self) -> None:
        record = self.make_record()
        with self.assertRaisesRegex(ValueError, "source hash overlaps"):
            validate_teacher_gold_corpus([record], forbidden_source_hashes=[SOURCE_HASH])
        with self.assertRaisesRegex(ValueError, "source origin overlaps"):
            validate_teacher_gold_corpus([record], forbidden_source_origins=[record.source_origin])

    def test_corpus_rejects_duplicate_event_ids_and_counts_disagreement(self) -> None:
        record = self.make_record(disagreement=True)
        summary = validate_teacher_gold_corpus([record])
        self.assertEqual(summary.independent_families, 1)
        self.assertEqual(summary.teacher_labeled_ambiguous_events, 1)
        self.assertEqual(summary.specialist_disagreement_events, 1)
        self.assertFalse(summary.stage7g_minimums_met)
        with self.assertRaisesRegex(ValueError, "duplicate Teacher-GOLD event_id"):
            validate_teacher_gold_corpus([record, record])

    def test_stage7g_minimums_are_fixed_and_enforced_before_training_gate(self) -> None:
        self.assertEqual(STAGE7G_MINIMUM_INDEPENDENT_FAMILIES, 30)
        self.assertEqual(STAGE7G_MINIMUM_TEACHER_LABELED_AMBIGUOUS_EVENTS, 600)
        self.assertEqual(STAGE7G_MINIMUM_SPECIALIST_DISAGREEMENT_EVENTS, 100)
        with self.assertRaisesRegex(ValueError, "Stage 7G corpus minimums not met"):
            validate_teacher_gold_corpus([self.make_record()], require_stage7g_minimums=True)

    def test_non_blind_or_observed_behavior_semantics_cannot_be_teacher_gold(self) -> None:
        record = self.make_record()
        with self.assertRaisesRegex(ValueError, "blind to specialist"):
            validate_teacher_gold_record(replace(record, annotation_blinded_to_specialists=False))
        with self.assertRaisesRegex(ValueError, "TEACHER_GOLD"):
            validate_teacher_gold_record(replace(record, label_semantics="OBSERVED_BEHAVIOR"))


if __name__ == "__main__":
    unittest.main()
