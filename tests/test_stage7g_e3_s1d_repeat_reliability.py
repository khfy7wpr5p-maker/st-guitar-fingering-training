from __future__ import annotations

from unittest.mock import patch

import pytest

import st_guitar_fingering_training.stage7g_e3_s1d_repeat_reliability as s1d
from st_guitar_fingering_training.stage7g_e3_s1b_batch_generator import (
    COMPONENTS,
    S1_FIRST_AUDIT_SCHEMA,
    S1_FIRST_EXPORT_SCHEMA,
    S1_FIRST_MANIFEST_SCHEMA,
    S1_REPEAT_AUDIT_SCHEMA,
    S1_REPEAT_EXPORT_SCHEMA,
    S1_REPEAT_MANIFEST_SCHEMA,
)


def _source_score(task_index: int, source_option: str, component_index: int) -> int:
    offset = 0 if source_option == "A" else 2
    return ((task_index + component_index + offset) % 5) + 1


def _orientation(task_index: int, *, repeat: bool) -> dict[str, str]:
    flipped = (task_index % 3 == 0) if repeat else (task_index % 2 == 1)
    return {"A": "B", "B": "A"} if flipped else {"A": "A", "B": "B"}


def _scores_for_orientation(task_index: int, orientation: dict[str, str]) -> dict:
    return {
        side: {
            component: _source_score(task_index, source_option, component_index)
            for component_index, component in enumerate(COMPONENTS)
        }
        for side, source_option in orientation.items()
    }


def _side_for_source(orientation: dict[str, str], source_option: str) -> str:
    return next(side for side, source in orientation.items() if source == source_option)


