from __future__ import annotations

from hashlib import sha256
import json
import platform
from pathlib import Path
from typing import Callable

import numpy as np
import scipy
from scipy import optimize
from scipy.special import expit
import sklearn
from sklearn.preprocessing import StandardScaler

EXPECTED_BASE_MAIN_SHA = "959ed78df27ce49a44ff1c444d329fc871abb334"
EXPECTED_MODEL_ARTIFACT_SHA256 = "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314"
EXPECTED_FEATURE_SCHEMA_SHA256 = "617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285"
EXPECTED_PROTOCOL_SHA256 = "db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02"
EXPECTED_SOURCE_ARCHIVE_SHA256 = "06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe"
EXPECTED_SELECTED_PAIR_IDENTITY_SHA256 = "6bc82ad12e99cafcdb26632b33e2240ed5f33c7a3e785a5594f744013d0c7663"
EXPECTED_SELECTED_PAIR_COUNT = 171_452
EXPECTED_SYMMETRIC_ROW_COUNT = 342_904
EXPECTED_FEATURE_COUNT = 28
EXPECTED_N_ITER = 37

LBFGS_C = 1.0
LBFGS_TOL = 1e-4
LBFGS_MAX_ITER = 2_000
LBFGS_MAX_LINE_SEARCH_STEPS = 50
LBFGS_FTOL = 64 * np.finfo(np.float64).eps
COEFFICIENT_MAX_ABS_DELTA_LIMIT = 1e-10
OBJECTIVE_TRACE_INCREASE_TOLERANCE = 1e-14


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_sha256(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _verify_sealed_json(payload: dict, hash_field: str) -> None:
    claimed = payload.get(hash_field)
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError(f"missing or invalid {hash_field}")
    core = {key: value for key, value in payload.items() if key != hash_field}
    if _canonical_sha256(core) != claimed:
        raise ValueError(f"{hash_field} mismatch")


def load_authorized_request(path: str | Path) -> dict:
    request = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("numerical-hardening request must be one JSON object")
    _verify_sealed_json(request, "request_sha256")
    required = {
        "schema": "st-guitar-guitarset-observed-voicing-numerical-hardening-request-v2",
        "base_training_main_sha": EXPECTED_BASE_MAIN_SHA,
        "retained_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "source_archive_sha256": EXPECTED_SOURCE_ARCHIVE_SHA256,
        "allowed_data_role": "DEVELOPMENT_ONLY",
        "diagnostic_reconstruction_authorized": True,
        "checkpoint_replacement_authorized": False,
        "model_mutation_authorized": False,
        "validation_access_authorized": False,
        "final_access_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    for field, expected in required.items():
        if request.get(field) != expected:
            raise ValueError(f"numerical-hardening request field {field!r} drift")
    return request


def load_retained_model(path: str | Path) -> dict:
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(model, dict):
        raise ValueError("retained model must be one JSON object")
    _verify_sealed_json(model, "artifact_sha256")
    required = {
        "artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v2",
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "source_archive_sha256": EXPECTED_SOURCE_ARCHIVE_SHA256,
        "candidate_fret_domain": [0, 20],
        "source_observed_fret_domain": [0, 19],
        "observed_fret20_positive_gold_count": 0,
        "fret20_quality_authority": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    for field, expected in required.items():
        if model.get(field) != expected:
            raise ValueError(f"retained model field {field!r} drift")
    params = model.get("pipeline", {}).get("params", {})
    if params != {
        "C": 1.0,
        "class_weight": None,
        "fit_intercept": False,
        "max_iter": 2000,
        "random_state": 0,
        "solver": "lbfgs",
    }:
        raise ValueError("retained model optimizer contract drift")
    if model.get("parameters", {}).get("n_iter") != [EXPECTED_N_ITER]:
        raise ValueError("retained model iteration evidence drift")
    return model


def logistic_objective_gradient(
    X_scaled: np.ndarray,
    y: np.ndarray,
    coefficients: np.ndarray,
    *,
    C: float = LBFGS_C,
) -> tuple[float, np.ndarray]:
    X_scaled = np.asarray(X_scaled, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    coefficients = np.asarray(coefficients, dtype=np.float64)
    if X_scaled.ndim != 2 or X_scaled.shape[1] != coefficients.shape[0]:
        raise ValueError("numerical-hardening matrix/coefficient shape mismatch")
    if y.ndim != 1 or y.shape[0] != X_scaled.shape[0] or set(np.unique(y).tolist()) != {0.0, 1.0}:
        raise ValueError("numerical-hardening labels must be one binary row per matrix row")
    if C <= 0 or not np.isfinite(C):
        raise ValueError("C must be finite and positive")
    if not np.isfinite(X_scaled).all() or not np.isfinite(y).all() or not np.isfinite(coefficients).all():
        raise ValueError("numerical-hardening inputs must be finite")

    row_count = X_scaled.shape[0]
    scores = X_scaled @ coefficients
    l2_reg_strength = 1.0 / (C * row_count)
    objective = float(
        np.mean(np.logaddexp(0.0, scores) - y * scores)
        + 0.5 * l2_reg_strength * np.dot(coefficients, coefficients)
    )
    gradient = (
        X_scaled.T @ (expit(scores) - y) / row_count
        + l2_reg_strength * coefficients
    )
    if not np.isfinite(objective) or not np.isfinite(gradient).all():
        raise ValueError("numerical-hardening objective/gradient is non-finite")
    return objective, np.asarray(gradient, dtype=np.float64)


def _hex_array(values: np.ndarray) -> list[str]:
    return [float(value).hex() for value in np.asarray(values, dtype=np.float64)]


def reconstruct_lbfgs(
    X_scaled: np.ndarray,
    y: np.ndarray,
    sealed_coefficients: np.ndarray,
    *,
    minimize: Callable = optimize.minimize,
) -> dict:
    X_scaled = np.asarray(X_scaled, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    sealed_coefficients = np.asarray(sealed_coefficients, dtype=np.float64)
    initial = np.zeros(X_scaled.shape[1], dtype=np.float64)
    accepted_objectives = [logistic_objective_gradient(X_scaled, y, initial)[0]]

    def objective(candidate: np.ndarray) -> tuple[float, np.ndarray]:
        return logistic_objective_gradient(X_scaled, y, candidate)

    def callback(candidate: np.ndarray) -> None:
        accepted_objectives.append(objective(np.asarray(candidate, dtype=np.float64))[0])

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        jac=True,
        callback=callback,
        options={
            "maxiter": LBFGS_MAX_ITER,
            "maxls": LBFGS_MAX_LINE_SEARCH_STEPS,
            "gtol": LBFGS_TOL,
            "ftol": LBFGS_FTOL,
        },
    )
    reconstructed = np.asarray(result.x, dtype=np.float64)
    if not accepted_objectives or accepted_objectives[-1] != float(result.fun):
        accepted_objectives.append(float(result.fun))
    increases = [
        current - previous
        for previous, current in zip(accepted_objectives, accepted_objectives[1:])
    ]
    maximum_increase = max(increases, default=0.0)
    sealed_objective, sealed_gradient = objective(sealed_coefficients)
    reconstructed_objective, reconstructed_gradient = objective(reconstructed)
    coefficient_delta = np.abs(reconstructed - sealed_coefficients)
    score_delta = np.abs(X_scaled @ reconstructed - X_scaled @ sealed_coefficients)
    maximum_row_l1_norm = float(np.max(np.sum(np.abs(X_scaled), axis=1)))
    derived_score_delta_limit = maximum_row_l1_norm * COEFFICIENT_MAX_ABS_DELTA_LIMIT

    return {
        "method": "L-BFGS-B",
        "C": LBFGS_C,
        "tol": LBFGS_TOL,
        "max_iter": LBFGS_MAX_ITER,
        "max_line_search_steps": LBFGS_MAX_LINE_SEARCH_STEPS,
        "ftol": LBFGS_FTOL,
        "initial_objective": accepted_objectives[0],
        "final_objective": float(result.fun),
        "objective_improvement": accepted_objectives[0] - float(result.fun),
        "accepted_iteration_objectives": accepted_objectives,
        "accepted_iteration_count": len(accepted_objectives) - 1,
        "maximum_accepted_objective_increase": maximum_increase,
        "accepted_objective_trace_non_increasing": maximum_increase <= OBJECTIVE_TRACE_INCREASE_TOLERANCE,
        "optimizer_success": bool(result.success),
        "optimizer_status": int(result.status),
        "optimizer_message": str(result.message),
        "optimizer_n_iter": int(result.nit),
        "optimizer_function_evaluations": int(result.nfev),
        "optimizer_gradient_evaluations": int(getattr(result, "njev", result.nfev)),
        "optimizer_final_gradient_l2_norm": float(np.linalg.norm(reconstructed_gradient, ord=2)),
        "optimizer_final_gradient_inf_norm": float(np.linalg.norm(reconstructed_gradient, ord=np.inf)),
        "optimizer_stationarity_within_tol": float(np.linalg.norm(reconstructed_gradient, ord=np.inf)) <= LBFGS_TOL,
        "sealed_model_objective": sealed_objective,
        "sealed_model_gradient_l2_norm": float(np.linalg.norm(sealed_gradient, ord=2)),
        "sealed_model_gradient_inf_norm": float(np.linalg.norm(sealed_gradient, ord=np.inf)),
        "sealed_model_stationarity_within_tol": float(np.linalg.norm(sealed_gradient, ord=np.inf)) <= LBFGS_TOL,
        "sealed_model_n_iter": EXPECTED_N_ITER,
        "sealed_model_n_iter_below_max_iter": EXPECTED_N_ITER < LBFGS_MAX_ITER,
        "reconstructed_coefficient_hex": _hex_array(reconstructed),
        "coefficient_max_abs_delta_vs_sealed": float(np.max(coefficient_delta)),
        "coefficient_delta_within_limit": float(np.max(coefficient_delta)) <= COEFFICIENT_MAX_ABS_DELTA_LIMIT,
        "training_score_max_abs_delta_vs_sealed": float(np.max(score_delta)),
        "maximum_training_row_l1_norm": maximum_row_l1_norm,
        "training_score_delta_derived_limit": derived_score_delta_limit,
        "training_score_delta_within_derived_limit": float(np.max(score_delta)) <= derived_score_delta_limit,
        "reconstructed_objective_recomputed": reconstructed_objective,
    }


def build_numerical_hardening_evidence_v2(
    *,
    archive_path: str | Path,
    model_path: str | Path,
    request_path: str | Path,
    source_code_sha: str,
) -> dict:
    from .guitarset_voicing_development_v2 import (
        build_training_matrix_v2,
        load_development_events_v2,
        selected_pair_identity_v2,
    )

    if not isinstance(source_code_sha, str) or len(source_code_sha) != 40 or any(c not in "0123456789abcdef" for c in source_code_sha):
        raise ValueError("source_code_sha must be one lowercase Git commit SHA")
    request = load_authorized_request(request_path)
    model = load_retained_model(model_path)
    events, source_summary = load_development_events_v2(archive_path)
    X, y = build_training_matrix_v2(events)
    pair_sha, pair_count = selected_pair_identity_v2(events)
    if pair_sha != EXPECTED_SELECTED_PAIR_IDENTITY_SHA256 or pair_count != EXPECTED_SELECTED_PAIR_COUNT:
        raise ValueError("DEVELOPMENT selected-pair identity drift")
    if X.shape != (EXPECTED_SYMMETRIC_ROW_COUNT, EXPECTED_FEATURE_COUNT):
        raise ValueError("DEVELOPMENT numerical surface shape drift")

    scaler = StandardScaler().fit(X)
    sealed_mean = np.asarray([float.fromhex(value) for value in model["parameters"]["scaler_mean_hex"]])
    sealed_scale = np.asarray([float.fromhex(value) for value in model["parameters"]["scaler_scale_hex"]])
    sealed_coefficients = np.asarray([float.fromhex(value) for value in model["parameters"]["logistic_coef_hex"]])
    scaler_mean_exact = _hex_array(scaler.mean_) == model["parameters"]["scaler_mean_hex"]
    scaler_scale_exact = _hex_array(scaler.scale_) == model["parameters"]["scaler_scale_hex"]
    if not scaler_mean_exact or not scaler_scale_exact:
        raise ValueError("reconstructed StandardScaler identity drift")
    X_scaled = (X - sealed_mean) / sealed_scale
    reconstruction = reconstruct_lbfgs(X_scaled, y, sealed_coefficients)

    gate = {
        "optimizer_success": reconstruction["optimizer_success"] and reconstruction["optimizer_status"] == 0,
        "optimizer_stopped_before_iteration_limit": reconstruction["optimizer_n_iter"] < LBFGS_MAX_ITER,
        "sealed_iteration_record_matches_reconstruction": reconstruction["optimizer_n_iter"] == EXPECTED_N_ITER,
        "sealed_model_stationarity_within_resolved_tol": reconstruction["sealed_model_stationarity_within_tol"],
        "accepted_objective_trace_non_increasing": reconstruction["accepted_objective_trace_non_increasing"],
        "coefficient_reconstruction_within_limit": reconstruction["coefficient_delta_within_limit"],
        "score_reconstruction_within_derived_limit": reconstruction["training_score_delta_within_derived_limit"],
        "scaler_identity_exact": scaler_mean_exact and scaler_scale_exact,
    }
    passed = all(gate.values())
    core = {
        "schema": "st-guitar-guitarset-observed-voicing-numerical-hardening-evidence-v2",
        "status": "NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED" if passed else "NUMERICAL_HARDENING_FAIL_STOP",
        "source_code_sha": source_code_sha,
        "base_training_main_sha": EXPECTED_BASE_MAIN_SHA,
        "request_sha256": request["request_sha256"],
        "retained_model_artifact_sha256": model["artifact_sha256"],
        "feature_schema_sha256": model["feature_schema_sha256"],
        "protocol_sha256": model["protocol_sha256"],
        "source_archive_sha256": model["source_archive_sha256"],
        "allowed_data_role": "DEVELOPMENT_ONLY",
        "development_event_count": len(events),
        "selected_pair_count": pair_count,
        "selected_pair_identity_sha256": pair_sha,
        "symmetric_training_row_count": int(X.shape[0]),
        "feature_count": int(X.shape[1]),
        "source_observed_fret_domain": [0, 19],
        "candidate_fret_domain": [0, 20],
        "observed_fret20_positive_gold_count": source_summary["observed_fret20_positive_gold_count"],
        "fret20_quality_authority": False,
        "objective_contract": {
            "loss": "mean(logaddexp(0,Xw)-y*Xw)+0.5*(1/(C*n))*dot(w,w)",
            "gradient": "X.T@(sigmoid(Xw)-y)/n+(1/(C*n))*w",
            "scaler": "SEALED_STANDARD_SCALER_PARAMETERS",
            "fit_intercept": False,
        },
        "reconstruction": reconstruction,
        "gate": gate,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "diagnostic_reconstruction_executed": True,
        "historical_model_rewritten": False,
        "checkpoint_replacement_authorized": False,
        "model_mutation_authorized": False,
        "validation_access_authorized": False,
        "final_access_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def verify_numerical_hardening_evidence_v2(payload: dict) -> None:
    _verify_sealed_json(payload, "evidence_sha256")
    if payload.get("status") != "NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED":
        raise ValueError("numerical-hardening evidence is not PASS")
    if not all(payload.get("gate", {}).values()):
        raise ValueError("numerical-hardening gate is not fully PASS")
    for field in (
        "historical_model_rewritten",
        "checkpoint_replacement_authorized",
        "model_mutation_authorized",
        "validation_access_authorized",
        "final_access_authorized",
        "runtime_connection_authorized",
        "production_authorized",
        "fret20_quality_authority",
    ):
        if payload.get(field) is not False:
            raise ValueError(f"numerical-hardening authority field {field!r} must remain false")


__all__ = [
    "build_numerical_hardening_evidence_v2",
    "load_authorized_request",
    "load_retained_model",
    "logistic_objective_gradient",
    "reconstruct_lbfgs",
    "verify_numerical_hardening_evidence_v2",
]
