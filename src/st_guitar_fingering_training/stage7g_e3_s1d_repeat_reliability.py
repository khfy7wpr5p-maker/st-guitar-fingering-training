from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from typing import Iterable

from .stage7g_e3_s1b_batch_generator import (
    COMPONENTS,
    S1_CONFIG,
    S1_FIRST_AUDIT_SCHEMA,
    S1_FIRST_EXPORT_SCHEMA,
    S1_FIRST_MANIFEST_SCHEMA,
    S1_REPEAT_AUDIT_SCHEMA,
    S1_REPEAT_EXPORT_SCHEMA,
    S1_REPEAT_MANIFEST_SCHEMA,
)


S1D_RESULT_SCHEMA = "st-guitar-stage7g-e3-s1d-repeat-reliability-result-v1"

# Frozen by evidence/stage7g_e3_s1b_batch_seal.json before any S1 first-pass response.
EXPECTED_S1_FIRST_MANIFEST_SHA256 = "4a5dd305bd9110eec115cd901ba43a154c6724dca13f54ff634a41f07dd286a1"
EXPECTED_S1_REPEAT_MANIFEST_SHA256 = "7a4fe1ef61df3a991984b00e35050cb0c5faff55b09bc6d8f7578157c70fae17"

PRIMARY_THRESHOLDS = {
    "quadratic_weighted_cohen_kappa_gte": 0.90,
    "exact_score_agreement_gte": 0.80,
    "within_one_point_agreement_gte": 0.98,
    "mean_absolute_score_difference_lte": 0.35,
    "minimum_distinct_first_pass_scores": 3,
    "maximum_single_first_pass_score_fraction": 0.85,
}

SECONDARY_THRESHOLDS = {
    "exact_semantic_repeat_agreement_gte": 0.90,
    "three_way_cohen_kappa_gte": 0.80,
    "repeat_equal_or_unsure_rate_lte": 0.10,
}