def _fixture() -> tuple[dict, dict, dict, dict, dict, dict, str, str]:
    first_tasks = [{"task_id": f"f{i:03d}"} for i in range(120)]
    first_core = {
        "schema": S1_FIRST_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "task_count": 120,
        "tasks": first_tasks,
    }
    first_sha = s1d._canonical_sha256(first_core)
    first_manifest = {**first_core, "manifest_sha256": first_sha}

    repeat_tasks = [{"task_id": f"r{i:03d}"} for i in range(48)]
    repeat_core = {
        "schema": S1_REPEAT_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "first_pass_scores": "withheld",
        "task_count": 48,
        "minimum_delay_hours": 24,
        "tasks": repeat_tasks,
    }
    repeat_sha = s1d._canonical_sha256(repeat_core)
    repeat_manifest = {**repeat_core, "manifest_sha256": repeat_sha}

    first_audit_rows = []
    first_export_rows = []
    first_orientations: dict[int, dict[str, str]] = {}
    for i in range(120):
        orientation = _orientation(i, repeat=False)
        first_orientations[i] = orientation
        level = f"L{(i % 4) + 1}"
        family = f"family_{i % 31:02d}"
        first_audit_rows.append({
            "task_id": f"f{i:03d}",
            "original_task_id": f"o{i:03d}",
            "family_id": family,
            "curriculum_level": level,
            "family_fold": i % 5,
            "A_source_option": orientation["A"],
            "B_source_option": orientation["B"],
            "session": (i // 30) + 1,
        })
        target_source = "A" if i % 2 == 0 else "B"
        first_export_rows.append({
            "task_id": f"f{i:03d}",
            "scores": _scores_for_orientation(i, orientation),
            "overall_preference": _side_for_source(orientation, target_source),
        })

    repeat_audit_rows = []
    repeat_export_rows = []
    for i in range(48):
        orientation = _orientation(i, repeat=True)
        level = f"L{(i % 4) + 1}"
        family = f"family_{i % 31:02d}"
        repeat_audit_rows.append({
            "repeat_task_id": f"r{i:03d}",
            "original_task_id": f"o{i:03d}",
            "first_pass_task_id": f"f{i:03d}",
            "family_id": family,
            "curriculum_level": level,
            "family_fold": i % 5,
            "A_source_option": orientation["A"],
            "B_source_option": orientation["B"],
        })
        target_source = "A" if i % 2 == 0 else "B"
        repeat_export_rows.append({
            "task_id": f"r{i:03d}",
            "scores": _scores_for_orientation(i, orientation),
            "overall_preference": _side_for_source(orientation, target_source),
        })

    first_audit = {
        "schema": S1_FIRST_AUDIT_SCHEMA,
        "manifest_sha256": first_sha,
        "rows": first_audit_rows,
    }
    repeat_audit = {
        "schema": S1_REPEAT_AUDIT_SCHEMA,
        "first_pass_manifest_sha256": first_sha,
        "repeat_manifest_sha256": repeat_sha,
        "rows": repeat_audit_rows,
    }
    first_payload = {
        "schema": S1_FIRST_EXPORT_SCHEMA,
        "manifest_sha256": first_sha,
        "annotator_id": "teacher_001",
        "started_at": "2026-08-16T10:00:00+00:00",
        "completed_at": "2026-08-16T12:00:00+00:00",
        "rows": first_export_rows,
    }
    repeat_payload = {
        "schema": S1_REPEAT_EXPORT_SCHEMA,
        "manifest_sha256": repeat_sha,
        "annotator_id": "teacher_001",
        "started_at": "2026-08-17T13:00:00+00:00",
        "completed_at": "2026-08-17T14:00:00+00:00",
        "rows": repeat_export_rows,
    }
    return (
        first_payload,
        repeat_payload,
        first_manifest,
        repeat_manifest,
        first_audit,
        repeat_audit,
        first_sha,
        repeat_sha,
    )


def _score_fixture(fixture: tuple[dict, dict, dict, dict, dict, dict, str, str]) -> dict:
    first_payload, repeat_payload, first_manifest, repeat_manifest, first_audit, repeat_audit, first_sha, repeat_sha = fixture
    with (
        patch.object(s1d, "EXPECTED_S1_FIRST_MANIFEST_SHA256", first_sha),
        patch.object(s1d, "EXPECTED_S1_REPEAT_MANIFEST_SHA256", repeat_sha),
    ):
        return s1d.score_s1d_repeat_reliability(
            first_payload,
            repeat_payload,
            first_manifest,
            repeat_manifest,
            first_audit,
            repeat_audit,
        )


def test_quadratic_weighted_kappa_identical_diverse_scores_is_one() -> None:
    scores = [1, 2, 3, 4, 5] * 4
    assert s1d.quadratic_weighted_cohen_kappa(scores, scores) == pytest.approx(1.0)


def test_quadratic_weighted_kappa_degenerate_distribution_is_undefined() -> None:
    assert s1d.quadratic_weighted_cohen_kappa([3] * 12, [3] * 12) is None


def test_score_s1d_aligns_independently_reblinded_options_and_passes() -> None:
    result = _score_fixture(_fixture())

    assert result["delay_gate"]["pass"] is True
    assert result["delay_gate"]["actual_hours"] == pytest.approx(25.0)
    assert result["primary_component_reliability"]["all_four_components_pass"] is True
    for component in COMPONENTS:
        metrics = result["primary_component_reliability"]["metrics"][component]
        assert metrics["paired_option_ratings"] == 96
        assert metrics["exact_score_agreement"] == pytest.approx(1.0)
        assert metrics["within_one_point_agreement"] == pytest.approx(1.0)
        assert metrics["mean_absolute_score_difference"] == pytest.approx(0.0)
        assert metrics["quadratic_weighted_cohen_kappa"] == pytest.approx(1.0)
        assert metrics["distinct_first_pass_scores"] == 5
    assert result["secondary_overall_preference_reliability"]["pass"] is True
    assert result["secondary_overall_preference_reliability"]["metrics"]["exact_semantic_repeat_agreement"] == pytest.approx(1.0)
    assert result["secondary_overall_preference_reliability"]["metrics"]["three_way_cohen_kappa"] == pytest.approx(1.0)
    assert {level: data["tasks"] for level, data in result["by_curriculum_level"].items()} == {
        "L1": 12,
        "L2": 12,
        "L3": 12,
        "L4": 12,
    }


def test_score_s1d_rejects_repeat_started_before_24_hour_gate() -> None:
    fixture = list(_fixture())
    fixture[1] = dict(fixture[1])
    fixture[1]["started_at"] = "2026-08-17T11:00:00+00:00"
    fixture[1]["completed_at"] = "2026-08-17T12:00:00+00:00"

    first_payload, repeat_payload, first_manifest, repeat_manifest, first_audit, repeat_audit, first_sha, repeat_sha = tuple(fixture)
    with (
        patch.object(s1d, "EXPECTED_S1_FIRST_MANIFEST_SHA256", first_sha),
        patch.object(s1d, "EXPECTED_S1_REPEAT_MANIFEST_SHA256", repeat_sha),
    ):
        with pytest.raises(ValueError, match="minimum delay gate not satisfied"):
            s1d.score_s1d_repeat_reliability(
                first_payload,
                repeat_payload,
                first_manifest,
                repeat_manifest,
                first_audit,
                repeat_audit,
            )


def test_score_s1d_rejects_manifest_tampering() -> None:
    fixture = list(_fixture())
    first_manifest = dict(fixture[2])
    first_manifest["tasks"] = list(first_manifest["tasks"])
    first_manifest["tasks"][0] = {"task_id": "tampered"}
    fixture[2] = first_manifest

    first_payload, repeat_payload, first_manifest, repeat_manifest, first_audit, repeat_audit, first_sha, repeat_sha = tuple(fixture)
    with (
        patch.object(s1d, "EXPECTED_S1_FIRST_MANIFEST_SHA256", first_sha),
        patch.object(s1d, "EXPECTED_S1_REPEAT_MANIFEST_SHA256", repeat_sha),
    ):
        with pytest.raises(ValueError, match="canonical SHA mismatch"):
            s1d.score_s1d_repeat_reliability(
                first_payload,
                repeat_payload,
                first_manifest,
                repeat_manifest,
                first_audit,
                repeat_audit,
            )
