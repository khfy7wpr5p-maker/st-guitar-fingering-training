from __future__ import annotations

import inspect
import unittest

from st_guitar_fingering_training.curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_LEVELS,
    STAGE7G_E3_RULE_PROPERTY_TARGETS,
)
from st_guitar_fingering_training.curriculum_generator import (
    Stage7GE3CurriculumItem,
    build_stage7g_e3_curriculum_pool,
    select_stage7g_e3_curriculum_batch,
    stage7g_e3_internal_audit,
    stage7g_e3_rule_property_records,
    stage7g_e3_teacher_manifest,
)
from st_guitar_fingering_training.teacher_gold import build_teacher_annotation_task
from st_guitar_fingering_training.teacher_task_sampling import (
    AnnotationSamplingDiagnostic,
    AnnotationSamplingEnvelope,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


def _envelope(seed: str, family_id: str, event_id: str) -> AnnotationSamplingEnvelope:
    task = build_teacher_annotation_task(
        source_sha256=seed * 64,
        source_origin=f"fixture:{family_id}",
        family_id=family_id,
        event_id=event_id,
        pitches_midi=(60, 64),
        tuning=STANDARD_TUNING,
    )
    open_low = task.candidates[0]
    compact = task.candidates[-1]
    if open_low == compact:
        raise AssertionError("fixture requires two distinct candidates")
    diagnostic = AnnotationSamplingDiagnostic(
        family_id=family_id,
        source_sha256=task.source_sha256,
        source_origin=task.source_origin,
        event_id=event_id,
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
    return AnnotationSamplingEnvelope(task=task, diagnostic=diagnostic)


def _item(seed: str, family_id: str, event_id: str, level: str) -> Stage7GE3CurriculumItem:
    envelope = _envelope(seed, family_id, event_id)
    predictions = dict(envelope.diagnostic.specialist_top1)
    return Stage7GE3CurriculumItem(
        task=envelope.task,
        curriculum_level=level,
        feature_values=tuple(0.0 for _ in STAGE7G_E3_FEATURE_NAMES),
        open_low_top1=predictions["open_low"],
        compact_top1=predictions["compact"],
    )


class Stage7GE3BCurriculumGeneratorTests(unittest.TestCase):
    def test_pool_is_target_blind_and_uses_frozen_40_feature_contract(self):
        pool = build_stage7g_e3_curriculum_pool((_envelope("1", "family_a", "event_a"),))
        self.assertEqual(len(pool), 1)
        self.assertIn(pool[0].curriculum_level, STAGE7G_E3_LEVELS)
        self.assertEqual(tuple(pool[0].feature_record), STAGE7G_E3_FEATURE_NAMES)
        self.assertEqual(len(pool[0].feature_values), 40)

        forbidden_parameters = {"teacher_response", "teacher_label", "observed_target"}
        parameters = set(inspect.signature(build_stage7g_e3_curriculum_pool).parameters)
        self.assertTrue(forbidden_parameters.isdisjoint(parameters))

    def test_pool_rejects_duplicate_event_ids(self):
        a = _envelope("1", "family_a", "duplicate")
        b = _envelope("2", "family_b", "duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate Stage 7G-E3 event_id"):
            build_stage7g_e3_curriculum_pool((a, b))

    def test_selection_requires_explicit_all_level_quotas_and_balances_families(self):
        items = (
            _item("1", "family_a", "a1", "L3"),
            _item("1", "family_a", "a2", "L3"),
            _item("2", "family_b", "b1", "L3"),
            _item("2", "family_b", "b2", "L3"),
        )
        with self.assertRaisesRegex(ValueError, "exactly L1..L4"):
            select_stage7g_e3_curriculum_batch(items, max_per_level={"L3": 2})

        selected = select_stage7g_e3_curriculum_batch(
            items,
            max_per_level={"L1": 0, "L2": 0, "L3": 2, "L4": 0},
        )
        self.assertEqual(len(selected), 2)
        self.assertEqual({item.task.family_id for item in selected}, {"family_a", "family_b"})

    def test_teacher_manifest_withholds_curriculum_and_specialist_identity(self):
        item = _item("3", "family_c", "event_c", "L1")
        manifest = stage7g_e3_teacher_manifest((item,))
        self.assertTrue(manifest["annotation_blinded"])
        self.assertEqual(manifest["choice_semantics"], "pairwise_guitaristic_preference")
        self.assertEqual(manifest["curriculum_level"], "withheld")
        self.assertEqual(manifest["specialist_identity"], "withheld")
        self.assertEqual(manifest["family_identity"], "withheld")
        task = manifest["tasks"][0]
        self.assertNotIn("family_id", task)
        self.assertNotIn("curriculum_level", task)
        self.assertNotIn("specialist", str(task).lower())
        self.assertEqual([row["option_id"] for row in task["options"]], ["A", "B"])
        self.assertEqual(task["responses"], ["A", "B", "EQUAL_OR_UNSURE"])

    def test_internal_audit_is_reproducible_but_has_no_teacher_response(self):
        pool = build_stage7g_e3_curriculum_pool((_envelope("4", "family_d", "event_d"),))
        audit = stage7g_e3_internal_audit(pool)
        self.assertFalse(audit["teacher_facing"])
        self.assertFalse(audit["teacher_response_used_for_generation"])
        self.assertEqual(audit["feature_count"], 40)
        self.assertEqual(audit["feature_names"], list(STAGE7G_E3_FEATURE_NAMES))
        self.assertNotIn("teacher_response", audit["rows"][0])
        self.assertEqual(set(audit["rows"][0]["feature_record"]), set(STAGE7G_E3_FEATURE_NAMES))

    def test_rule_property_records_are_descriptive_l1_l2_only(self):
        easy = _item("5", "family_e", "event_e", "L1")
        hard = _item("6", "family_f", "event_f", "L4")
        result = stage7g_e3_rule_property_records((easy, hard))
        self.assertFalse(result["teacher_gold"])
        self.assertEqual(result["record_count"], len(STAGE7G_E3_RULE_PROPERTY_TARGETS))
        self.assertEqual({row["event_id"] for row in result["records"]}, {"event_e"})
        self.assertEqual({row["provenance"] for row in result["records"]}, {"RULE_DERIVED_PROPERTY"})
        self.assertTrue(all(row["teacher_gold"] is False for row in result["records"]))
        self.assertNotIn("preference", result["semantic_boundary"])


if __name__ == "__main__":
    unittest.main()