_OVERALL_LABELS = ("SOURCE_A", "SOURCE_B", "EQUAL_OR_UNSURE")


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _parse_aware_iso8601(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone offset")
    return parsed


def _cohen_kappa(labels_a: list[str], labels_b: list[str], labels: Iterable[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("kappa inputs must be aligned and non-empty")
    labels = tuple(labels)
    allowed = set(labels)
    if any(value not in allowed for value in labels_a + labels_b):
        raise ValueError("kappa input contains an unexpected label")
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in labels)
    denominator = 1.0 - expected
    if denominator <= 1e-15:
        return None
    return (observed - expected) / denominator


def quadratic_weighted_cohen_kappa(scores_a: list[int], scores_b: list[int]) -> float | None:
    """Quadratic-weighted Cohen kappa for the frozen ordinal 1..5 component scale.

    A degenerate marginal distribution can make kappa undefined. The S1-A protocol
    explicitly treats undefined kappa as FAIL/REVIEW rather than silently passing it.
    """
    if len(scores_a) != len(scores_b) or not scores_a:
        raise ValueError("weighted-kappa inputs must be aligned and non-empty")
    allowed = {1, 2, 3, 4, 5}
    if any(value not in allowed for value in scores_a + scores_b):
        raise ValueError("component scores must be integers in 1..5")

    n = len(scores_a)
    counts_a = Counter(scores_a)
    counts_b = Counter(scores_b)
    observed_disagreement = 0.0
    expected_disagreement = 0.0
    for left in range(1, 6):
        for right in range(1, 6):
            weight = ((left - right) / 4.0) ** 2
            observed_count = sum(
                1 for a, b in zip(scores_a, scores_b) if a == left and b == right
            )
            observed_disagreement += weight * (observed_count / n)
            expected_disagreement += weight * (
                (counts_a[left] / n) * (counts_b[right] / n)
            )
    if expected_disagreement <= 1e-15:
        return None
    return 1.0 - (observed_disagreement / expected_disagreement)


def _validate_manifest(
    manifest: dict,
    *,
    schema: str,
    task_count: int,
    expected_sha256: str,
    repeat: bool,
) -> set[str]:
    if manifest.get("schema") != schema:
        raise ValueError("unexpected S1 manifest schema")
    if manifest.get("annotation_blinded") is not True:
        raise ValueError("S1 manifest must remain blinded")
    if manifest.get("task_count") != task_count:
        raise ValueError(f"S1 manifest must contain exactly {task_count} tasks")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != task_count:
        raise ValueError(f"S1 manifest tasks must contain exactly {task_count} rows")
    task_ids = [str(task.get("task_id", "")) for task in tasks]
    if any(not task_id for task_id in task_ids) or len(set(task_ids)) != task_count:
        raise ValueError("S1 manifest task IDs are blank or duplicated")

    manifest_sha = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if manifest_sha != _canonical_sha256(core):
        raise ValueError("S1 manifest canonical SHA mismatch")
    if manifest_sha != expected_sha256:
        raise ValueError("S1 manifest identity differs from the frozen S1-B seal")

    if repeat:
        if manifest.get("minimum_delay_hours") != int(S1_CONFIG["minimum_delay_hours"]):
            raise ValueError("S1 repeat minimum-delay requirement drift")
        if manifest.get("first_pass_scores") != "withheld":
            raise ValueError("S1 repeat manifest must withhold first-pass scores")
    return set(task_ids)


def _validate_export(
    payload: dict,
    *,
    schema: str,
    manifest_sha256: str,
    known_task_ids: set[str],
    task_count: int,
) -> tuple[dict[str, dict], datetime, datetime]:
    if payload.get("schema") != schema:
        raise ValueError("unexpected S1 choice-export schema")
    if payload.get("manifest_sha256") != manifest_sha256:
        raise ValueError("S1 choice export references the wrong manifest")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != task_count:
        raise ValueError(f"S1 choice export must contain exactly {task_count} rows")

    started_at = _parse_aware_iso8601(payload.get("started_at"), field="started_at")
    completed_at = _parse_aware_iso8601(payload.get("completed_at"), field="completed_at")
    if completed_at < started_at:
        raise ValueError("S1 choice export completed_at precedes started_at")

    row_by_id: dict[str, dict] = {}
    for row in rows:
        task_id = str(row.get("task_id", ""))
        if task_id not in known_task_ids or task_id in row_by_id:
            raise ValueError("S1 choice export task ID is unknown or duplicated")
        scores = row.get("scores")
        if not isinstance(scores, dict) or set(scores) != {"A", "B"}:
            raise ValueError("S1 choice export must contain A/B score dictionaries")
        for side in ("A", "B"):
            side_scores = scores.get(side)
            if not isinstance(side_scores, dict) or set(side_scores) != set(COMPONENTS):
                raise ValueError("S1 component score keys do not match the frozen rubric")
            for component in COMPONENTS:
                value = side_scores[component]
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                    raise ValueError("S1 component scores must be integer values in 1..5")
        if row.get("overall_preference") not in ("A", "B", "EQUAL_OR_UNSURE"):
            raise ValueError("invalid S1 overall preference")
        row_by_id[task_id] = row
    if set(row_by_id) != known_task_ids:
        raise ValueError("S1 choice export task set is incomplete")
    return row_by_id, started_at, completed_at


def _validate_audits(
    first_audit: dict,
    repeat_audit: dict,
    *,
    first_manifest_sha256: str,
    repeat_manifest_sha256: str,
    first_task_ids: set[str],
    repeat_task_ids: set[str],
) -> tuple[dict[str, dict], dict[str, dict]]:
    if first_audit.get("schema") != S1_FIRST_AUDIT_SCHEMA:
        raise ValueError("unexpected S1 first-pass audit schema")
    if first_audit.get("manifest_sha256") != first_manifest_sha256:
        raise ValueError("S1 first-pass audit references the wrong manifest")
    first_rows = first_audit.get("rows")
    if not isinstance(first_rows, list) or len(first_rows) != 120:
        raise ValueError("S1 first-pass audit must contain exactly 120 rows")
    first_by_id = {str(row.get("task_id", "")): row for row in first_rows}
    if set(first_by_id) != first_task_ids or len(first_by_id) != 120:
        raise ValueError("S1 first-pass audit task set mismatch")

    if repeat_audit.get("schema") != S1_REPEAT_AUDIT_SCHEMA:
        raise ValueError("unexpected S1 repeat audit schema")
    if repeat_audit.get("first_pass_manifest_sha256") != first_manifest_sha256:
        raise ValueError("S1 repeat audit references the wrong first-pass manifest")
    if repeat_audit.get("repeat_manifest_sha256") != repeat_manifest_sha256:
        raise ValueError("S1 repeat audit references the wrong repeat manifest")
    repeat_rows = repeat_audit.get("rows")
    if not isinstance(repeat_rows, list) or len(repeat_rows) != 48:
        raise ValueError("S1 repeat audit must contain exactly 48 rows")
    repeat_by_id = {str(row.get("repeat_task_id", "")): row for row in repeat_rows}
    if set(repeat_by_id) != repeat_task_ids or len(repeat_by_id) != 48:
        raise ValueError("S1 repeat audit task set mismatch")

    for repeat_row in repeat_rows:
        first_task_id = str(repeat_row.get("first_pass_task_id", ""))
        first_row = first_by_id.get(first_task_id)
        if first_row is None:
            raise ValueError("S1 repeat audit references an unknown first-pass task")
        for field in ("original_task_id", "family_id", "curriculum_level", "family_fold"):
            if repeat_row.get(field) != first_row.get(field):
                raise ValueError(f"S1 repeat/first audit linkage drift in {field}")
        for audit_row in (first_row, repeat_row):
            sides = {audit_row.get("A_source_option"), audit_row.get("B_source_option")}
            if sides != {"A", "B"}:
                raise ValueError("S1 audit A/B source-option mapping is invalid")
    return first_by_id, repeat_by_id


def _component_metrics(first_scores: list[int], repeat_scores: list[int]) -> dict:
    if len(first_scores) != len(repeat_scores) or not first_scores:
        raise ValueError("component metric inputs must be aligned and non-empty")
    n = len(first_scores)
    exact = sum(a == b for a, b in zip(first_scores, repeat_scores)) / n
    within_one = sum(abs(a - b) <= 1 for a, b in zip(first_scores, repeat_scores)) / n
    mad = sum(abs(a - b) for a, b in zip(first_scores, repeat_scores)) / n
    qwk = quadratic_weighted_cohen_kappa(first_scores, repeat_scores)
    counts = Counter(first_scores)
    distinct = len(counts)
    max_fraction = max(counts.values()) / n
    return {
        "paired_option_ratings": n,
        "quadratic_weighted_cohen_kappa": qwk,
        "exact_score_agreement": exact,
        "within_one_point_agreement": within_one,
        "mean_absolute_score_difference": mad,
        "first_pass_score_counts": {str(score): counts[score] for score in range(1, 6)},
        "distinct_first_pass_scores": distinct,
        "maximum_single_first_pass_score_fraction": max_fraction,
    }


def _component_gate(metrics: dict) -> dict:
    qwk = metrics["quadratic_weighted_cohen_kappa"]
    conditions = {
        "quadratic_weighted_cohen_kappa": qwk is not None
        and qwk >= PRIMARY_THRESHOLDS["quadratic_weighted_cohen_kappa_gte"],
        "exact_score_agreement": metrics["exact_score_agreement"]
        >= PRIMARY_THRESHOLDS["exact_score_agreement_gte"],
        "within_one_point_agreement": metrics["within_one_point_agreement"]
        >= PRIMARY_THRESHOLDS["within_one_point_agreement_gte"],
        "mean_absolute_score_difference": metrics["mean_absolute_score_difference"]
        <= PRIMARY_THRESHOLDS["mean_absolute_score_difference_lte"],
        "variance_minimum_distinct_scores": metrics["distinct_first_pass_scores"]
        >= PRIMARY_THRESHOLDS["minimum_distinct_first_pass_scores"],
        "variance_maximum_single_score_fraction": metrics["maximum_single_first_pass_score_fraction"]
        <= PRIMARY_THRESHOLDS["maximum_single_first_pass_score_fraction"],
    }
    return {
        "conditions": conditions,
        "pass": all(conditions.values()),
        "undefined_kappa_review": qwk is None,
    }


def _semantic_overall(preference: str, audit_row: dict) -> str:
    if preference == "EQUAL_OR_UNSURE":
        return preference
    source_option = audit_row[f"{preference}_source_option"]
    if source_option not in ("A", "B"):
        raise ValueError("invalid source-option mapping for overall preference")
    return f"SOURCE_{source_option}"


def _summarize_subset(task_records: list[dict]) -> dict:
    result: dict[str, object] = {"tasks": len(task_records)}
    component_summary: dict[str, dict] = {}
    for component in COMPONENTS:
        first_scores: list[int] = []
        repeat_scores: list[int] = []
        for record in task_records:
            for option_pair in record["option_pairs"]:
                first_scores.append(option_pair["first_scores"][component])
                repeat_scores.append(option_pair["repeat_scores"][component])
        if first_scores:
            metrics = _component_metrics(first_scores, repeat_scores)
            component_summary[component] = {
                "paired_option_ratings": metrics["paired_option_ratings"],
                "exact_score_agreement": metrics["exact_score_agreement"],
                "within_one_point_agreement": metrics["within_one_point_agreement"],
                "mean_absolute_score_difference": metrics["mean_absolute_score_difference"],
                "quadratic_weighted_cohen_kappa": metrics["quadratic_weighted_cohen_kappa"],
            }
    result["components"] = component_summary
    if task_records:
        result["overall_exact_semantic_agreement"] = sum(
            record["first_overall_semantic"] == record["repeat_overall_semantic"]
            for record in task_records
        ) / len(task_records)
    return result


def score_s1d_repeat_reliability(
    first_payload: dict,
    repeat_payload: dict,
    first_manifest: dict,
    repeat_manifest: dict,
    first_audit: dict,
    repeat_audit: dict,
) -> dict:
    """Validate and score the frozen S1-D blind repeat.

    The function is intentionally fail-closed. It verifies the exact S1-B sealed
    manifest identities, hidden audit linkage, complete 120/48 response exports,
    and the preregistered 24-hour delay before computing any reliability result.
    It never trains, tunes, weights, or promotes a model.
    """
    first_task_ids = _validate_manifest(
        first_manifest,
        schema=S1_FIRST_MANIFEST_SCHEMA,
        task_count=120,
        expected_sha256=EXPECTED_S1_FIRST_MANIFEST_SHA256,
        repeat=False,
    )
    repeat_task_ids = _validate_manifest(
        repeat_manifest,
        schema=S1_REPEAT_MANIFEST_SCHEMA,
        task_count=48,
        expected_sha256=EXPECTED_S1_REPEAT_MANIFEST_SHA256,
        repeat=True,
    )
    first_by_id, repeat_by_id = _validate_audits(
        first_audit,
        repeat_audit,
        first_manifest_sha256=first_manifest["manifest_sha256"],
        repeat_manifest_sha256=repeat_manifest["manifest_sha256"],
        first_task_ids=first_task_ids,
        repeat_task_ids=repeat_task_ids,
    )
    first_choices, _first_started, first_completed = _validate_export(
        first_payload,
        schema=S1_FIRST_EXPORT_SCHEMA,
        manifest_sha256=first_manifest["manifest_sha256"],
        known_task_ids=first_task_ids,
        task_count=120,
    )
    repeat_choices, repeat_started, _repeat_completed = _validate_export(
        repeat_payload,
        schema=S1_REPEAT_EXPORT_SCHEMA,
        manifest_sha256=repeat_manifest["manifest_sha256"],
        known_task_ids=repeat_task_ids,
        task_count=48,
    )
    if first_payload.get("annotator_id") != repeat_payload.get("annotator_id"):
        raise ValueError("S1 first-pass and repeat exports must use the same annotator_id")

    delay_hours = (repeat_started - first_completed).total_seconds() / 3600.0
    required_delay = float(S1_CONFIG["minimum_delay_hours"])
    if delay_hours < required_delay:
        raise ValueError(
            f"S1-D minimum delay gate not satisfied: {delay_hours:.6f}h < {required_delay:.1f}h"
        )

    task_records: list[dict] = []
    component_first: dict[str, list[int]] = {component: [] for component in COMPONENTS}
    component_repeat: dict[str, list[int]] = {component: [] for component in COMPONENTS}
    overall_first: list[str] = []
    overall_repeat: list[str] = []

    repeat_audit_by_id = repeat_by_id
    for task in repeat_manifest["tasks"]:
        repeat_task_id = str(task["task_id"])
        repeat_audit_row = repeat_audit_by_id[repeat_task_id]
        first_task_id = str(repeat_audit_row["first_pass_task_id"])
        first_audit_row = first_by_id[first_task_id]
        first_choice = first_choices[first_task_id]
        repeat_choice = repeat_choices[repeat_task_id]

        option_pairs: list[dict] = []
        for repeat_side in ("A", "B"):
            source_option = repeat_audit_row[f"{repeat_side}_source_option"]
            first_side = next(
                side for side in ("A", "B")
                if first_audit_row[f"{side}_source_option"] == source_option
            )
            first_score_map = first_choice["scores"][first_side]
            repeat_score_map = repeat_choice["scores"][repeat_side]
            for component in COMPONENTS:
                component_first[component].append(first_score_map[component])
                component_repeat[component].append(repeat_score_map[component])
            option_pairs.append({
                "source_option": source_option,
                "first_scores": first_score_map,
                "repeat_scores": repeat_score_map,
            })

        first_semantic = _semantic_overall(first_choice["overall_preference"], first_audit_row)
        repeat_semantic = _semantic_overall(repeat_choice["overall_preference"], repeat_audit_row)
        overall_first.append(first_semantic)
        overall_repeat.append(repeat_semantic)
        task_records.append({
            "curriculum_level": repeat_audit_row["curriculum_level"],
            "family_id": repeat_audit_row["family_id"],
            "option_pairs": option_pairs,
            "first_overall_semantic": first_semantic,
            "repeat_overall_semantic": repeat_semantic,
        })

    component_metrics = {
        component: _component_metrics(component_first[component], component_repeat[component])
        for component in COMPONENTS
    }
    component_gates = {
        component: _component_gate(component_metrics[component])
        for component in COMPONENTS
    }
    component_pass = all(gate["pass"] for gate in component_gates.values())

    overall_exact = sum(a == b for a, b in zip(overall_first, overall_repeat)) / 48
    overall_kappa = _cohen_kappa(overall_first, overall_repeat, _OVERALL_LABELS)
    repeat_equal_count = sum(value == "EQUAL_OR_UNSURE" for value in overall_repeat)
    repeat_equal_rate = repeat_equal_count / 48
    overall_conditions = {
        "exact_semantic_repeat_agreement": overall_exact
        >= SECONDARY_THRESHOLDS["exact_semantic_repeat_agreement_gte"],
        "three_way_cohen_kappa": overall_kappa is not None
        and overall_kappa >= SECONDARY_THRESHOLDS["three_way_cohen_kappa_gte"],
        "repeat_equal_or_unsure_rate": repeat_equal_rate
        <= SECONDARY_THRESHOLDS["repeat_equal_or_unsure_rate_lte"],
    }
    overall_pass = all(overall_conditions.values())

    by_level = {
        level: _summarize_subset([row for row in task_records if row["curriculum_level"] == level])
        for level in ("L1", "L2", "L3", "L4")
    }
    grouped_family: dict[str, list[dict]] = defaultdict(list)
    for record in task_records:
        grouped_family[str(record["family_id"])].append(record)
    by_family = {
        family_id: _summarize_subset(records)
        for family_id, records in sorted(grouped_family.items())
    }

    return {
        "schema": S1D_RESULT_SCHEMA,
        "stage": "7G-E3-S1-D",
        "status": (
            "S1A_COMPONENT_RELIABILITY_GATE_PASS_ELIGIBLE_FOR_COMPONENT_TRAINING_PROTOCOL_DESIGN"
            if component_pass
            else "S1A_COMPONENT_RELIABILITY_GATE_FAIL_REVIEW_RUBRIC_BEFORE_TRAINING"
        ),
        "sealed_identity": {
            "first_pass_manifest_sha256": first_manifest["manifest_sha256"],
            "repeat_manifest_sha256": repeat_manifest["manifest_sha256"],
            "first_pass_task_count": 120,
            "repeat_task_count": 48,
            "paired_option_ratings_per_component": 96,
        },
        "delay_gate": {
            "required_hours": required_delay,
            "actual_hours": delay_hours,
            "pass": True,
            "first_pass_completed_at": first_payload["completed_at"],
            "repeat_started_at": repeat_payload["started_at"],
        },
        "primary_component_reliability": {
            "thresholds": dict(PRIMARY_THRESHOLDS),
            "metrics": component_metrics,
            "gates": component_gates,
            "all_four_components_pass": component_pass,
        },
        "secondary_overall_preference_reliability": {
            "status": (
                "S1A_OVERALL_REPEAT_SIGNAL_ADEQUATE_FOR_LATER_ARBITER_TARGET_DESIGN"
                if overall_pass
                else "S1A_OVERALL_REPEAT_SIGNAL_INADEQUATE_KEEP_ARBITER_TARGET_CLOSED"
            ),
            "thresholds": dict(SECONDARY_THRESHOLDS),
            "metrics": {
                "exact_semantic_repeat_agreement": overall_exact,
                "three_way_cohen_kappa": overall_kappa,
                "repeat_equal_or_unsure_rate": repeat_equal_rate,
                "repeat_equal_or_unsure_count": repeat_equal_count,
            },
            "conditions": overall_conditions,
            "pass": overall_pass,
            "undefined_kappa_review": overall_kappa is None,
        },
        "by_curriculum_level": by_level,
        "by_family": by_family,
        "scientific_boundary": {
            "first_pass_labels_used_for_training": False,
            "repeat_labels_used_for_training": False,
            "repeat_labels_used_for_tuning": False,
            "repeat_labels_used_for_model_selection": False,
            "rubric_weights_fitted": False,
            "thresholds_changed_after_results": False,
            "component_specialist_trained": False,
            "guitaristic_arbiter_trained": False,
            "dcr_refiner_trained": False,
            "checkpoint_retained": False,
            "production_or_shadow_integration": False,
        },
    }


__all__ = [
    "EXPECTED_S1_FIRST_MANIFEST_SHA256",
    "EXPECTED_S1_REPEAT_MANIFEST_SHA256",
    "PRIMARY_THRESHOLDS",
    "SECONDARY_THRESHOLDS",
    "S1D_RESULT_SCHEMA",
    "quadratic_weighted_cohen_kappa",
    "score_s1d_repeat_reliability",
]
