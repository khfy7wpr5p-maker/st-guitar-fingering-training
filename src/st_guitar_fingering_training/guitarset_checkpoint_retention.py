from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .guitarset_voicing_development import verify_sealed_json
from .guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    assert_frozen_protocol,
)

EXPECTED_MODEL_ARTIFACT_SHA256 = "5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869"
EXPECTED_FINAL_EVIDENCE_SHA256 = "c883fbbe076ea1bc098357cd70aca592a3a95a7fedf0174cab2bdf95dcb4e57e"
EXPECTED_BASE_MAIN_SHA = "1b1ff2d5a8036fc70e4465850a030cf822ed6355"
MODEL_PATH = "evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json"
FINAL_EVIDENCE_PATH = "evidence/stage7g_e3_guitarset_observed_voicing_final_v1.json"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _load_json(path: str | Path, *, name: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be one JSON object")
    return payload


def build_checkpoint_retention_decision(
    *,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    """Authorize retention of the exact sealed DEVELOPMENT model, not deployment or refit."""

    assert_frozen_protocol()

    model = _load_json(model_path, name="sealed DEVELOPMENT model")
    verify_sealed_json(model, "artifact_sha256")
    required_model = {
        "artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v1",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "training_role": "DEVELOPMENT",
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    for key, expected in required_model.items():
        if model.get(key) != expected:
            raise ValueError(f"sealed DEVELOPMENT model field {key!r} drift")
    if model.get("training_performers") != ["00", "01", "04", "05"]:
        raise ValueError("sealed DEVELOPMENT model performer set drift")

    final = _load_json(final_evidence_path, name="untouched-final evidence")
    verify_sealed_json(final, "evidence_sha256")
    required_final = {
        "evidence_sha256": EXPECTED_FINAL_EVIDENCE_SHA256,
        "status": "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY",
        "final_pass": True,
        "checkpoint_retention_review_eligible": True,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "sealed_development_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "next_gate": "CHECKPOINT_RETENTION_REVIEW",
    }
    for key, expected in required_final.items():
        if final.get(key) != expected:
            raise ValueError(f"untouched-final evidence field {key!r} drift")

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-checkpoint-retention-v1",
        "status": "CHECKPOINT_RETAINED_RESEARCH_ONLY_SHADOW_REVIEW_ELIGIBLE",
        "base_main_sha": EXPECTED_BASE_MAIN_SHA,
        "model_version": model["model_version"],
        "retained_model_artifact_path": MODEL_PATH,
        "retained_model_artifact_sha256": model["artifact_sha256"],
        "accepted_final_evidence_path": FINAL_EVIDENCE_PATH,
        "accepted_final_evidence_sha256": final["evidence_sha256"],
        "checkpoint_retained": True,
        "checkpoint_retention_authorized": True,
        "checkpoint_mutation_authorized": False,
        "refit_authorized": False,
        "tuning_authorized": False,
        "validation_reuse_for_training_authorized": False,
        "final_reuse_for_training_authorized": False,
        "shadow_integration_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "retention_semantics": "IMMUTABLE_EXACT_DEVELOPMENT_MODEL_REFERENCE_NO_REFIT_NO_TUNING",
        "next_gate": "SHADOW_INTEGRATION_REVIEW",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def validate_checkpoint_retention_decision(
    decision_path: str | Path,
    *,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    decision = _load_json(decision_path, name="checkpoint retention decision")
    verify_sealed_json(decision, "evidence_sha256")
    expected = build_checkpoint_retention_decision(
        model_path=model_path,
        final_evidence_path=final_evidence_path,
    )
    if decision != expected:
        raise ValueError("checkpoint retention decision drift")
    return decision
