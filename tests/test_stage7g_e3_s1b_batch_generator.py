from __future__ import annotations

from collections import Counter, defaultdict
import json

from st_guitar_fingering_training.stage7g_e3_s0c_repeat_reliability import (
    EXPECTED_SOURCE_CHOICES_SHA256,
    EXPECTED_SOURCE_MANIFEST_SHA256,
)
from st_guitar_fingering_training.stage7g_e3_s1b_batch_generator import (
    COMPONENTS,
    S1_FIRST_EXPORT_SCHEMA,
    S1_FIRST_MANIFEST_SCHEMA,
    S1_REPEAT_EXPORT_SCHEMA,
    S1_REPEAT_MANIFEST_SCHEMA,
    build_s1_packages,
    reconstruct_prior_exclusion_task_ids,
    render_s1_component_annotator,
)


def _fixture() -> tuple[dict, dict]:
    level_specs = {
        "L1": (140, 131, 9, 0),
        "L2": (120, 88, 32, 0),
        "L3": (80, 63, 17, 0),
        "L4": (60, 29, 30, 1),
    }
    tasks = []
    rows = []
    global_index = 0
    for level, (total, open_count, compact_count, equal_count) in level_specs.items():
        preferences = (
            ["open_low"] * open_count
            + ["compact"] * compact_count
            + ["EQUAL_OR_UNSURE"] * equal_count
        )
        assert len(preferences) == total
        for local_index, preference in enumerate(preferences):
            task_id = f"fixture-{level}-{local_index:03d}"
            family_id = f"family_{global_index % 40:02d}"
            low_pitch = 45 + (global_index % 8)
            high_pitch = 60 + (global_index % 12)
            tasks.append({
                "task_id": task_id,
                "pitches_midi": [low_pitch, high_pitch],
                "tuning": [64, 59, 55, 50, 45, 40],
                "options": [
                    {
                        "option_id": "A",
                        "placements": [
                            {"pitch_midi": low_pitch, "string": 5, "fret": global_index % 6},
                            {"pitch_midi": high_pitch, "string": 2, "fret": (global_index + 3) % 9},
                        ],
                    },
                    {
                        "option_id": "B",
                        "placements": [
                            {"pitch_midi": low_pitch, "string": 6, "fret": (global_index + 2) % 8},
                            {"pitch_midi": high_pitch, "string": 1, "fret": (global_index + 5) % 10},
                        ],
                    },
                ],
                "responses": ["A", "B", "EQUAL_OR_UNSURE"],
            })
            rows.append({
                "task_id": task_id,
                "curriculum_level": level,
                "family_id": family_id,
                "blind_response": "A" if global_index % 2 == 0 else "B",
                "teacher_preference": preference,
            })
            global_index += 1

    source_manifest = {
        "schema": "st-guitar-stage7g-e3-teacher-pairwise-manifest-v1",
        "annotation_blinded": True,
        "choice_semantics": "pairwise_guitaristic_preference",
        "task_count": 400,
        "tasks": tasks,
    }
    validated = {
        "schema": "st-guitar-stage7g-e3-c-teacher-batch01-validated-v1",
        "status": "VALIDATED_COMPLETE_TEACHER_GOLD_PAIRWISE",
        "input_choices_sha256": EXPECTED_SOURCE_CHOICES_SHA256,
        "manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "rows": rows,
    }
    return source_manifest, validated


def test_s1b_reconstructs_prior_exclusions_without_response_files():
    _, validated = _fixture()
    exclusions = reconstruct_prior_exclusion_task_ids(validated)
    assert len(exclusions["s0c"]) == 60
    assert len(exclusions["s0da"]) == 20
    assert len(exclusions["s0db"]) == 20
    assert len(exclusions["original_equal_or_unsure"]) == 1
    assert len(exclusions["all"]) == 101
    assert not (exclusions["s0c"] & exclusions["s0da"])
    assert not (exclusions["s0c"] & exclusions["s0db"])
    assert not (exclusions["s0da"] & exclusions["s0db"])


