from __future__ import annotations

from hashlib import sha256
import json
import math

import numpy as np

from .guitarset_teacher_voicing import (
    DECISION_MANUAL_VOICING,
    DECISION_SELECT_OPTION,
    TEACHER_VOICING_AUDIT_SCHEMA,
    TEACHER_VOICING_PILOT_VERSION,
    candidate_id,
    canonical_candidate as canonical_teacher_candidate,
    parse_manual_voicing,
    validate_teacher_voicing_export,
)
from .guitarset_voicing_development import (
    feature_vector,
    low_total_fret_key,
    verify_sealed_json,
)
from .guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
)

ALIGNMENT_SCHEMA = "st-guitar-guitarset-teacher-model-alignment-v1"
ALIGNMENT_VERSION = "GUITARSET-TEACHER-MODEL-ALIGNMENT.v1"
EXPECTED_MODEL_SCHEMA = "st-guitar-guitarset-observed-voicing-development-model-v1"
EXPECTED_MODEL_VERSION = "GUITARSET-OBSERVED-VOICING-MODEL.v1"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _candidate_from_option(option: dict) -> tuple[tuple[int, int, int], ...]:
    placements = option.get("placements")
    if not isinstance(placements, list):
        raise ValueError("Teacher Voicing option placements must be a list")
    rows = []
    for row in placements:
        if not isinstance(row, dict):
            raise ValueError("Teacher Voicing option placement must be an object")
        rows.append((int(row["pitch_midi"]), int(row["string"]), int(row["fret"])))
    candidate = canonical_teacher_candidate(rows)
    if option.get("candidate_id") != candidate_id(candidate):
        raise ValueError("Teacher Voicing option candidate ID mismatch")
    return candidate


