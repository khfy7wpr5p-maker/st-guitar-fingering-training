from __future__ import annotations

from hashlib import sha256
import json
from math import isfinite
from random import Random
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .s2a_features import S2A_FEATURE_LIST_SHA256, S2A_FEATURE_NAMES, assignment_feature_vector
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
from .s2a_v2_ranker import COMPARATOR_VERSION, mechanical_complexity_key


V21_PROTOCOL_VERSION = "S2-A.v2.1-DEVELOPMENT-RECOVERY.v1"
V21_MODEL_VERSION = "S2-A.v2.1-QUADRATIC-UTILITY-RANKER.v1"
V21_MODEL_SCHEMA = "st-guitar-s2a-v21-development-model-v1"
V21_FINAL_SCHEMA = "st-guitar-s2a-v21-untouched-final-result-v1"
V21_EXPANDED_DIM = 495
V21_C = 3.0


def _feature_names() -> tuple[str, ...]:
    base = tuple(S2A_FEATURE_NAMES)
    quadratic = tuple(
        f"quadratic:{base[i]}*{base[j]}"
        for i in range(len(base))
        for j in range(i, len(base))
    )
    names = base + quadratic
    if len(names) != V21_EXPANDED_DIM:
        raise AssertionError("S2-A.v2.1 expanded feature dimension drift")
    return names


V21_FEATURE_NAMES = _feature_names()
V21_FEATURE_LIST_SHA256 = sha256(
    json.dumps(V21_FEATURE_NAMES, separators=(",", ":")).encode("utf-8")
).hexdigest()


def quadratic_feature_vector(assignment) -> tuple[float, ...]:
    base = tuple(float(value) for value in assignment_feature_vector(assignment))
    values = list(base)
    for i in range(len(base)):
        for j in range(i, len(base)):
            values.append(base[i] * base[j])
    if len(values) != V21_EXPANDED_DIM or not all(isfinite(value) for value in values):
        raise ValueError("S2-A.v2.1 expanded feature vector invalid")
    return tuple(values)


def _audit_by_task(internal_audit: dict) -> dict[str, dict]:
    if internal_audit.get("schema") != S2A_V2_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A.v2 audit schema")
    rows = internal_audit.get("rows")
    if not isinstance(rows, list):
        raise ValueError("S2-A.v2.1 audit rows must be a list")
    out: dict[str, dict] = {}
    for row in rows:
        task_id = str(row.get("task_id", ""))
        if not task_id or task_id in out:
            raise ValueError("S2-A.v2.1 audit has blank/duplicate task identity")
        out[task_id] = row
    return out


def _decision_token(decision: dict) -> tuple[str, str | None]:
    kind = str(decision.get("decision", ""))
    selected = str(decision.get("selected_assignment_id")) if kind == DECISION_SELECT else None
    return kind, selected