def test_s1b_builds_deterministic_120_first_pass_and_48_repeat_packages():
    source_manifest, validated = _fixture()
    first, first_audit, repeat, repeat_audit = build_s1_packages(source_manifest, validated)
    second = build_s1_packages(source_manifest, validated)
    assert (first, first_audit, repeat, repeat_audit) == second

    assert first["schema"] == S1_FIRST_MANIFEST_SCHEMA
    assert first["task_count"] == 120
    assert len(first["tasks"]) == 120
    assert first_audit["level_counts"] == {"L1": 30, "L2": 30, "L3": 30, "L4": 30}
    assert first_audit["distinct_families"] >= 32
    assert first_audit["max_tasks_per_family"] <= 4
    assert first_audit["session_counts"] == {1: 30, 2: 30, 3: 30, 4: 30}
    assert first_audit["prior_exclusion_counts"] == {
        "s0c": 60,
        "s0da": 20,
        "s0db": 20,
        "original_equal_or_unsure": 1,
        "total_unique": 101,
    }

    first_folds = defaultdict(set)
    for row in first_audit["rows"]:
        first_folds[row["family_id"]].add(row["family_fold"])
    assert all(len(folds) == 1 for folds in first_folds.values())
    assert set().union(*first_folds.values()) == {0, 1, 2, 3, 4}

    assert repeat["schema"] == S1_REPEAT_MANIFEST_SCHEMA
    assert repeat["task_count"] == 48
    assert len(repeat["tasks"]) == 48
    assert repeat_audit["level_counts"] == {"L1": 12, "L2": 12, "L3": 12, "L4": 12}
    assert repeat_audit["max_tasks_per_family"] <= 2
    assert repeat["minimum_delay_hours"] == 24

    first_original_ids = {row["original_task_id"] for row in first_audit["rows"]}
    repeat_original_ids = {row["original_task_id"] for row in repeat_audit["rows"]}
    assert repeat_original_ids <= first_original_ids
    first_task_ids = {row["task_id"] for row in first_audit["rows"]}
    assert {row["first_pass_task_id"] for row in repeat_audit["rows"]} <= first_task_ids


def test_s1b_teacher_manifests_hide_audit_identity_and_old_labels():
    source_manifest, validated = _fixture()
    first, first_audit, repeat, repeat_audit = build_s1_packages(source_manifest, validated)

    first_text = json.dumps(first, ensure_ascii=False)
    repeat_text = json.dumps(repeat, ensure_ascii=False)
    for forbidden in (
        "original_task_id",
        "teacher_preference",
        "blind_response",
        "family_00",
        "fixture-L1-",
        "fixture-L2-",
        "fixture-L3-",
        "fixture-L4-",
    ):
        assert forbidden not in first_text
        assert forbidden not in repeat_text

    assert first_audit["teacher_facing"] is False
    assert repeat_audit["teacher_facing"] is False
    assert first_audit["scientific_boundary"]["model_training"] is False
    assert repeat_audit["scientific_boundary"]["repeat_labels_for_training"] is False

    for task in first["tasks"]:
        assert set(task) == {
            "task_id",
            "pitches_midi",
            "tuning",
            "options",
            "component_dimensions",
            "component_scale",
            "overall_responses",
            "session",
        }
        assert tuple(task["component_dimensions"]) == COMPONENTS
        assert [item["option_id"] for item in task["options"]] == ["A", "B"]


def test_s1b_mobile_annotators_enforce_independent_option_flow_and_export_schema():
    source_manifest, validated = _fixture()
    first, first_audit, repeat, repeat_audit = build_s1_packages(source_manifest, validated)

    first_html = render_s1_component_annotator(first)
    repeat_html = render_s1_component_annotator(repeat, repeat=True)

    assert "viewport" in first_html
    assert "localStorage" in first_html
    assert "Yalnız A seçeneğini değerlendir" in first_html
    assert "Yalnız B seçeneğini değerlendir" in first_html
    assert "Genel tercih" in first_html
    assert S1_FIRST_EXPORT_SCHEMA in first_html
    assert "ST_Guitar_S1_component_choices_120of120.json" in first_html
    assert S1_REPEAT_EXPORT_SCHEMA in repeat_html
    assert "ST_Guitar_S1_repeat_choices_48of48.json" in repeat_html
    assert "Önceki puanlar gösterilmez" in repeat_html
    for component in COMPONENTS:
        assert component in first_html
        assert component in repeat_html
    for hidden_identity in ("fixture-L1-", "family_00", "teacher_preference"):
        assert hidden_identity not in first_html
        assert hidden_identity not in repeat_html


def test_s1b_repeat_is_selected_before_any_new_teacher_answer_field_exists():
    source_manifest, validated = _fixture()
    first, first_audit, repeat, repeat_audit = build_s1_packages(source_manifest, validated)
    assert repeat_audit["scientific_boundary"] == {
        "selected_before_first_pass_answers": True,
        "repeat_labels_for_training": False,
        "repeat_labels_for_tuning": False,
        "repeat_labels_for_model_selection": False,
    }
    assert all("scores" not in task for task in first["tasks"])
    assert all("scores" not in task for task in repeat["tasks"])
