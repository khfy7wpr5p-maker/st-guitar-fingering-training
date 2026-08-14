from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_d_r3_pairwise_label_result.json"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_stage7g_d_r3_export_is_complete_and_validated() -> None:
    data = _load()
    validation = data["validation"]
    assert data["schema"] == "st-guitar-stage7g-d-r3-pairwise-label-evidence-v1"
    assert data["source_annotation"]["annotation_blinded"] is True
    assert validation["known_manifest_tasks"] == 562
    assert validation["validated_choice_rows"] == 562
    assert validation["unknown_task_ids"] == 0
    assert validation["duplicate_task_ids"] == 0
    assert validation["invalid_responses"] == 0
    assert validation["missing_task_ids"] == 0
    assert validation["complete_export"] is True
    assert validation["manifest_sha256_matches_sealed_r2_package"] is True


def test_stage7g_d_r3_counts_are_self_consistent() -> None:
    data = _load()
    responses = data["responses"]
    decoded = data["decoded_teacher_preference"]
    assert responses["A"] + responses["B"] + responses["EQUAL_OR_UNSURE"] == 562
    assert responses["A"] + responses["B"] == responses["decisive_ab"] == 556
    assert decoded["open_low"] + decoded["compact"] == responses["decisive_ab"]
    assert decoded["EQUAL_OR_UNSURE"] == responses["EQUAL_OR_UNSURE"]
    assert decoded["family_majority"]["open_low"] + decoded["family_majority"]["compact"] + decoded["family_majority"]["tie"] == 40


def test_stage7g_d_r3_preregistered_pairwise_gate_passes() -> None:
    data = _load()
    gate = data["preregistered_pairwise_training_gate"]
    coverage = data["family_coverage"]
    assert gate["observed_decisive_ab_labels"] >= gate["minimum_decisive_ab_labels"]
    assert gate["observed_independent_families_with_decisive_labels"] >= gate["minimum_independent_families_with_decisive_labels"]
    assert gate["observed_independent_families_with_decisive_labels"] == 40
    assert coverage["families_with_decisive_ab_label"] == 40
    assert coverage["minimum_decisive_labels_per_family"] > 0
    assert gate["equal_or_unsure_preserved_and_not_coerced"] is True
    assert gate["family_isolated_validation_required"] is True
    assert gate["gate_passed"] is True


def test_stage7g_d_r3_keeps_safety_boundaries_closed() -> None:
    data = _load()
    boundary = data["scientific_boundary"]
    assert data["source_annotation"]["raw_choice_rows_committed_to_git"] is False
    assert boundary["model_fit_started"] is False
    assert boundary["colab_training_started"] is False
    assert boundary["checkpoint_retained"] is False
    assert boundary["production_integration"] is False
    assert boundary["stage7e_final_reused"] is False
    assert boundary["raw_teacher_rows_in_git"] is False
