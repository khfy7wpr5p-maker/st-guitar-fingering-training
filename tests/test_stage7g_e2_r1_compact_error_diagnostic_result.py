from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "stage7g_e2_r1_compact_error_diagnostic_result.json"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_stage7g_e2_r1_confusion_is_self_consistent() -> None:
    data = _load()
    result = data["e1_oof_reproduction"]
    confusion = result["confusion"]
    assert data["schema"] == "st-guitar-stage7g-e2-r1-compact-error-diagnostic-result-v1"
    assert data["status"] == "DIAGNOSTIC_COMPLETE_HYPOTHESIS_ONLY"
    assert confusion == {
        "compact_true_positive": 66,
        "compact_false_negative": 57,
        "compact_false_positive": 107,
        "open_low_true_negative": 326,
    }
    assert sum(confusion.values()) == 556
    assert confusion["compact_true_positive"] + confusion["compact_false_negative"] == 123
    assert confusion["compact_false_positive"] + confusion["open_low_true_negative"] == 433
    assert result["predicted_compact"] == 173
    assert result["net_correct_change_vs_always_open_low"] == -41


def test_stage7g_e2_r1_fixed_strata_cover_all_events() -> None:
    data = _load()
    strata = data["fixed_strata"]
    for dimension in (
        "candidate_count",
        "chord_size",
        "internal_string_gaps_delta",
        "mean_positive_fret_delta",
        "open_note_delta",
        "positive_fret_span_delta",
        "same_fret_barre_proxy_delta",
    ):
        assert sum(bucket["events"] for bucket in strata[dimension].values()) == 556


def test_stage7g_e2_r1_position_pattern_is_diagnostic_only() -> None:
    data = _load()
    fret = data["fixed_strata"]["mean_positive_fret_delta"]
    assert fret["negative"]["events"] == 50
    assert fret["negative"]["teacher_compact"] == 42
    assert fret["negative"]["teacher_compact_rate"] == 0.84
    assert fret["zero"]["oof_false_positive_compact"] == 70
    assert fret["positive"]["teacher_compact_rate"] < fret["negative"]["teacher_compact_rate"]
    assert data["scientific_boundary"]["feature_selection"] is False


def test_stage7g_e2_r1_keeps_all_promotion_boundaries_closed() -> None:
    data = _load()
    boundary = data["scientific_boundary"]
    assert boundary["diagnostic_only"] is True
    assert boundary["new_model_fit"] is False
    assert boundary["feature_selection"] is False
    assert boundary["threshold_tuning"] is False
    assert boundary["hyperparameter_search"] is False
    assert boundary["checkpoint_retained"] is False
    assert boundary["production_integration"] is False
    assert boundary["stage7e_reused"] is False
    assert boundary["sequence_context_used"] is False
    assert boundary["raw_teacher_rows_embedded"] is False
    assert boundary["event_level_predictions_embedded"] is False
    assert boundary["future_model_claim_requires_new_disjoint_teacher_gold_or_separately_preregistered_nested_evaluation"] is True
