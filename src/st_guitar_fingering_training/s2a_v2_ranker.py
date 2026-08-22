from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from random import Random
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression

from .finger_assignments import StandardFingering
from .s2a_features import S2A_FEATURE_LIST_SHA256, assignment_feature_vector
from .s2a_v2_fixed_voicing import (
    BUCKET_DEVELOPMENT,
    BUCKET_FINAL,
    DECISION_SELECT,
    S2A_V2_AUDIT_SCHEMA,
    S2A_V2_PROTOCOL_VERSION,
    canonical_sha256,
    manifest_task,
    recompute_assignment_map,
    reliability_report,
    validate_choice_export,
)


COMPARATOR_VERSION = "MIN_MECHANICAL_COMPLEXITY.v1"
MODEL_SCHEMA = "st-guitar-s2a-v2-development-model-v1"
MODEL_VERSION = "S2-A.v2-FIXED-VOICING-RANKER.v1"


@dataclass(frozen=True)
class PreferenceConstraint:
    family_id: str
    task_id: str
    preferred_assignment_id: str
    other_assignment_id: str
    preferred_features: tuple[float, ...]
    other_features: tuple[float, ...]


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _audit_by_task(internal_audit: dict) -> dict[str, dict]:
    if internal_audit.get("schema") != S2A_V2_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A.v2 audit schema")
    rows = internal_audit.get("rows")
    if not isinstance(rows, list):
        raise ValueError("S2-A.v2 audit rows must be a list")
    out: dict[str, dict] = {}
    for row in rows:
        task_id = str(row.get("task_id", ""))
        if not task_id or task_id in out:
            raise ValueError("S2-A.v2 audit has blank/duplicate task identity")
        out[task_id] = row
    return out


