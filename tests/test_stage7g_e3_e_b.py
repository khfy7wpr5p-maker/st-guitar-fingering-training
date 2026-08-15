from __future__ import annotations

from io import BytesIO
import unittest
from zipfile import ZipFile

from st_guitar_fingering_training.stage7g_e3_e_b import (
    E3E_B_EVALUATION_GATE,
    E3E_B_EXPECTED_DISAGREEMENT_EVENTS,
    E3E_B_EXPECTED_DISAGREEMENT_FAMILIES,
    E3E_B_TASK_QUOTA,
    E3EBValidationItem,
    e3e_internal_audit,
    e3e_response_template,
    e3e_teacher_manifest,
    e3e_teacher_package_bytes,
    select_e3e_validation_batch,
)
from st_guitar_fingering_training.teacher_gold import TeacherAnnotationTask


OPEN = ((60, 2, 5), (64, 1, 5))
COMPACT = ((60, 3, 10), (64, 2, 9))


def _pool() -> tuple[E3EBValidationItem, ...]:
    out = []
    for index in range(E3E_B_EXPECTED_DISAGREEMENT_EVENTS):
        family = f"family_{index % E3E_B_EXPECTED_DISAGREEMENT_FAMILIES:02d}"
        task_id = f"0123456789abcdef:{index // 100}:0:1:{index}"
        task = TeacherAnnotationTask(
            source_sha256=(f"{index % E3E_B_EXPECTED_DISAGREEMENT_FAMILIES + 1:064x}"),
            source_origin=f"source/{family}",
            family_id=family,
            event_id=task_id,
            pitches_midi=(60, 64),
            tuning=(64, 59, 55, 50, 45, 40),
            candidates=(OPEN, COMPACT),
        )
        out.append(E3EBValidationItem(
            task=task,
            curriculum_level=("L1", "L2", "L3", "L4")[index % 4],
            feature_values=(0.0,) * 40,
            open_low_top1=OPEN,
            compact_top1=COMPACT,
        ))
    return tuple(out)


class Stage7GE3EBTests(unittest.TestCase):
    def test_selection_is_exact_deterministic_and_covers_all_disagreement_families(self) -> None:
        pool = _pool()
        first = select_e3e_validation_batch(pool)
        second = select_e3e_validation_batch(reversed(pool))
        self.assertEqual(len(first), E3E_B_TASK_QUOTA)
        self.assertEqual(
            [item.task.event_id for item in first],
            [item.task.event_id for item in second],
        )
        self.assertEqual(
            len({item.task.family_id for item in first}),
            E3E_B_EXPECTED_DISAGREEMENT_FAMILIES,
        )

    def test_teacher_manifest_is_blind_and_response_template_has_no_answers(self) -> None:
        batch = select_e3e_validation_batch(_pool())
        manifest = e3e_teacher_manifest(batch)
        self.assertEqual(manifest["task_count"], 240)
        text = str(manifest)
        for forbidden in ("family_00", "open_low", "compact", "feature_record"):
            self.assertNotIn(forbidden, text)
        self.assertTrue(manifest["annotation_blinded"])
        self.assertEqual(manifest["family_identity"], "withheld")
        self.assertEqual(manifest["specialist_identity"], "withheld")

        template = e3e_response_template(batch)
        self.assertEqual(template["task_count"], 240)
        self.assertTrue(all(row["choice"] == "" for row in template["choices"]))

    def test_teacher_package_is_deterministic_and_contains_no_internal_audit(self) -> None:
        batch = select_e3e_validation_batch(_pool())
        first = e3e_teacher_package_bytes(batch)
        second = e3e_teacher_package_bytes(batch)
        self.assertEqual(first, second)
        with ZipFile(BytesIO(first)) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [
                    "README.txt",
                    "ST_Guitar_E3E_Teacher_UI.html",
                    "choices_template.json",
                    "teacher_manifest.json",
                ],
            )
            html = archive.read("ST_Guitar_E3E_Teacher_UI.html").decode("utf-8")
            manifest = archive.read("teacher_manifest.json").decode("utf-8")
            for sensitive in (
                '"family_id":',
                '"source_sha256":',
                '"source_origin":',
                '"blind_A_specialist":',
                '"blind_B_specialist":',
                '"feature_record":',
            ):
                self.assertNotIn(sensitive, html)
                self.assertNotIn(sensitive, manifest)
            self.assertNotIn("internal_audit", archive.namelist())

    def test_internal_audit_keeps_mapping_separate_and_gate_is_frozen(self) -> None:
        batch = select_e3e_validation_batch(_pool())
        audit = e3e_internal_audit(batch)
        self.assertFalse(audit["teacher_facing"])
        self.assertEqual(audit["selected_events"], 240)
        self.assertEqual(audit["selected_families"], 24)
        self.assertEqual(sum(audit["family_counts"].values()), 240)
        self.assertEqual(sum(audit["level_counts"].values()), 240)
        self.assertEqual(audit["evaluation_gate"], E3E_B_EVALUATION_GATE)
        self.assertEqual(E3E_B_EVALUATION_GATE["compact_probability_threshold"], 0.5)
        self.assertFalse(E3E_B_EVALUATION_GATE["threshold_search_on_e3e"])
        self.assertEqual(
            E3E_B_EVALUATION_GATE["pass_requirements"]["compact_precision_gte"],
            2.0 / 3.0,
        )

    def test_wrong_pool_size_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            select_e3e_validation_batch(_pool()[:-1])


if __name__ == "__main__":
    unittest.main()
