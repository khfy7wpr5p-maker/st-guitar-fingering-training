from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .guitarset_voicing_development import verify_sealed_json
from .guitarset_voicing_final_v2 import verify_final_evidence_v2
from .guitarset_voicing_prereg_v2 import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    assert_frozen_protocol,
)

EXPECTED_MODEL_ARTIFACT_SHA256 = "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314"
EXPECTED_FINAL_EVIDENCE_SHA256 = "8aab8f841cf2a5e5a6e6437a8f2207026465b1863fdc064629e2818eae6a67b2"
EXPECTED_BASE_MAIN_SHA = "dce495a9ddba0b299854128d483c67f84e56e380"
MODEL_PATH = "evidence/stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
FINAL_EVIDENCE_PATH = "evidence/stage7g_e4_guitarset_observed_voicing_final_v2.json"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _load_json(path: str | Path, *, name: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be one JSON object")
    return payload


def build_checkpoint_retention_decision_v2(
    *,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    """Retain the exact v2 DEVELOPMENT artifact as research-only; grant no execution authority."""

    assert_frozen_protocol()

    model = _load_json(model_path, name="sealed v2 DEVELOPMENT model")
    verify_sealed_json(model, "artifact_sha256")
    required_model = {
        "artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v2",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "training_role": "DEVELOPMENT",
        "candidate_fret_domain": [0, 20],
        "source_observed_fret_domain": [0, 19],
        "observed_fret20_positive_gold_count": 0,
        "fret20_quality_authority": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }
    for key, expected in required_model.items():
        if model.get(key) != expected:
            raise ValueError(f"sealed v2 DEVELOPMENT model field {key!r} drift")
    if model.get("training_performers") != ["00", "01", "04", "05"]:
        raise ValueError("sealed v2 DEVELOPMENT model performer set drift")

    final = _load_json(final_evidence_path, name="v2 untouched-final evidence")
    verify_final_evidence_v2(final)
    required_final = {
        "evidence_sha256": EXPECTED_FINAL_EVIDENCE_SHA256,
        "status": "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY",
        "final_pass": True,
        "checkpoint_retention_review_eligible": True,
        "checkpoint_authorized": False,
        "shadow_integration_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "sealed_development_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "candidate_fret_domain": [0, 20],
        "source_observed_fret_domain": [0, 19],
        "fret20_quality_authority": False,
        "next_gate": "CHECKPOINT_RETENTION_REVIEW",
    }
    for key, expected in required_final.items():
        if final.get(key) != expected:
            raise ValueError(f"v2 untouched-final evidence field {key!r} drift")
    if final.get("final_source_counts", {}).get("observed_fret20_positive_gold_count") != 0:
        raise ValueError("v2 final evidence unexpectedly contains positive fret-20 gold")

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-checkpoint-retention-v2",
        "status": "CHECKPOINT_RETAINED_RESEARCH_ONLY_SHADOW_REVIEW_ELIGIBLE",
        "base_main_sha": EXPECTED_BASE_MAIN_SHA,
        "model_version": model["model_version"],
        "retained_model_artifact_path": MODEL_PATH,
        "retained_model_artifact_sha256": model["artifact_sha256"],
        "accepted_final_evidence_path": FINAL_EVIDENCE_PATH,
        "accepted_final_evidence_sha256": final["evidence_sha256"],
        "candidate_fret_domain": [0, 20],
        "source_observed_fret_domain": [0, 19],
        "fret20_quality_authority": False,
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
        "retention_semantics": "IMMUTABLE_EXACT_DEVELOPMENT_MODEL_REFERENCE_NO_REFIT_NO_TUNING_NO_FRET20_QUALITY_CLAIM",
        "next_gate": "SHADOW_INTEGRATION_REVIEW",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def validate_checkpoint_retention_decision_v2(
    decision_path: str | Path,
    *,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    decision = _load_json(decision_path, name="v2 checkpoint retention decision")
    verify_sealed_json(decision, "evidence_sha256")
    expected = build_checkpoint_retention_decision_v2(
        model_path=model_path,
        final_evidence_path=final_evidence_path,
    )
    if decision != expected:
        raise ValueError("v2 checkpoint retention decision drift")
    return decision
