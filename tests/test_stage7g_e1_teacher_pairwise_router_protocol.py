from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = json.loads(
    (ROOT / "evidence" / "stage7g_e1_teacher_pairwise_router_protocol.json").read_text(encoding="utf-8")
)


def test_stage7g_e1_protocol_is_preregistered_before_real_fit() -> None:
    assert EVIDENCE["schema"] == "st-guitar-stage7g-e1-teacher-pairwise-router-protocol-v1"
    assert EVIDENCE["status"] == "PREREGISTERED_BEFORE_REAL_MODEL_FIT_PENDING_MERGE"
    boundary = EVIDENCE["scientific_boundary"]
    assert boundary["real_teacher_gold_model_fit_started"] is False
    assert boundary["real_teacher_gold_cv_started"] is False
    assert boundary["checkpoint_retained"] is False
    assert boundary["production_integration"] is False
    assert boundary["stage7e_final_reused"] is False


def test_stage7g_e1_uses_only_decisive_pairwise_labels_and_keeps_semantics_separate() -> None:
    source = EVIDENCE["source_teacher_evidence"]
    target = EVIDENCE["target"]
    excluded = EVIDENCE["excluded_from_e1"]
    assert source["pairwise_tasks"] == 562
    assert source["decisive_binary_labels"] == 556
    assert source["equal_or_unsure"] == 6
    assert source["families_with_decisive_labels"] == 40
    assert source["raw_teacher_rows_committed_to_git"] is False
    assert target["equal_or_unsure_coerced"] is False
    assert excluded["full_candidate_teacher_choices"] == 38


def test_stage7g_e1_feature_and_model_contract_is_fixed() -> None:
    features = EVIDENCE["features"]
    model = EVIDENCE["model"]
    assert features["count"] == len(features["names"]) == 15
    assert features["current_event_only"] is True
    assert features["deterministic_physical_candidate_set_only"] is True
    assert features["teacher_response_in_features"] is False
    assert features["source_identity_in_features"] is False
    assert features["family_identity_in_features"] is False
    assert features["observed_source_tab_in_features"] is False
    assert features["sequence_context_in_features"] is False
    assert model["class_weight"] == "balanced"
    assert model["C"] == 1.0
    assert model["solver"] == "lbfgs"
    assert model["random_state"] == 0
    assert model["decision_threshold"] == 0.5
    assert model["hyperparameter_search"] is False
    assert model["feature_selection_after_validation"] is False
    assert model["calibration"] is False


def test_stage7g_e1_validation_is_family_isolated_and_no_cv_checkpoint_gate_is_invented() -> None:
    validation = EVIDENCE["validation"]
    metrics = EVIDENCE["metrics"]
    assert validation["kind"] == "deterministic_5_fold_family_isolated_cross_validation"
    assert validation["fold_count"] == 5
    assert validation["family_count"] == 40
    assert validation["expected_train_families_per_fold"] == 32
    assert validation["expected_validation_families_per_fold"] == 8
    assert validation["event_level_random_split"] is False
    assert validation["family_leakage_allowed"] is False
    assert validation["equal_or_unsure_excluded_from_binary_fit"] is True
    assert metrics["required_baseline"] == "always_open_low"
    assert metrics["checkpoint_promotion_threshold_from_same_cv"] is None
