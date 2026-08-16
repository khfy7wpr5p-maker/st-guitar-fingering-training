from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.stage7g_e3_s0c_repeat_reliability import (
    EXPECTED_SOURCE_MANIFEST_SHA256,
    S0C_CONFIG,
    S0C_CHOICE_EXPORT_SCHEMA,
    S0C_TEACHER_MANIFEST_SCHEMA,
    build_s0c_repeat_package,
    extract_source_teacher_manifest_from_html,
    render_s0c_repeat_annotator_html,
    score_s0c_repeat_choices,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads(
    (ROOT / "evidence/stage7g_e3_s0c_teacher_repeat_reliability_protocol.json").read_text(
        encoding="utf-8"
    )
)


def _synthetic_inputs() -> tuple[dict, dict]:
    quotas = {
        ("L1", "open_low"): 6,
        ("L1", "compact"): 6,
        ("L2", "open_low"): 9,
        ("L2", "compact"): 9,
        ("L3", "open_low"): 7,
        ("L3", "compact"): 7,
        ("L4", "open_low"): 8,
        ("L4", "compact"): 8,
    }
    rows = []
    task_rows = []
    index = 0

    # First create well-distributed candidates for every frozen quota.
    for (level, pref), count in quotas.items():
        for local in range(count + 5):
            family = f"family-{(index + local) % 40:02d}"
            task_id = f"task-{index:04d}"
            response = "A" if index % 2 == 0 else "B"
            rows.append({
                "task_id": task_id,
                "curriculum_level": level,
                "family_id": family,
                "blind_response": response,
                "teacher_preference": pref,
            })
            task_rows.append({
                "task_id": task_id,
                "pitches_midi": [48, 60],
                "tuning": [64, 59, 55, 50, 45, 40],
                "options": [
                    {"option_id": "A", "placements": [
                        {"pitch_midi": 48, "string": 5, "fret": 3},
                        {"pitch_midi": 60, "string": 2, "fret": 1},
                    ]},
                    {"option_id": "B", "placements": [
                        {"pitch_midi": 48, "string": 6, "fret": 8},
                        {"pitch_midi": 60, "string": 3, "fret": 5},
                    ]},
                ],
                "responses": ["A", "B", "EQUAL_OR_UNSURE"],
            })
            index += 1

    # Fill to the exact historical semantic totals: 311 OPEN_LOW, 88 COMPACT, 1 equal.
    current_open = sum(row["teacher_preference"] == "open_low" for row in rows)
    current_compact = sum(row["teacher_preference"] == "compact" for row in rows)
    levels = ("L1", "L2", "L3", "L4")
    while current_open < 311:
        task_id = f"task-{index:04d}"
        rows.append({
            "task_id": task_id,
            "curriculum_level": levels[index % 4],
            "family_id": f"family-{index % 40:02d}",
            "blind_response": "A" if index % 2 == 0 else "B",
            "teacher_preference": "open_low",
        })
        task_rows.append({
            "task_id": task_id,
            "pitches_midi": [50, 62],
            "tuning": [64, 59, 55, 50, 45, 40],
            "options": [
                {"option_id": "A", "placements": [
                    {"pitch_midi": 50, "string": 4, "fret": 0},
                    {"pitch_midi": 62, "string": 2, "fret": 3},
                ]},
                {"option_id": "B", "placements": [
                    {"pitch_midi": 50, "string": 5, "fret": 5},
                    {"pitch_midi": 62, "string": 3, "fret": 7},
                ]},
            ],
            "responses": ["A", "B", "EQUAL_OR_UNSURE"],
        })
        current_open += 1
        index += 1
    while current_compact < 88:
        task_id = f"task-{index:04d}"
        rows.append({
            "task_id": task_id,
            "curriculum_level": levels[index % 4],
            "family_id": f"family-{index % 40:02d}",
            "blind_response": "A" if index % 2 == 0 else "B",
            "teacher_preference": "compact",
        })
        task_rows.append({
            "task_id": task_id,
            "pitches_midi": [52, 64],
            "tuning": [64, 59, 55, 50, 45, 40],
            "options": [
                {"option_id": "A", "placements": [
                    {"pitch_midi": 52, "string": 4, "fret": 2},
                    {"pitch_midi": 64, "string": 1, "fret": 0},
                ]},
                {"option_id": "B", "placements": [
                    {"pitch_midi": 52, "string": 5, "fret": 7},
                    {"pitch_midi": 64, "string": 2, "fret": 5},
                ]},
            ],
            "responses": ["A", "B", "EQUAL_OR_UNSURE"],
        })
        current_compact += 1
        index += 1

    task_id = f"task-{index:04d}"
    rows.append({
        "task_id": task_id,
        "curriculum_level": "L4",
        "family_id": f"family-{index % 40:02d}",
        "blind_response": "EQUAL_OR_UNSURE",
        "teacher_preference": "EQUAL_OR_UNSURE",
    })
    task_rows.append({
        "task_id": task_id,
        "pitches_midi": [55, 67],
        "tuning": [64, 59, 55, 50, 45, 40],
        "options": [
            {"option_id": "A", "placements": [
                {"pitch_midi": 55, "string": 3, "fret": 0},
                {"pitch_midi": 67, "string": 1, "fret": 3},
            ]},
            {"option_id": "B", "placements": [
                {"pitch_midi": 55, "string": 4, "fret": 5},
                {"pitch_midi": 67, "string": 2, "fret": 8},
            ]},
        ],
        "responses": ["A", "B", "EQUAL_OR_UNSURE"],
    })

    assert len(rows) == 400
    manifest = {
        "schema": "st-guitar-stage7g-e3-teacher-pairwise-manifest-v1",
        "annotation_blinded": True,
        "task_count": 400,
        "tasks": task_rows,
    }
    validated = {
        "schema": "st-guitar-stage7g-e3-c-teacher-batch01-validated-v1",
        "status": "VALIDATED_COMPLETE_TEACHER_GOLD_PAIRWISE",
        "input_choices_sha256": "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e",
        "manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "rows": rows,
    }
    return manifest, validated


class Stage7GE3S0CRepeatReliabilityTests(unittest.TestCase):
    def test_protocol_freezes_repeat_scope_and_forbids_architecture_activation(self) -> None:
        self.assertEqual(PROTOCOL["status"], "PREREGISTERED_NO_REPEAT_RESULTS")
        self.assertEqual(PROTOCOL["repeat_batch"]["task_count"], 60)
        self.assertEqual(PROTOCOL["repeat_batch"]["teacher_preference_balance"], {"OPEN_LOW": 30, "COMPACT": 30})
        self.assertEqual(PROTOCOL["repeat_batch"]["family_cap"], 2)
        self.assertEqual(PROTOCOL["ultra_reliability_gate"]["exact_semantic_repeat_agreement_gte"], 0.95)
        self.assertEqual(PROTOCOL["ultra_reliability_gate"]["three_way_cohen_kappa_gte"], 0.90)
        self.assertEqual(PROTOCOL["interpretation"]["specialist_architecture_activation_from_s0c_alone"], "FORBIDDEN")
        self.assertEqual(PROTOCOL["interpretation"]["repeat_labels_training_use"], "FORBIDDEN")

    def test_repeat_package_is_deterministic_balanced_reblinded_and_family_capped(self) -> None:
        manifest, validated = _synthetic_inputs()
        teacher_a, audit_a = build_s0c_repeat_package(manifest, validated)
        teacher_b, audit_b = build_s0c_repeat_package(manifest, validated)
        self.assertEqual(teacher_a, teacher_b)
        self.assertEqual(audit_a, audit_b)
        self.assertEqual(teacher_a["schema"], S0C_TEACHER_MANIFEST_SCHEMA)
        self.assertEqual(teacher_a["task_count"], 60)
        self.assertEqual(len({row["task_id"] for row in teacher_a["tasks"]}), 60)
        source_ids = {row["task_id"] for row in manifest["tasks"]}
        self.assertTrue(all(row["task_id"] not in source_ids for row in teacher_a["tasks"]))
        prefs = [row["original_teacher_preference"] for row in audit_a["rows"]]
        self.assertEqual(prefs.count("OPEN_LOW"), 30)
        self.assertEqual(prefs.count("COMPACT"), 30)
        self.assertLessEqual(audit_a["max_tasks_per_family"], 2)
        source_sides = {(row["repeat_A_source_option"], row["repeat_B_source_option"]) for row in audit_a["rows"]}
        self.assertTrue(source_sides.issubset({("A", "B"), ("B", "A")}))
        self.assertGreater(len(source_sides), 1)

    def test_perfect_repeat_passes_ultra_gate(self) -> None:
        manifest, validated = _synthetic_inputs()
        teacher, audit = build_s0c_repeat_package(manifest, validated)
        audit_by_id = {row["repeat_task_id"]: row for row in audit["rows"]}
        choices = []
        for task in teacher["tasks"]:
            row = audit_by_id[task["task_id"]]
            response = "A" if row["repeat_A_source_option"] == row["original_blind_response"] else "B"
            choices.append({"task_id": task["task_id"], "response": response})
        payload = {
            "schema": S0C_CHOICE_EXPORT_SCHEMA,
            "manifest_sha256": teacher["manifest_sha256"],
            "annotation_blinded": True,
            "annotator_id": "teacher_001",
            "selected_count": 60,
            "task_count": 60,
            "choices": choices,
        }
        result = score_s0c_repeat_choices(payload, teacher, audit)
        self.assertTrue(result["ultra_reliability_gate"]["pass"])
        self.assertEqual(result["metrics"]["exact_semantic_repeat_agreement_all_60"], 1.0)
        self.assertEqual(result["metrics"]["three_way_cohen_kappa"], 1.0)
        self.assertFalse(result["scientific_boundary"]["specialist_architecture_activated"])

    def test_four_repeat_disagreements_fail_frozen_ultra_gate(self) -> None:
        manifest, validated = _synthetic_inputs()
        teacher, audit = build_s0c_repeat_package(manifest, validated)
        audit_by_id = {row["repeat_task_id"]: row for row in audit["rows"]}
        choices = []
        for index, task in enumerate(teacher["tasks"]):
            row = audit_by_id[task["task_id"]]
            correct = "A" if row["repeat_A_source_option"] == row["original_blind_response"] else "B"
            if index < 4:
                response = "B" if correct == "A" else "A"
            else:
                response = correct
            choices.append({"task_id": task["task_id"], "response": response})
        payload = {
            "schema": S0C_CHOICE_EXPORT_SCHEMA,
            "manifest_sha256": teacher["manifest_sha256"],
            "annotation_blinded": True,
            "annotator_id": "teacher_001",
            "selected_count": 60,
            "task_count": 60,
            "choices": choices,
        }
        result = score_s0c_repeat_choices(payload, teacher, audit)
        self.assertFalse(result["ultra_reliability_gate"]["pass"])
        self.assertLess(result["metrics"]["exact_semantic_repeat_agreement_all_60"], 0.95)

    def test_html_extractor_and_renderer_do_not_offer_old_answer_import(self) -> None:
        manifest, validated = _synthetic_inputs()
        source_html = (
            "<script>\nconst MANIFEST = "
            + json.dumps(manifest, separators=(",", ":"))
            + ";\nconst MANIFEST_SHA256 = \""
            + EXPECTED_SOURCE_MANIFEST_SHA256
            + "\";\n</script>"
        )
        extracted, digest = extract_source_teacher_manifest_from_html(source_html)
        self.assertEqual(extracted, manifest)
        self.assertEqual(digest, EXPECTED_SOURCE_MANIFEST_SHA256)
        teacher, _ = build_s0c_repeat_package(extracted, validated)
        page = render_s0c_repeat_annotator_html(teacher)
        self.assertIn("Kör tekrar testi", page)
        self.assertIn(S0C_CHOICE_EXPORT_SCHEMA, page)
        self.assertNotIn("importAnswers", page)
        self.assertNotIn("original_teacher_preference", page)


if __name__ == "__main__":
    unittest.main()
