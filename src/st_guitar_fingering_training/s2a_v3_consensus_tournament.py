from __future__ import annotations

from hashlib import sha256
import json
from math import isfinite
from typing import Callable, Iterable

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier

from .s2a_features import assignment_feature_vector
from .s2a_v2_fixed_voicing import (
    BUCKET_DEVELOPMENT,
    BUCKET_FINAL,
    DECISION_SELECT,
    S2A_V2_AUDIT_SCHEMA,
    S2A_V2_PROTOCOL_VERSION,
    canonical_sha256,
    manifest_task,
    recompute_assignment_map,
    validate_choice_export,
)
from .s2a_v2_ranker import mechanical_complexity_key


S2A_V3_PROTOCOL_VERSION = "S2-A.v3-CONSENSUS-TOURNAMENT.v1"
S2A_V3_MODEL_VERSION = "S2-A.v3-EXTRATREES-PAIRWISE-TOURNAMENT.v1"
S2A_V3_EXECUTION_SCHEMA = "st-guitar-s2a-v3-post-session-execution-v1"
S2A_V3_MODEL_SCHEMA = "st-guitar-s2a-v3-development-model-v1"
S2A_V3_FINAL_SCHEMA = "st-guitar-s2a-v3-untouched-final-result-v1"

# Frozen after S2-A.v2 DEVELOPMENT failure and before opening FINAL.
TREE_COUNT = 250
MIN_SAMPLES_LEAF = 4
MAX_FEATURES = "sqrt"
RANDOM_STATE = 0
REPEAT_MINIMUM = 0.80
CV_TOP1_MINIMUM = 0.60
CV_MRR_MINIMUM = 0.75
CV_MACRO_TOP1_MINIMUM = 0.60
CV_MACRO_DELTA_MINIMUM = 0.05
FINAL_TOP1_MINIMUM = 0.60
FINAL_MRR_MINIMUM = 0.75
FINAL_MACRO_TOP1_MINIMUM = 0.60
FINAL_MACRO_DELTA_MINIMUM = 0.05


def _audit_by_task(internal_audit: dict) -> dict[str, dict]:
    if internal_audit.get("schema") != S2A_V2_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A.v2 audit schema")
    rows = internal_audit.get("rows")
    if not isinstance(rows, list):
        raise ValueError("S2-A.v3 audit rows must be a list")
    out: dict[str, dict] = {}
    for row in rows:
        task_id = str(row.get("task_id", ""))
        if not task_id or task_id in out:
            raise ValueError("S2-A.v3 audit has blank/duplicate task identity")
        out[task_id] = row
    return out


def _decision_token(decision: dict) -> tuple[str, str | None]:
    label = str(decision.get("decision", ""))
    selected = decision.get("selected_assignment_id") if label == DECISION_SELECT else None
    return label, None if selected is None else str(selected)