def build_development_constraints(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> tuple[PreferenceConstraint, ...]:
    choices = validate_choice_export(development_export, manifest, expected_bucket=BUCKET_DEVELOPMENT)
    audit = _audit_by_task(internal_audit)
    constraints: list[PreferenceConstraint] = []
    for task_id in sorted(choices):
        meta = audit.get(task_id)
        if meta is None:
            raise ValueError("S2-A.v2 development choice missing audit row")
        if meta.get("role") != "DEVELOPMENT_ORIGINAL":
            continue
        decision = choices[task_id]
        if decision["decision"] != DECISION_SELECT:
            continue
        task = manifest_task(manifest, task_id)
        assignments = recompute_assignment_map(task)
        selected_id = str(decision["selected_assignment_id"])
        if selected_id not in assignments:
            raise ValueError("S2-A.v2 selected assignment missing from fresh H-C.v2 output")
        selected_features = assignment_feature_vector(assignments[selected_id])
        family_id = str(meta.get("family_id", ""))
        if not family_id:
            raise ValueError("S2-A.v2 development task missing family identity")
        for other_id in sorted(assignments):
            if other_id == selected_id:
                continue
            constraints.append(PreferenceConstraint(
                family_id=family_id,
                task_id=task_id,
                preferred_assignment_id=selected_id,
                other_assignment_id=other_id,
                preferred_features=selected_features,
                other_features=assignment_feature_vector(assignments[other_id]),
            ))
    constraints.sort(key=lambda row: (row.family_id, row.task_id, row.other_assignment_id))
    return tuple(constraints)


def build_training_matrix(constraints: Iterable[PreferenceConstraint]) -> tuple[np.ndarray, np.ndarray]:
    rows = tuple(constraints)
    if not rows:
        raise ValueError("S2-A.v2 has no decisive preference constraints")
    X: list[np.ndarray] = []
    y: list[int] = []
    for row in rows:
        if len(row.preferred_features) != 30 or len(row.other_features) != 30:
            raise ValueError("S2-A.v2 feature dimension drift")
        delta = np.asarray(row.preferred_features, dtype=np.float64) - np.asarray(row.other_features, dtype=np.float64)
        if not np.isfinite(delta).all():
            raise ValueError("S2-A.v2 pair delta must be finite")
        X.extend((delta, -delta))
        y.extend((1, 0))
    matrix = np.asarray(X, dtype=np.float64)
    labels = np.asarray(y, dtype=np.int64)
    if matrix.shape != (2 * len(rows), 30):
        raise AssertionError("S2-A.v2 mirrored matrix shape mismatch")
    for index in range(0, len(matrix), 2):
        if not np.array_equal(matrix[index], -matrix[index + 1]):
            raise AssertionError("S2-A.v2 mirrored feature symmetry violated")
    return matrix, labels


def build_model() -> LogisticRegression:
    return LogisticRegression(
        penalty="l2",
        C=1.0,
        fit_intercept=False,
        class_weight=None,
        solver="lbfgs",
        max_iter=2000,
        random_state=0,
    )


def mechanical_complexity_key(assignment: StandardFingering) -> tuple:
    positive_fingers = [finger for _, _, fret, finger in assignment.placements if fret > 0]
    barre_span = sum(end - start for _, _, start, end in assignment.barres)
    return (
        len(assignment.barres),
        barre_span,
        len(set(positive_fingers)),
        sum(positive_fingers),
        max(positive_fingers, default=0),
        assignment.assignment_id,
    )


def _score_assignment(model, assignment: StandardFingering) -> float:
    vector = np.asarray(assignment_feature_vector(assignment), dtype=np.float64)
    if hasattr(model, "coef_"):
        score = float(np.dot(np.asarray(model.coef_[0], dtype=np.float64), vector))
    else:
        score = float(np.dot(np.asarray(model, dtype=np.float64), vector))
    if not isfinite(score):
        raise ValueError("S2-A.v2 model produced a non-finite score")
    return score


def _rank_model(model, assignments: dict[str, StandardFingering]) -> list[str]:
    return sorted(assignments, key=lambda item: (-_score_assignment(model, assignments[item]), item))


def _rank_comparator(assignments: dict[str, StandardFingering]) -> list[str]:
    return sorted(assignments, key=lambda item: mechanical_complexity_key(assignments[item]))


def _records(
    manifest: dict,
    internal_audit: dict,
    export: dict,
    *,
    expected_bucket: str,
    required_role: str,
) -> tuple[dict, ...]:
    choices = validate_choice_export(export, manifest, expected_bucket=expected_bucket)
    audit = _audit_by_task(internal_audit)
    out: list[dict] = []
    for task_id in sorted(choices):
        meta = audit.get(task_id)
        if meta is None or meta.get("role") != required_role:
            continue
        decision = choices[task_id]
        if decision["decision"] != DECISION_SELECT:
            continue
        task = manifest_task(manifest, task_id)
        assignments = recompute_assignment_map(task)
        selected = str(decision["selected_assignment_id"])
        if selected not in assignments:
            raise ValueError("S2-A.v2 record selected out-of-set assignment")
        out.append({
            "family_id": str(meta["family_id"]),
            "task_id": task_id,
            "selected_assignment_id": selected,
            "assignments": assignments,
        })
    return tuple(out)


def _fold_map(families: Iterable[str], folds: int = 5) -> dict[str, int]:
    unique = sorted(set(families), key=lambda value: sha256(
        f"{S2A_V2_PROTOCOL_VERSION}|FOLD|{value}".encode("utf-8")
    ).hexdigest())
    if len(unique) < folds:
        raise ValueError("S2-A.v2 needs at least one family per CV fold")
    return {family: index % folds for index, family in enumerate(unique)}


def _fit_from_records(records: Iterable[dict]) -> LogisticRegression:
    constraints: list[PreferenceConstraint] = []
    for row in records:
        preferred = row["assignments"][row["selected_assignment_id"]]
        preferred_features = assignment_feature_vector(preferred)
        for other_id, other in sorted(row["assignments"].items()):
            if other_id == row["selected_assignment_id"]:
                continue
            constraints.append(PreferenceConstraint(
                family_id=row["family_id"],
                task_id=row["task_id"],
                preferred_assignment_id=row["selected_assignment_id"],
                other_assignment_id=other_id,
                preferred_features=preferred_features,
                other_features=assignment_feature_vector(other),
            ))
    X, y = build_training_matrix(constraints)
    model = build_model()
    model.fit(X, y)
    return model


def _evaluate_records(model, records: Iterable[dict]) -> dict:
    rows = tuple(records)
    if not rows:
        raise ValueError("S2-A.v2 evaluation has no decisive tasks")
    details = []
    for row in rows:
        ranked = _rank_model(model, row["assignments"])
        baseline = _rank_comparator(row["assignments"])
        selected = row["selected_assignment_id"]
        model_rank = ranked.index(selected) + 1
        baseline_rank = baseline.index(selected) + 1
        details.append({
            "family_id": row["family_id"],
            "task_id": row["task_id"],
            "model_top1": int(model_rank == 1),
            "model_rr": 1.0 / model_rank,
            "baseline_top1": int(baseline_rank == 1),
            "baseline_rr": 1.0 / baseline_rank,
        })
    family_ids = sorted({row["family_id"] for row in details})
    family_panel = {}
    for family in family_ids:
        items = [row for row in details if row["family_id"] == family]
        family_panel[family] = {
            "model_top1": float(np.mean([row["model_top1"] for row in items])),
            "model_mrr": float(np.mean([row["model_rr"] for row in items])),
            "baseline_top1": float(np.mean([row["baseline_top1"] for row in items])),
            "baseline_mrr": float(np.mean([row["baseline_rr"] for row in items])),
        }
    wins = sum(v["model_top1"] > v["baseline_top1"] for v in family_panel.values())
    ties = sum(v["model_top1"] == v["baseline_top1"] for v in family_panel.values())
    losses = sum(v["model_top1"] < v["baseline_top1"] for v in family_panel.values())
    model_macro_top1 = float(np.mean([v["model_top1"] for v in family_panel.values()]))
    baseline_macro_top1 = float(np.mean([v["baseline_top1"] for v in family_panel.values()]))
    model_macro_mrr = float(np.mean([v["model_mrr"] for v in family_panel.values()]))
    baseline_macro_mrr = float(np.mean([v["baseline_mrr"] for v in family_panel.values()]))
    return {
        "task_count": len(details),
        "family_count": len(family_panel),
        "top1_accuracy": float(np.mean([row["model_top1"] for row in details])),
        "mrr": float(np.mean([row["model_rr"] for row in details])),
        "baseline_top1_accuracy": float(np.mean([row["baseline_top1"] for row in details])),
        "baseline_mrr": float(np.mean([row["baseline_rr"] for row in details])),
        "macro_family_top1": model_macro_top1,
        "macro_family_mrr": model_macro_mrr,
        "baseline_macro_family_top1": baseline_macro_top1,
        "baseline_macro_family_mrr": baseline_macro_mrr,
        "macro_family_top1_delta": model_macro_top1 - baseline_macro_top1,
        "macro_family_mrr_delta": model_macro_mrr - baseline_macro_mrr,
        "family_wins": wins,
        "family_ties": ties,
        "family_losses": losses,
        "family_panel": family_panel,
    }


def _cv_once(records: tuple[dict, ...]) -> dict:
    fold_by_family = _fold_map(row["family_id"] for row in records)
    fold_reports = []
    all_details = []
    for fold in range(5):
        train = tuple(row for row in records if fold_by_family[row["family_id"]] != fold)
        held = tuple(row for row in records if fold_by_family[row["family_id"]] == fold)
        if not train or not held:
            raise ValueError("S2-A.v2 CV produced an empty train/held fold")
        model = _fit_from_records(train)
        report = _evaluate_records(model, held)
        report["fold"] = fold
        fold_reports.append(report)
        for row in held:
            assignments = row["assignments"]
            ranked = _rank_model(model, assignments)
            baseline = _rank_comparator(assignments)
            selected = row["selected_assignment_id"]
            all_details.append({
                "family_id": row["family_id"],
                "task_id": row["task_id"],
                "model_rank": ranked.index(selected) + 1,
                "baseline_rank": baseline.index(selected) + 1,
            })
    all_details.sort(key=lambda row: row["task_id"])
    signature = sha256(_canonical_bytes(all_details)).hexdigest()
    family_ids = sorted({row["family_id"] for row in records})
    family_panel = {}
    for family in family_ids:
        items = [row for row in all_details if row["family_id"] == family]
        family_panel[family] = {
            "model_top1": float(np.mean([row["model_rank"] == 1 for row in items])),
            "model_mrr": float(np.mean([1.0 / row["model_rank"] for row in items])),
            "baseline_top1": float(np.mean([row["baseline_rank"] == 1 for row in items])),
            "baseline_mrr": float(np.mean([1.0 / row["baseline_rank"] for row in items])),
        }
    model_top1 = float(np.mean([row["model_rank"] == 1 for row in all_details]))
    model_mrr = float(np.mean([1.0 / row["model_rank"] for row in all_details]))
    baseline_top1 = float(np.mean([row["baseline_rank"] == 1 for row in all_details]))
    baseline_mrr = float(np.mean([1.0 / row["baseline_rank"] for row in all_details]))
    macro_top1 = float(np.mean([v["model_top1"] for v in family_panel.values()]))
    base_macro_top1 = float(np.mean([v["baseline_top1"] for v in family_panel.values()]))
    macro_mrr = float(np.mean([v["model_mrr"] for v in family_panel.values()]))
    base_macro_mrr = float(np.mean([v["baseline_mrr"] for v in family_panel.values()]))
    return {
        "signature": signature,
        "task_count": len(all_details),
        "family_count": len(family_panel),
        "top1_accuracy": model_top1,
        "mrr": model_mrr,
        "baseline_top1_accuracy": baseline_top1,
        "baseline_mrr": baseline_mrr,
        "macro_family_top1": macro_top1,
        "macro_family_mrr": macro_mrr,
        "baseline_macro_family_top1": base_macro_top1,
        "baseline_macro_family_mrr": base_macro_mrr,
        "macro_family_top1_delta": macro_top1 - base_macro_top1,
        "macro_family_mrr_delta": macro_mrr - base_macro_mrr,
        "family_wins": sum(v["model_top1"] > v["baseline_top1"] for v in family_panel.values()),
        "family_ties": sum(v["model_top1"] == v["baseline_top1"] for v in family_panel.values()),
        "family_losses": sum(v["model_top1"] < v["baseline_top1"] for v in family_panel.values()),
        "folds": fold_reports,
    }


def development_gate_report(manifest: dict, internal_audit: dict, development_export: dict) -> dict:
    rel = reliability_report(development_export, manifest, internal_audit)
    records = _records(
        manifest, internal_audit, development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
    )
    constraints = build_development_constraints(manifest, internal_audit, development_export)
    signatures = []
    reports = []
    if len(records) >= 5 and len({row["family_id"] for row in records}) >= 5:
        for _ in range(10):
            report = _cv_once(records)
            signatures.append(report["signature"])
            reports.append(report)
        cv = reports[0]
        deterministic = len(set(signatures)) == 1
    else:
        cv = {
            "top1_accuracy": 0.0, "mrr": 0.0, "macro_family_top1": 0.0,
            "macro_family_top1_delta": -1.0, "family_wins": 0, "family_losses": 1,
        }
        deterministic = False
    checks = {
        "reliability_pass": rel["status"] == "PASS",
        "decisive_development_tasks_gte_160": len(records) >= 160,
        "development_families_gte_20": len({row["family_id"] for row in records}) >= 20,
        "preference_constraints_gte_200": len(constraints) >= 200,
        "cv_top1_gte_0_60": float(cv["top1_accuracy"]) >= 0.60,
        "cv_mrr_gte_0_75": float(cv["mrr"]) >= 0.75,
        "cv_macro_family_top1_gte_0_60": float(cv["macro_family_top1"]) >= 0.60,
        "cv_macro_family_top1_delta_gte_0_05": float(cv["macro_family_top1_delta"]) >= 0.05,
        "family_wins_gt_losses": int(cv["family_wins"]) > int(cv["family_losses"]),
        "deterministic_10_of_10": deterministic,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "reliability": rel,
        "decisive_development_tasks": len(records),
        "development_families": len({row["family_id"] for row in records}),
        "preference_constraints": len(constraints),
        "cv": cv,
        "determinism_signatures": signatures,
        "comparator": COMPARATOR_VERSION,
    }


def fit_and_seal_development_model(manifest: dict, internal_audit: dict, development_export: dict) -> dict:
    gate = development_gate_report(manifest, internal_audit, development_export)
    if gate["status"] != "PASS":
        raise RuntimeError("S2-A.v2 real Teacher fit gate is CLOSED")
    records = _records(
        manifest, internal_audit, development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
    )
    model = _fit_from_records(records)
    coef = np.asarray(model.coef_[0], dtype=np.float64)
    if coef.shape != (30,) or not np.isfinite(coef).all():
        raise ValueError("S2-A.v2 fitted coefficient vector invalid")
    artifact = {
        "schema": MODEL_SCHEMA,
        "model_version": MODEL_VERSION,
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "feature_list_sha256": S2A_FEATURE_LIST_SHA256,
        "comparator": COMPARATOR_VERSION,
        "training_role": "DEVELOPMENT_ORIGINAL_ONLY",
        "development_gate": gate,
        "manifest_sha256": manifest["manifest_sha256"],
        "internal_audit_sha256": canonical_sha256(internal_audit),
        "development_export_sha256": canonical_sha256(development_export),
        "pipeline": {
            "estimator": "LogisticRegression",
            "params": {
                "penalty": "l2", "C": 1.0, "fit_intercept": False,
                "class_weight": None, "solver": "lbfgs", "max_iter": 2000, "random_state": 0,
            },
            "scaler": None,
        },
        "logistic_coef_hex": [float(value).hex() for value in coef],
        "status": "DEVELOPMENT_PASS_MODEL_SEALED_FINAL_MAY_OPEN",
        "model_sealed": True,
        "final_access_authorized": True,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    artifact["artifact_sha256"] = canonical_sha256(artifact)
    return artifact


def _verify_model_artifact(artifact: dict) -> np.ndarray:
    digest = artifact.get("artifact_sha256")
    if not isinstance(digest, str):
        raise ValueError("S2-A.v2 model artifact is unsealed")
    payload = dict(artifact)
    payload.pop("artifact_sha256", None)
    if canonical_sha256(payload) != digest:
        raise ValueError("S2-A.v2 model artifact SHA mismatch")
    if artifact.get("schema") != MODEL_SCHEMA or artifact.get("model_version") != MODEL_VERSION:
        raise ValueError("unexpected S2-A.v2 model artifact identity")
    if artifact.get("protocol_version") != S2A_V2_PROTOCOL_VERSION:
        raise ValueError("S2-A.v2 model protocol drift")
    if artifact.get("feature_list_sha256") != S2A_FEATURE_LIST_SHA256:
        raise ValueError("S2-A.v2 feature-list drift")
    if artifact.get("model_sealed") is not True or artifact.get("final_access_authorized") is not True:
        raise ValueError("S2-A.v2 final remains closed")
    coef = np.asarray([float.fromhex(value) for value in artifact.get("logistic_coef_hex", [])], dtype=np.float64)
    if coef.shape != (30,) or not np.isfinite(coef).all():
        raise ValueError("S2-A.v2 model coefficient artifact invalid")
    return coef


def _bootstrap_lower_mrr_delta(family_panel: dict[str, dict], *, repetitions: int = 2000) -> float:
    families = sorted(family_panel)
    if len(families) < 2:
        raise ValueError("S2-A.v2 final bootstrap needs multiple families")
    rng = Random(0)
    values = []
    for _ in range(repetitions):
        sampled = [families[rng.randrange(len(families))] for _ in families]
        delta = float(np.mean([
            family_panel[family]["model_mrr"] - family_panel[family]["baseline_mrr"]
            for family in sampled
        ]))
        values.append(delta)
    values.sort()
    return values[49]


def evaluate_untouched_final(
    manifest: dict,
    internal_audit: dict,
    final_export: dict,
    sealed_model_artifact: dict,
) -> dict:
    coef = _verify_model_artifact(sealed_model_artifact)
    records = _records(
        manifest, internal_audit, final_export,
        expected_bucket=BUCKET_FINAL,
        required_role="UNTOUCHED_FINAL",
    )
    panel = _evaluate_records(coef, records)
    lower = _bootstrap_lower_mrr_delta(panel["family_panel"])
    checks = {
        "decisive_final_tasks_gte_50": len(records) >= 50,
        "final_families_gte_6": len({row["family_id"] for row in records}) >= 6,
        "final_top1_gte_0_60": panel["top1_accuracy"] >= 0.60,
        "final_mrr_gte_0_75": panel["mrr"] >= 0.75,
        "final_macro_family_top1_delta_gte_0_05": panel["macro_family_top1_delta"] >= 0.05,
        "final_family_wins_gt_losses": panel["family_wins"] > panel["family_losses"],
        "bootstrap_95pct_mrr_delta_lower_gt_0": lower > 0.0,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metrics": panel,
        "bootstrap_repetitions": 2000,
        "bootstrap_seed": 0,
        "bootstrap_95pct_mrr_delta_lower": lower,
        "model_artifact_sha256": sealed_model_artifact["artifact_sha256"],
        "final_export_sha256": canonical_sha256(final_export),
        "checkpoint_retention_eligibility": "ELIGIBLE_FOR_SEPARATE_REVIEW" if all(checks.values()) else "NOT_ELIGIBLE",
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    result["result_sha256"] = canonical_sha256(result)
    return result