def _load_model_parameters(model_artifact: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    verify_sealed_json(model_artifact, "artifact_sha256")
    if model_artifact.get("schema") != EXPECTED_MODEL_SCHEMA:
        raise ValueError("unexpected GuitarSet DEVELOPMENT model schema")
    if model_artifact.get("model_version") != EXPECTED_MODEL_VERSION:
        raise ValueError("unexpected GuitarSet DEVELOPMENT model version")
    if model_artifact.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
        raise ValueError("GuitarSet DEVELOPMENT model protocol drift")
    if model_artifact.get("feature_schema_sha256") != EXPECTED_FEATURE_SCHEMA_SHA256:
        raise ValueError("GuitarSet DEVELOPMENT model feature-schema drift")
    if model_artifact.get("training_role") != "DEVELOPMENT":
        raise ValueError("Teacher/model alignment accepts DEVELOPMENT-trained model only")
    if model_artifact.get("validation_only_artifact") is not True:
        raise ValueError("Teacher/model alignment requires validation-only sealed model")
    if model_artifact.get("checkpoint_authorized") is not False:
        raise ValueError("Teacher/model alignment cannot consume checkpoint-authorized artifact")
    if model_artifact.get("runtime_connection_authorized") is not False:
        raise ValueError("Teacher/model alignment cannot consume runtime-authorized artifact")
    if model_artifact.get("scoring") != "dot((features-mean)/scale, coef)":
        raise ValueError("unexpected GuitarSet DEVELOPMENT model scoring contract")

    expected_pipeline = {
        "scaler": "StandardScaler",
        "estimator": "LogisticRegression",
        "params": {
            "C": 1.0,
            "fit_intercept": False,
            "class_weight": None,
            "solver": "lbfgs",
            "max_iter": 2000,
            "random_state": 0,
        },
    }
    if model_artifact.get("pipeline") != expected_pipeline:
        raise ValueError("GuitarSet DEVELOPMENT model pipeline drift")

    parameters = model_artifact.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("missing GuitarSet DEVELOPMENT model parameters")
    try:
        mean = np.asarray([float.fromhex(value) for value in parameters["scaler_mean_hex"]], dtype=np.float64)
        scale = np.asarray([float.fromhex(value) for value in parameters["scaler_scale_hex"]], dtype=np.float64)
        coef = np.asarray([float.fromhex(value) for value in parameters["logistic_coef_hex"]], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid GuitarSet DEVELOPMENT model parameters") from exc
    if mean.shape != (28,) or scale.shape != (28,) or coef.shape != (28,):
        raise ValueError("GuitarSet DEVELOPMENT model must expose exactly 28 parameters per vector")
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or not np.isfinite(coef).all():
        raise ValueError("GuitarSet DEVELOPMENT model parameters must be finite")
    if not (scale > 0).all():
        raise ValueError("GuitarSet DEVELOPMENT scaler scale must be strictly positive")
    return mean, scale, coef


def _score_candidate(
    candidate: tuple[tuple[int, int, int], ...],
    *,
    mean: np.ndarray,
    scale: np.ndarray,
    coef: np.ndarray,
) -> float:
    features = np.asarray(feature_vector(candidate), dtype=np.float64)
    score = float(np.dot((features - mean) / scale, coef))
    if not math.isfinite(score):
        raise ValueError("non-finite GuitarSet DEVELOPMENT model score")
    return score


def _teacher_candidate_id(decision: dict, task: dict) -> str | None:
    mode = decision.get("decision")
    if mode == DECISION_SELECT_OPTION:
        return str(decision.get("selected_candidate_id"))
    if mode == DECISION_MANUAL_VOICING:
        manual = parse_manual_voicing(
            str(decision.get("manual_voicing") or ""),
            pitches_midi=task["pitches_midi"],
        )
        return candidate_id(manual)
    return None


def analyze_teacher_model_alignment(
    *,
    choices: dict,
    choices_sha256: str,
    manifest: dict,
    internal_audit: dict,
    model_artifact: dict,
) -> dict:
    if not isinstance(choices_sha256, str) or len(choices_sha256) != 64:
        raise ValueError("choices_sha256 must be a lowercase SHA-256 hex digest")
    try:
        int(choices_sha256, 16)
    except ValueError as exc:
        raise ValueError("choices_sha256 must be a SHA-256 hex digest") from exc
    if choices_sha256.lower() != choices_sha256:
        raise ValueError("choices_sha256 must use lowercase hex")

    validate_teacher_voicing_export(choices, manifest)
    if manifest.get("protocol_version") != TEACHER_VOICING_PILOT_VERSION:
        raise ValueError("Teacher Voicing manifest protocol drift")
    if manifest.get("diagnostic_only_never_training") is not True:
        raise ValueError("Teacher/model alignment requires diagnostic-only Teacher manifest")
    for field in (
        "training_authorized",
        "validation_access_authorized",
        "final_access_authorized",
        "checkpoint_authorized",
        "runtime_connection_authorized",
    ):
        if manifest.get(field) is not False:
            raise ValueError(f"Teacher/model alignment requires {field}=false")

    if internal_audit.get("schema") != TEACHER_VOICING_AUDIT_SCHEMA:
        raise ValueError("unexpected Teacher Voicing internal-audit schema")
    if internal_audit.get("protocol_version") != TEACHER_VOICING_PILOT_VERSION:
        raise ValueError("Teacher Voicing internal-audit protocol drift")
    if internal_audit.get("source_role") != "DEVELOPMENT_ONLY":
        raise ValueError("Teacher/model alignment accepts DEVELOPMENT-only pilot audit")
    if internal_audit.get("teacher_manifest_sha256") != manifest.get("manifest_sha256"):
        raise ValueError("Teacher Voicing audit/manifest mismatch")
    if internal_audit.get("validation_performer_opened") is not False:
        raise ValueError("Teacher/model alignment must not open validation performer")
    if internal_audit.get("untouched_final_performer_opened") is not False:
        raise ValueError("Teacher/model alignment must not open untouched-final performer")
    for field in ("training_authorized", "checkpoint_authorized", "runtime_connection_authorized"):
        if internal_audit.get(field) is not False:
            raise ValueError(f"Teacher/model alignment requires audit {field}=false")

    mean, scale, coef = _load_model_parameters(model_artifact)

    tasks = manifest.get("tasks")
    audit_rows = internal_audit.get("rows")
    decisions = choices.get("decisions")
    if not isinstance(tasks, list) or not isinstance(audit_rows, list) or not isinstance(decisions, list):
        raise ValueError("Teacher/model alignment inputs must contain list rows")
    task_by_id = {str(task["task_id"]): task for task in tasks}
    audit_by_id = {str(row["task_id"]): row for row in audit_rows}
    decision_by_id = {str(row["task_id"]): row for row in decisions}
    if len(task_by_id) != len(tasks) or len(audit_by_id) != len(audit_rows) or len(decision_by_id) != len(decisions):
        raise ValueError("Teacher/model alignment rejects duplicate task IDs")
    if set(task_by_id) != set(audit_by_id) or set(task_by_id) != set(decision_by_id):
        raise ValueError("Teacher/model alignment requires exact task coverage")

    counts = {
        "all_three_same": 0,
        "teacher_observed_same_model_diff": 0,
        "model_observed_same_teacher_diff": 0,
        "teacher_model_same_observed_diff": 0,
        "all_three_different": 0,
    }
    decisive = 0
    teacher_observed = 0
    model_observed = 0
    teacher_model = 0
    baseline_observed = 0
    baseline_teacher = 0

    for task_id in [str(task["task_id"]) for task in tasks]:
        task = task_by_id[task_id]
        audit = audit_by_id[task_id]
        decision = decision_by_id[task_id]

        if int(task.get("option_count", -1)) != int(task.get("full_candidate_count", -2)):
            raise ValueError("Teacher/model alignment refuses partial candidate display")
        options = task.get("options")
        if not isinstance(options, list) or len(options) != int(task["option_count"]):
            raise ValueError("Teacher/model alignment option-count mismatch")
        candidate_by_id = {}
        for option in options:
            candidate = _candidate_from_option(option)
            cid = str(option["candidate_id"])
            if cid in candidate_by_id:
                raise ValueError("Teacher/model alignment rejects duplicate candidate IDs")
            candidate_by_id[cid] = candidate

        observed_id = str(audit.get("observed_candidate_id"))
        if observed_id not in candidate_by_id:
            raise ValueError("observed GuitarSet answer missing from complete Teacher candidate set")
        teacher_id = _teacher_candidate_id(decision, task)
        if teacher_id is None:
            continue
        if teacher_id not in candidate_by_id:
            raise ValueError("Teacher decisive answer missing from complete candidate set")

        scores = {
            cid: _score_candidate(candidate, mean=mean, scale=scale, coef=coef)
            for cid, candidate in candidate_by_id.items()
        }
        model_id = min(candidate_by_id, key=lambda cid: (-scores[cid], candidate_by_id[cid]))
        baseline_id = min(candidate_by_id, key=lambda cid: low_total_fret_key(candidate_by_id[cid]))

        decisive += 1
        teacher_observed += int(teacher_id == observed_id)
        model_observed += int(model_id == observed_id)
        teacher_model += int(teacher_id == model_id)
        baseline_observed += int(baseline_id == observed_id)
        baseline_teacher += int(baseline_id == teacher_id)

        if teacher_id == observed_id == model_id:
            counts["all_three_same"] += 1
        elif teacher_id == observed_id:
            counts["teacher_observed_same_model_diff"] += 1
        elif model_id == observed_id:
            counts["model_observed_same_teacher_diff"] += 1
        elif teacher_id == model_id:
            counts["teacher_model_same_observed_diff"] += 1
        else:
            counts["all_three_different"] += 1

    if decisive == 0:
        raise ValueError("Teacher/model alignment has no decisive Teacher choices")

    result_core = {
        "schema": ALIGNMENT_SCHEMA,
        "version": ALIGNMENT_VERSION,
        "status": "DIAGNOSTIC_TEACHER_MODEL_ALIGNMENT_COMPLETE",
        "teacher_choices_sha256": choices_sha256,
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "sealed_development_model_artifact_sha256": model_artifact["artifact_sha256"],
        "task_count": len(tasks),
        "decisive_teacher_task_count": decisive,
        "agreement": {
            "teacher_vs_observed_guitarist": {
                "exact": teacher_observed,
                "total": decisive,
                "rate": teacher_observed / decisive,
                "semantics": "BLIND_HUMAN_PREFERENCE_VS_OBSERVED_DEVELOPMENT_GUITARIST",
            },
            "model_vs_observed_guitarist": {
                "exact": model_observed,
                "total": decisive,
                "rate": model_observed / decisive,
                "semantics": "IN_SAMPLE_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION",
            },
            "model_vs_teacher": {
                "exact": teacher_model,
                "total": decisive,
                "rate": teacher_model / decisive,
                "semantics": "DEVELOPMENT_DIAGNOSTIC_HUMAN_ALIGNMENT",
            },
            "baseline_vs_observed_guitarist": {
                "exact": baseline_observed,
                "total": decisive,
                "rate": baseline_observed / decisive,
            },
            "baseline_vs_teacher": {
                "exact": baseline_teacher,
                "total": decisive,
                "rate": baseline_teacher / decisive,
            },
        },
        "triple_agreement_counts": counts,
        "interpretation_guard": {
            "pilot_source_role": "DEVELOPMENT_ONLY",
            "model_was_fit_on_development_role": True,
            "model_vs_observed_is_in_sample": True,
            "teacher_answers_used_for_model_fit": False,
            "teacher_answers_may_tune_preregistered_model": False,
            "independent_model_validation_claim_authorized": False,
        },
        "raw_teacher_choices_embedded": False,
        "raw_task_ids_embedded": False,
        "validation_performer_opened_by_this_analysis": False,
        "untouched_final_performer_opened_by_this_analysis": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "final_access_authorized": False,
        "next_gate": "OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW",
    }
    return {**result_core, "diagnostic_sha256": _canonical_sha256(result_core)}