def consensus_quarantine_report(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> dict:
    choices = validate_choice_export(
        development_export,
        manifest,
        expected_bucket=BUCKET_DEVELOPMENT,
    )
    pairs = internal_audit.get("repeat_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("S2-A.v3 requires hidden repeat pairs")

    stable_semantics: set[str] = set()
    quarantined_semantics: set[str] = set()
    agreements = 0
    for pair in pairs:
        original = str(pair.get("original_task_id", ""))
        repeat = str(pair.get("repeat_task_id", ""))
        semantic = str(pair.get("semantic_fingerprint", ""))
        if original not in choices or repeat not in choices or not semantic:
            raise ValueError("S2-A.v3 repeat pair identity mismatch")
        original_task = manifest_task(manifest, original)
        repeat_task = manifest_task(manifest, repeat)
        if original_task.get("semantic_fingerprint") != semantic:
            raise ValueError("S2-A.v3 original repeat semantic mismatch")
        if repeat_task.get("semantic_fingerprint") != semantic:
            raise ValueError("S2-A.v3 hidden repeat semantic mismatch")
        if _decision_token(choices[original]) == _decision_token(choices[repeat]):
            agreements += 1
            stable_semantics.add(semantic)
        else:
            quarantined_semantics.add(semantic)

    if stable_semantics & quarantined_semantics:
        raise AssertionError("S2-A.v3 semantic cannot be stable and quarantined")
    exact = agreements / len(pairs)
    return {
        "status": "PASS" if exact >= REPEAT_MINIMUM else "FAIL",
        "repeat_pairs": len(pairs),
        "exact_assignment_or_class_agreement": exact,
        "minimum_required_agreement": REPEAT_MINIMUM,
        "stable_repeat_pairs": agreements,
        "quarantined_repeat_pairs": len(pairs) - agreements,
        "quarantined_semantic_fingerprints": sorted(quarantined_semantics),
        "quarantined_repeat_rows_trainable": False,
        "protocol_adapted_after_v2_development_failure": True,
        "final_opened_during_protocol_adaptation": False,
    }


def _records(
    manifest: dict,
    internal_audit: dict,
    export: dict,
    *,
    expected_bucket: str,
    required_role: str,
    quarantined_semantics: set[str] | None = None,
) -> tuple[dict, ...]:
    choices = validate_choice_export(export, manifest, expected_bucket=expected_bucket)
    audit = _audit_by_task(internal_audit)
    quarantine = quarantined_semantics or set()
    out: list[dict] = []
    for task_id in sorted(choices):
        meta = audit.get(task_id)
        if meta is None or meta.get("role") != required_role:
            continue
        decision = choices[task_id]
        if decision.get("decision") != DECISION_SELECT:
            continue
        task = manifest_task(manifest, task_id)
        semantic = str(task.get("semantic_fingerprint", ""))
        if semantic in quarantine:
            continue
        assignments = recompute_assignment_map(task)
        selected = str(decision.get("selected_assignment_id", ""))
        if selected not in assignments:
            raise ValueError("S2-A.v3 selected assignment missing from fresh H-C.v2 output")
        family_id = str(meta.get("family_id", ""))
        if not family_id:
            raise ValueError("S2-A.v3 record missing family identity")
        out.append({
            "family_id": family_id,
            "task_id": task_id,
            "selected_assignment_id": selected,
            "assignments": assignments,
        })
    return tuple(out)


def _pair_matrix(records: Iterable[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    X: list[np.ndarray] = []
    y: list[int] = []
    preference_constraints = 0
    for row in records:
        selected = row["assignments"][row["selected_assignment_id"]]
        selected_features = np.asarray(assignment_feature_vector(selected), dtype=np.float64)
        for other_id, other in sorted(row["assignments"].items()):
            if other_id == row["selected_assignment_id"]:
                continue
            other_features = np.asarray(assignment_feature_vector(other), dtype=np.float64)
            delta = selected_features - other_features
            if delta.shape != (30,) or not np.isfinite(delta).all():
                raise ValueError("S2-A.v3 pair delta must be finite 30D")
            X.extend((delta, -delta))
            y.extend((1, 0))
            preference_constraints += 1
    if not X:
        raise ValueError("S2-A.v3 has no decisive preference constraints")
    matrix = np.asarray(X, dtype=np.float64)
    labels = np.asarray(y, dtype=np.int64)
    return matrix, labels, preference_constraints


def _build_model() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=TREE_COUNT,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        max_features=MAX_FEATURES,
        random_state=RANDOM_STATE,
        n_jobs=1,
        bootstrap=False,
    )


def _fit(records: tuple[dict, ...]) -> ExtraTreesClassifier:
    X, y, _ = _pair_matrix(records)
    model = _build_model()
    model.fit(X, y)
    if tuple(int(value) for value in model.classes_) != (0, 1):
        raise AssertionError("S2-A.v3 classifier classes drifted")
    return model


def _rank_tournament(model: ExtraTreesClassifier, assignments: dict) -> list[str]:
    ids = sorted(assignments)
    if len(ids) < 2:
        raise ValueError("S2-A.v3 tournament requires at least two assignments")
    features = {
        assignment_id: np.asarray(assignment_feature_vector(assignment), dtype=np.float64)
        for assignment_id, assignment in assignments.items()
    }
    pair_rows: list[np.ndarray] = []
    owners: list[str] = []
    for left in ids:
        for right in ids:
            if left == right:
                continue
            pair_rows.append(features[left] - features[right])
            owners.append(left)
    probabilities = model.predict_proba(np.asarray(pair_rows, dtype=np.float64))[:, 1]
    scores = {assignment_id: 0.0 for assignment_id in ids}
    for owner, probability in zip(owners, probabilities):
        probability = float(probability)
        if not isfinite(probability):
            raise ValueError("S2-A.v3 model produced non-finite probability")
        scores[owner] += probability
    return sorted(ids, key=lambda assignment_id: (-scores[assignment_id], assignment_id))


def _rank_baseline(assignments: dict) -> list[str]:
    return sorted(assignments, key=lambda item: mechanical_complexity_key(assignments[item]))


def _fold_map(families: Iterable[str], folds: int = 5) -> dict[str, int]:
    # Keep the exact v2 family split contract. Only the ranker changes in v3.
    unique = sorted(set(families), key=lambda value: sha256(
        f"{S2A_V2_PROTOCOL_VERSION}|FOLD|{value}".encode("utf-8")
    ).hexdigest())
    if len(unique) < folds:
        raise ValueError("S2-A.v3 needs at least one family per CV fold")
    return {family: index % folds for index, family in enumerate(unique)}


def _aggregate(details: list[dict]) -> dict:
    if not details:
        raise ValueError("S2-A.v3 evaluation has no decisive tasks")
    family_ids = sorted({row["family_id"] for row in details})
    family_panel = {}
    for family in family_ids:
        rows = [row for row in details if row["family_id"] == family]
        family_panel[family] = {
            "model_top1": float(np.mean([row["model_rank"] == 1 for row in rows])),
            "model_mrr": float(np.mean([1.0 / row["model_rank"] for row in rows])),
            "baseline_top1": float(np.mean([row["baseline_rank"] == 1 for row in rows])),
            "baseline_mrr": float(np.mean([1.0 / row["baseline_rank"] for row in rows])),
        }
    model_top1 = float(np.mean([row["model_rank"] == 1 for row in details]))
    model_mrr = float(np.mean([1.0 / row["model_rank"] for row in details]))
    baseline_top1 = float(np.mean([row["baseline_rank"] == 1 for row in details]))
    baseline_mrr = float(np.mean([1.0 / row["baseline_rank"] for row in details]))
    macro_top1 = float(np.mean([row["model_top1"] for row in family_panel.values()]))
    macro_mrr = float(np.mean([row["model_mrr"] for row in family_panel.values()]))
    baseline_macro_top1 = float(np.mean([row["baseline_top1"] for row in family_panel.values()]))
    baseline_macro_mrr = float(np.mean([row["baseline_mrr"] for row in family_panel.values()]))
    return {
        "task_count": len(details),
        "family_count": len(family_panel),
        "top1_accuracy": model_top1,
        "mrr": model_mrr,
        "baseline_top1_accuracy": baseline_top1,
        "baseline_mrr": baseline_mrr,
        "macro_family_top1": macro_top1,
        "macro_family_mrr": macro_mrr,
        "baseline_macro_family_top1": baseline_macro_top1,
        "baseline_macro_family_mrr": baseline_macro_mrr,
        "macro_family_top1_delta": macro_top1 - baseline_macro_top1,
        "macro_family_mrr_delta": macro_mrr - baseline_macro_mrr,
        "family_wins": sum(v["model_top1"] > v["baseline_top1"] for v in family_panel.values()),
        "family_ties": sum(v["model_top1"] == v["baseline_top1"] for v in family_panel.values()),
        "family_losses": sum(v["model_top1"] < v["baseline_top1"] for v in family_panel.values()),
        "family_panel": family_panel,
    }


def _evaluate(model: ExtraTreesClassifier, records: tuple[dict, ...]) -> dict:
    details: list[dict] = []
    for row in records:
        ranked = _rank_tournament(model, row["assignments"])
        baseline = _rank_baseline(row["assignments"])
        selected = row["selected_assignment_id"]
        details.append({
            "family_id": row["family_id"],
            "task_id": row["task_id"],
            "model_rank": ranked.index(selected) + 1,
            "baseline_rank": baseline.index(selected) + 1,
        })
    report = _aggregate(details)
    report["prediction_signature"] = sha256(json.dumps(
        sorted((row["task_id"], row["model_rank"], row["baseline_rank"]) for row in details),
        separators=(",", ":"),
    ).encode("ascii")).hexdigest()
    return report


def _cv_once(records: tuple[dict, ...]) -> dict:
    fold_by_family = _fold_map(row["family_id"] for row in records)
    all_details: list[dict] = []
    for fold in range(5):
        train = tuple(row for row in records if fold_by_family[row["family_id"]] != fold)
        held = tuple(row for row in records if fold_by_family[row["family_id"]] == fold)
        if not train or not held:
            raise ValueError("S2-A.v3 CV produced empty train/held fold")
        model = _fit(train)
        for row in held:
            ranked = _rank_tournament(model, row["assignments"])
            baseline = _rank_baseline(row["assignments"])
            selected = row["selected_assignment_id"]
            all_details.append({
                "family_id": row["family_id"],
                "task_id": row["task_id"],
                "model_rank": ranked.index(selected) + 1,
                "baseline_rank": baseline.index(selected) + 1,
            })
    all_details.sort(key=lambda row: row["task_id"])
    report = _aggregate(all_details)
    report["signature"] = sha256(json.dumps(
        [(row["task_id"], row["model_rank"], row["baseline_rank"]) for row in all_details],
        separators=(",", ":"),
    ).encode("ascii")).hexdigest()
    return report


def development_gate_report(manifest: dict, internal_audit: dict, development_export: dict) -> dict:
    consensus = consensus_quarantine_report(manifest, internal_audit, development_export)
    quarantine = set(consensus["quarantined_semantic_fingerprints"])
    records = _records(
        manifest,
        internal_audit,
        development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
        quarantined_semantics=quarantine,
    )
    _, _, constraints = _pair_matrix(records)
    reports = [_cv_once(records) for _ in range(10)]
    signatures = [row["signature"] for row in reports]
    deterministic = len(set(signatures)) == 1
    cv = reports[0]
    checks = {
        "repeat_consensus_gte_0_80": consensus["status"] == "PASS",
        "all_repeat_disagreements_quarantined": len(quarantine) == consensus["quarantined_repeat_pairs"],
        "stable_decisive_development_tasks_gte_160": len(records) >= 160,
        "development_families_gte_20": len({row["family_id"] for row in records}) >= 20,
        "preference_constraints_gte_200": constraints >= 200,
        "cv_top1_gte_0_60": float(cv["top1_accuracy"]) >= CV_TOP1_MINIMUM,
        "cv_mrr_gte_0_75": float(cv["mrr"]) >= CV_MRR_MINIMUM,
        "cv_macro_family_top1_gte_0_60": float(cv["macro_family_top1"]) >= CV_MACRO_TOP1_MINIMUM,
        "cv_macro_family_top1_delta_gte_0_05": float(cv["macro_family_top1_delta"]) >= CV_MACRO_DELTA_MINIMUM,
        "family_wins_gt_losses": int(cv["family_wins"]) > int(cv["family_losses"]),
        "deterministic_10_of_10": deterministic,
    }
    return {
        "protocol_version": S2A_V3_PROTOCOL_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "consensus_quarantine": consensus,
        "stable_decisive_development_tasks": len(records),
        "development_families": len({row["family_id"] for row in records}),
        "preference_constraints": constraints,
        "cv": cv,
        "determinism_signatures": signatures,
    }


def _model_digest(model: ExtraTreesClassifier) -> str:
    digest = sha256()
    digest.update(S2A_V3_MODEL_VERSION.encode("ascii"))
    digest.update(str(model.get_params(deep=False)).encode("utf-8"))
    for estimator in model.estimators_:
        tree = estimator.tree_
        for array in (
            tree.children_left,
            tree.children_right,
            tree.feature,
            tree.threshold,
            tree.value,
        ):
            digest.update(np.asarray(array).tobytes(order="C"))
    return digest.hexdigest()


def fit_and_seal_development_model(
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
) -> tuple[ExtraTreesClassifier, dict]:
    gate = development_gate_report(manifest, internal_audit, development_export)
    if gate["status"] != "PASS":
        raise RuntimeError("S2-A.v3 development gate closed")
    quarantine = set(gate["consensus_quarantine"]["quarantined_semantic_fingerprints"])
    records = _records(
        manifest,
        internal_audit,
        development_export,
        expected_bucket=BUCKET_DEVELOPMENT,
        required_role="DEVELOPMENT_ORIGINAL",
        quarantined_semantics=quarantine,
    )
    model = _fit(records)
    artifact = {
        "schema": S2A_V3_MODEL_SCHEMA,
        "protocol_version": S2A_V3_PROTOCOL_VERSION,
        "model_version": S2A_V3_MODEL_VERSION,
        "manifest_sha256": manifest.get("manifest_sha256"),
        "development_export_sha256": canonical_sha256(development_export),
        "development_gate": gate,
        "training_record_count": len(records),
        "quarantined_semantic_fingerprints": sorted(quarantine),
        "model_parameters": {
            "n_estimators": TREE_COUNT,
            "min_samples_leaf": MIN_SAMPLES_LEAF,
            "max_features": MAX_FEATURES,
            "random_state": RANDOM_STATE,
            "n_jobs": 1,
            "bootstrap": False,
        },
        "model_sha256": _model_digest(model),
        "model_sealed": True,
        "final_access_authorized": True,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    artifact["artifact_sha256"] = canonical_sha256(artifact)
    return model, artifact


def evaluate_untouched_final(
    manifest: dict,
    internal_audit: dict,
    final_export: dict,
    model: ExtraTreesClassifier,
    model_artifact: dict,
) -> dict:
    if model_artifact.get("model_sealed") is not True or model_artifact.get("final_access_authorized") is not True:
        raise RuntimeError("S2-A.v3 final access requires sealed development model")
    records = _records(
        manifest,
        internal_audit,
        final_export,
        expected_bucket=BUCKET_FINAL,
        required_role="UNTOUCHED_FINAL",
    )
    report = _evaluate(model, records)
    checks = {
        "final_top1_gte_0_60": float(report["top1_accuracy"]) >= FINAL_TOP1_MINIMUM,
        "final_mrr_gte_0_75": float(report["mrr"]) >= FINAL_MRR_MINIMUM,
        "final_macro_family_top1_gte_0_60": float(report["macro_family_top1"]) >= FINAL_MACRO_TOP1_MINIMUM,
        "final_macro_family_top1_delta_gte_0_05": float(report["macro_family_top1_delta"]) >= FINAL_MACRO_DELTA_MINIMUM,
        "family_wins_gt_losses": int(report["family_wins"]) > int(report["family_losses"]),
    }
    result = {
        "schema": S2A_V3_FINAL_SCHEMA,
        "protocol_version": S2A_V3_PROTOCOL_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "model_artifact_sha256": model_artifact.get("artifact_sha256"),
        "final_export_sha256": canonical_sha256(final_export),
        "metrics": report,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    result["result_sha256"] = canonical_sha256(result)
    return result


def execute_after_teacher_session(
    *,
    manifest: dict,
    internal_audit: dict,
    development_export: dict,
    final_loader: Callable[[], dict],
) -> tuple[dict, dict, dict]:
    model, artifact = fit_and_seal_development_model(
        manifest,
        internal_audit,
        development_export,
    )
    final_export = final_loader()
    if not isinstance(final_export, dict):
        raise ValueError("S2-A.v3 FINAL loader must return a JSON object")
    final_result = evaluate_untouched_final(
        manifest,
        internal_audit,
        final_export,
        model,
        artifact,
    )
    execution = {
        "schema": S2A_V3_EXECUTION_SCHEMA,
        "protocol_version": S2A_V3_PROTOCOL_VERSION,
        "status": (
            "TEACHER_FIT_AND_FINAL_PASS"
            if final_result["status"] == "PASS"
            else "TEACHER_FIT_PASS_FINAL_FAIL"
        ),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "development_model_artifact_sha256": artifact.get("artifact_sha256"),
        "final_result_sha256": final_result.get("result_sha256"),
        "final_file_opened_only_after_v3_development_model_seal": True,
        "v2_failure_preserved": True,
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    execution["execution_sha256"] = canonical_sha256(execution)
    return artifact, final_result, execution