def unstable_repeat_semantics(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> tuple[str, ...]:
    choices = validate_choice_export(
        development_export, manifest, expected_bucket=BUCKET_DEVELOPMENT
    )
    pairs = internal_audit.get("repeat_pairs")
    if not isinstance(pairs, list) or len(pairs) != 30:
        raise ValueError("S2-A.v2.1 requires the frozen 30 hidden repeat pairs")
    unstable: set[str] = set()
    for pair in pairs:
        original = str(pair.get("original_task_id", ""))
        repeat = str(pair.get("repeat_task_id", ""))
        if original not in choices or repeat not in choices:
            raise ValueError("S2-A.v2.1 repeat choice missing")
        original_task = manifest_task(manifest, original)
        repeat_task = manifest_task(manifest, repeat)
        semantic = str(original_task["semantic_fingerprint"])
        if semantic != str(repeat_task["semantic_fingerprint"]):
            raise ValueError("S2-A.v2.1 repeat semantic mismatch")
        if _decision_token(choices[original]) != _decision_token(choices[repeat]):
            unstable.add(semantic)
    return tuple(sorted(unstable))


def _records(
    manifest: dict,
    internal_audit: dict,
    export: dict,
    *,
    expected_bucket: str,
    required_role: str,
    excluded_semantics: Iterable[str] = (),
) -> tuple[dict, ...]:
    choices = validate_choice_export(export, manifest, expected_bucket=expected_bucket)
    audit = _audit_by_task(internal_audit)
    excluded = set(excluded_semantics)
    out: list[dict] = []
    for task_id in sorted(choices):
        meta = audit.get(task_id)
        if meta is None or meta.get("role") != required_role:
            continue
        decision = choices[task_id]
        if decision["decision"] != DECISION_SELECT:
            continue
        task = manifest_task(manifest, task_id)
        if str(task["semantic_fingerprint"]) in excluded:
            continue
        assignments = recompute_assignment_map(task)
        selected = str(decision["selected_assignment_id"])
        if selected not in assignments:
            raise ValueError("S2-A.v2.1 selected assignment missing from fresh H-C.v2 output")
        family_id = str(meta.get("family_id", ""))
        if not family_id:
            raise ValueError("S2-A.v2.1 task missing family identity")
        out.append({
            "family_id": family_id,
            "task_id": task_id,
            "selected_assignment_id": selected,
            "assignments": assignments,
        })
    return tuple(out)


def _matrix(records: Iterable[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    X: list[np.ndarray] = []
    y: list[int] = []
    constraints = 0
    for row in records:
        preferred = np.asarray(
            quadratic_feature_vector(row["assignments"][row["selected_assignment_id"]]),
            dtype=np.float64,
        )
        for other_id, other in sorted(row["assignments"].items()):
            if other_id == row["selected_assignment_id"]:
                continue
            other_features = np.asarray(quadratic_feature_vector(other), dtype=np.float64)
            delta = preferred - other_features
            if not np.isfinite(delta).all():
                raise ValueError("S2-A.v2.1 pair delta must be finite")
            X.extend((delta, -delta))
            y.extend((1, 0))
            constraints += 1
    if not X:
        raise ValueError("S2-A.v2.1 has no stable preference constraints")
    matrix = np.asarray(X, dtype=np.float64)
    labels = np.asarray(y, dtype=np.int64)
    if matrix.shape != (2 * constraints, V21_EXPANDED_DIM):
        raise AssertionError("S2-A.v2.1 mirrored matrix shape mismatch")
    return matrix, labels, constraints


def _fit(records: Iterable[dict]):
    X, y, constraints = _matrix(records)
    scaler = StandardScaler(with_mean=False, with_std=True)
    X_scaled = scaler.fit_transform(X)
    model = LogisticRegression(
        penalty="l2",
        C=V21_C,
        fit_intercept=False,
        class_weight=None,
        solver="lbfgs",
        max_iter=5000,
        random_state=0,
    )
    model.fit(X_scaled, y)
    scale = np.asarray(scaler.scale_, dtype=np.float64)
    coef = np.asarray(model.coef_[0], dtype=np.float64)
    if scale.shape != (V21_EXPANDED_DIM,) or coef.shape != (V21_EXPANDED_DIM,):
        raise ValueError("S2-A.v2.1 fitted artifact dimension mismatch")
    if not np.isfinite(scale).all() or not np.isfinite(coef).all() or np.any(scale <= 0):
        raise ValueError("S2-A.v2.1 fitted artifact is non-finite")
    return scale, coef, constraints


def _score(scale: np.ndarray, coef: np.ndarray, assignment) -> float:
    vector = np.asarray(quadratic_feature_vector(assignment), dtype=np.float64)
    score = float(np.dot(coef, vector / scale))
    if not isfinite(score):
        raise ValueError("S2-A.v2.1 model produced non-finite score")
    return score


def _rank_model(scale: np.ndarray, coef: np.ndarray, assignments: dict) -> list[str]:
    return sorted(
        assignments,
        key=lambda item: (-_score(scale, coef, assignments[item]), item),
    )


def _rank_comparator(assignments: dict) -> list[str]:
    return sorted(assignments, key=lambda item: mechanical_complexity_key(assignments[item]))


def _fold_map(families: Iterable[str], folds: int = 5) -> dict[str, int]:
    unique = sorted(
        set(families),
        key=lambda value: sha256(
            f"{V21_PROTOCOL_VERSION}|FOLD|{value}".encode("utf-8")
        ).hexdigest(),
    )
    if len(unique) < folds:
        raise ValueError("S2-A.v2.1 needs at least one family per CV fold")
    return {family: index % folds for index, family in enumerate(unique)}


def _evaluate(scale: np.ndarray, coef: np.ndarray, records: Iterable[dict]) -> dict:
    rows = tuple(records)
    if not rows:
        raise ValueError("S2-A.v2.1 evaluation has no decisive tasks")
    details = []
    for row in rows:
        ranked = _rank_model(scale, coef, row["assignments"])
        baseline = _rank_comparator(row["assignments"])
        selected = row["selected_assignment_id"]
        mrank = ranked.index(selected) + 1
        brank = baseline.index(selected) + 1
        details.append({
            "family_id": row["family_id"],
            "task_id": row["task_id"],
            "model_rank": mrank,
            "baseline_rank": brank,
        })
    family_ids = sorted({row["family_id"] for row in details})
    panel = {}
    for family in family_ids:
        items = [row for row in details if row["family_id"] == family]
        panel[family] = {
            "model_top1": float(np.mean([row["model_rank"] == 1 for row in items])),
            "model_mrr": float(np.mean([1.0 / row["model_rank"] for row in items])),
            "baseline_top1": float(np.mean([row["baseline_rank"] == 1 for row in items])),
            "baseline_mrr": float(np.mean([1.0 / row["baseline_rank"] for row in items])),
        }
    model_macro_top1 = float(np.mean([v["model_top1"] for v in panel.values()]))
    baseline_macro_top1 = float(np.mean([v["baseline_top1"] for v in panel.values()]))
    return {
        "task_count": len(details),
        "family_count": len(panel),
        "top1_accuracy": float(np.mean([row["model_rank"] == 1 for row in details])),
        "mrr": float(np.mean([1.0 / row["model_rank"] for row in details])),
        "baseline_top1_accuracy": float(np.mean([row["baseline_rank"] == 1 for row in details])),
        "baseline_mrr": float(np.mean([1.0 / row["baseline_rank"] for row in details])),
        "macro_family_top1": model_macro_top1,
        "baseline_macro_family_top1": baseline_macro_top1,
        "macro_family_top1_delta": model_macro_top1 - baseline_macro_top1,
        "family_wins": sum(v["model_top1"] > v["baseline_top1"] for v in panel.values()),
        "family_ties": sum(v["model_top1"] == v["baseline_top1"] for v in panel.values()),
        "family_losses": sum(v["model_top1"] < v["baseline_top1"] for v in panel.values()),
        "family_panel": panel,
        "details": details,
    }


def _cv_once(records: tuple[dict, ...]) -> dict:
    fold_by_family = _fold_map(row["family_id"] for row in records)
    all_details = []
    for fold in range(5):
        train = tuple(row for row in records if fold_by_family[row["family_id"]] != fold)
        held = tuple(row for row in records if fold_by_family[row["family_id"]] == fold)
        scale, coef, _ = _fit(train)
        report = _evaluate(scale, coef, held)
        all_details.extend(report["details"])
    all_details.sort(key=lambda row: row["task_id"])
    signature = sha256(
        json.dumps(all_details, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    family_ids = sorted({row["family_id"] for row in all_details})
    panel = {}
    for family in family_ids:
        items = [row for row in all_details if row["family_id"] == family]
        panel[family] = {
            "model_top1": float(np.mean([row["model_rank"] == 1 for row in items])),
            "model_mrr": float(np.mean([1.0 / row["model_rank"] for row in items])),
            "baseline_top1": float(np.mean([row["baseline_rank"] == 1 for row in items])),
            "baseline_mrr": float(np.mean([1.0 / row["baseline_rank"] for row in items])),
        }
    macro = float(np.mean([v["model_top1"] for v in panel.values()]))
    base_macro = float(np.mean([v["baseline_top1"] for v in panel.values()]))
    return {
        "signature": signature,
        "task_count": len(all_details),
        "family_count": len(panel),
        "top1_accuracy": float(np.mean([row["model_rank"] == 1 for row in all_details])),
        "mrr": float(np.mean([1.0 / row["model_rank"] for row in all_details])),
        "macro_family_top1": macro,
        "baseline_macro_family_top1": base_macro,
        "macro_family_top1_delta": macro - base_macro,
        "family_wins": sum(v["model_top1"] > v["baseline_top1"] for v in panel.values()),
        "family_ties": sum(v["model_top1"] == v["baseline_top1"] for v in panel.values()),
        "family_losses": sum(v["model_top1"] < v["baseline_top1"] for v in panel.values()),
    }


def development_recovery_report(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> dict:
    original_reliability = reliability_report(development_export, manifest, internal_audit)
    unstable = unstable_repeat_semantics(manifest, internal_audit, development_export)
    records = _records(
        manifest,
        internal_audit,
        development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
        excluded_semantics=unstable,
    )
    _, _, constraints = _matrix(records)
    reports = [_cv_once(records) for _ in range(10)]
    signatures = [row["signature"] for row in reports]
    cv = reports[0]
    checks = {
        "stable_decisive_development_tasks_gte_160": len(records) >= 160,
        "stable_development_families_gte_20": len({row["family_id"] for row in records}) >= 20,
        "stable_preference_constraints_gte_200": constraints >= 200,
        "cv_top1_gte_0_60": cv["top1_accuracy"] >= 0.60,
        "cv_mrr_gte_0_75": cv["mrr"] >= 0.75,
        "cv_macro_family_top1_gte_0_60": cv["macro_family_top1"] >= 0.60,
        "cv_macro_family_top1_delta_gte_0_05": cv["macro_family_top1_delta"] >= 0.05,
        "family_wins_gt_losses": cv["family_wins"] > cv["family_losses"],
        "deterministic_10_of_10": len(set(signatures)) == 1,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "v2_original_status": "FAIL_DO_NOT_RECLASSIFY",
        "original_v2_reliability": original_reliability,
        "unstable_repeat_semantics_count": len(unstable),
        "unstable_repeat_semantics_sha256": sha256(
            json.dumps(unstable, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "unstable_repeat_semantics_excluded_from_fit": True,
        "stable_decisive_development_tasks": len(records),
        "stable_development_families": len({row["family_id"] for row in records}),
        "stable_preference_constraints": constraints,
        "checks": checks,
        "cv": cv,
        "determinism_signatures": signatures,
        "development_informed_model_revision": True,
        "final_labels_opened_during_model_revision": False,
    }


def fit_and_seal_development_recovery(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> dict:
    gate = development_recovery_report(manifest, internal_audit, development_export)
    if gate["status"] != "PASS":
        raise RuntimeError("S2-A.v2.1 development recovery gate is CLOSED")
    unstable = unstable_repeat_semantics(manifest, internal_audit, development_export)
    records = _records(
        manifest,
        internal_audit,
        development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
        excluded_semantics=unstable,
    )
    scale, coef, constraints = _fit(records)
    artifact = {
        "schema": V21_MODEL_SCHEMA,
        "model_version": V21_MODEL_VERSION,
        "protocol_version": V21_PROTOCOL_VERSION,
        "teacher_protocol_version": S2A_V2_PROTOCOL_VERSION,
        "base_feature_list_sha256": S2A_FEATURE_LIST_SHA256,
        "expanded_feature_list_sha256": V21_FEATURE_LIST_SHA256,
        "expanded_feature_dimension": V21_EXPANDED_DIM,
        "comparator": COMPARATOR_VERSION,
        "training_role": "DEVELOPMENT_ORIGINAL_DECISIVE_REPEAT_CONSISTENT_ONLY",
        "development_recovery_gate": gate,
        "training_task_count": len(records),
        "training_constraint_count": constraints,
        "manifest_sha256": manifest["manifest_sha256"],
        "internal_audit_sha256": canonical_sha256(internal_audit),
        "development_export_sha256": canonical_sha256(development_export),
        "pipeline": {
            "feature_map": "DETERMINISTIC_LINEAR_PLUS_ALL_I_LE_J_QUADRATIC_TERMS",
            "scaler": "StandardScaler(with_mean=False,with_std=True)",
            "estimator": "LogisticRegression",
            "params": {
                "penalty": "l2",
                "C": V21_C,
                "fit_intercept": False,
                "class_weight": None,
                "solver": "lbfgs",
                "max_iter": 5000,
                "random_state": 0,
            },
        },
        "scaler_scale_hex": [float(value).hex() for value in scale],
        "logistic_coef_hex": [float(value).hex() for value in coef],
        "status": "DEVELOPMENT_RECOVERY_PASS_MODEL_SEALED_FINAL_MAY_OPEN_ONCE",
        "model_sealed": True,
        "final_access_authorized": True,
        "final_access_count_authorized": 1,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    artifact["artifact_sha256"] = canonical_sha256(artifact)
    return artifact


def _verify_model(artifact: dict) -> tuple[np.ndarray, np.ndarray]:
    digest = artifact.get("artifact_sha256")
    if not isinstance(digest, str):
        raise ValueError("S2-A.v2.1 model artifact is unsealed")
    payload = dict(artifact)
    payload.pop("artifact_sha256", None)
    if canonical_sha256(payload) != digest:
        raise ValueError("S2-A.v2.1 model artifact SHA mismatch")
    if artifact.get("schema") != V21_MODEL_SCHEMA or artifact.get("model_version") != V21_MODEL_VERSION:
        raise ValueError("unexpected S2-A.v2.1 model identity")
    if artifact.get("expanded_feature_list_sha256") != V21_FEATURE_LIST_SHA256:
        raise ValueError("S2-A.v2.1 expanded feature-list drift")
    if artifact.get("model_sealed") is not True or artifact.get("final_access_authorized") is not True:
        raise ValueError("S2-A.v2.1 final remains closed")
    scale = np.asarray([float.fromhex(x) for x in artifact.get("scaler_scale_hex", [])], dtype=np.float64)
    coef = np.asarray([float.fromhex(x) for x in artifact.get("logistic_coef_hex", [])], dtype=np.float64)
    if scale.shape != (V21_EXPANDED_DIM,) or coef.shape != (V21_EXPANDED_DIM,):
        raise ValueError("S2-A.v2.1 model artifact dimension mismatch")
    if not np.isfinite(scale).all() or not np.isfinite(coef).all() or np.any(scale <= 0):
        raise ValueError("S2-A.v2.1 model artifact is non-finite")
    return scale, coef


def _bootstrap_lower_mrr_delta(family_panel: dict[str, dict], repetitions: int = 2000) -> float:
    families = sorted(family_panel)
    if len(families) < 2:
        raise ValueError("S2-A.v2.1 final bootstrap needs multiple families")
    rng = Random(0)
    values = []
    for _ in range(repetitions):
        sampled = [families[rng.randrange(len(families))] for _ in families]
        values.append(float(np.mean([
            family_panel[family]["model_mrr"] - family_panel[family]["baseline_mrr"]
            for family in sampled
        ])))
    values.sort()
    return values[49]


def evaluate_untouched_final_recovery(
    manifest: dict,
    internal_audit: dict,
    final_export: dict,
    sealed_model_artifact: dict,
) -> dict:
    scale, coef = _verify_model(sealed_model_artifact)
    records = _records(
        manifest,
        internal_audit,
        final_export,
        expected_bucket=BUCKET_FINAL,
        required_role="UNTOUCHED_FINAL",
    )
    panel = _evaluate(scale, coef, records)
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
        "schema": V21_FINAL_SCHEMA,
        "protocol_version": V21_PROTOCOL_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metrics": panel,
        "bootstrap_repetitions": 2000,
        "bootstrap_seed": 0,
        "bootstrap_95pct_mrr_delta_lower": lower,
        "model_artifact_sha256": sealed_model_artifact["artifact_sha256"],
        "final_export_sha256": canonical_sha256(final_export),
        "final_opened_after_model_seal": True,
        "final_access_count_used": 1,
        "checkpoint_retention_eligibility": "ELIGIBLE_FOR_SEPARATE_REVIEW" if all(checks.values()) else "NOT_ELIGIBLE",
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    result["result_sha256"] = canonical_sha256(result)
    return result
