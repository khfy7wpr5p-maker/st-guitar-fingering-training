from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_e1_r1_teacher_pairwise_router_result.json"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_stage7g_e1_r1_input_counts_and_hashes_are_pinned() -> None:
    data = _load()
    inputs = data["inputs"]
    assert data["schema"] == "st-guitar-stage7g-e1-r1-teacher-pairwise-router-result-v1"
    assert inputs["teacher_manifest_sha256"] == "3d3fbf9d0107ef8a1a31e597820b687a072fa0f2cc5123b8e59adbbf07e4a167"
    assert inputs["teacher_choice_export_sha256"] == "87aecd6f26f3aa450bb71524fd4205afefa77cb9aee8b8741577f8a0f169afde"
    assert inputs["pairwise_tasks"] == 562
    assert inputs["decisive_rows"] == 556
    assert inputs["equal_or_unsure_excluded"] == 6
    assert inputs["families"] == 40
    assert inputs["decoded_teacher_preference"] == {"open_low": 433, "compact": 123}


def test_stage7g_e1_r1_folds_are_family_isolated_exhaustive_and_disjoint() -> None:
    data = _load()
    validation = data["validation"]
    folds = validation["folds"]
    assert validation["family_isolated"] is True
    assert validation["fold_count"] == len(folds) == 5
    family_ids = [family for fold in folds for family in fold["validation_families"]]
    assert len(family_ids) == 40
    assert len(set(family_ids)) == 40
    assert sum(fold["validation_events"] for fold in folds) == 556


def test_stage7g_e1_r1_router_does_not_beat_preregistered_open_low_baseline() -> None:
    data = _load()
    validation = data["validation"]
    assert validation["event_weighted_accuracy"] < validation["event_weighted_always_open_low_accuracy"]
    assert validation["event_weighted_accuracy_delta_vs_always_open_low"] < 0.0
    assert validation["macro_family_accuracy"] < validation["macro_family_always_open_low_accuracy"]
    assert validation["macro_family_accuracy_delta_vs_always_open_low"] < 0.0
    assert data["interpretation"]["primary_baseline_beaten"] is False
    assert data["interpretation"]["promotion_decision"] == "NO_PROMOTION"


def test_stage7g_e1_r1_keeps_post_result_safety_boundaries_closed() -> None:
    data = _load()
    boundary = data["scientific_boundary"]
    assert data["model"]["hyperparameter_search"] is False
    assert data["interpretation"]["post_hoc_threshold_or_hyperparameter_tuning_performed"] is False
    assert boundary["development_cv_only"] is True
    assert boundary["checkpoint_retained"] is False
    assert boundary["production_integration"] is False
    assert boundary["stage7e_reused"] is False
    assert boundary["sequence_context_used"] is False
    assert boundary["raw_teacher_rows_committed_to_git"] is False
    assert boundary["checkpoint_gate_defined_from_this_cv"] is False
