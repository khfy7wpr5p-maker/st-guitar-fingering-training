from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .guitarset_checkpoint_retention_v2 import validate_checkpoint_retention_decision_v2
from .guitarset_voicing_development import verify_sealed_json

EXPECTED_TRAINING_MAIN_SHA = "b4bf08a4d8b901537b0e704a65b4fc77679c191f"
EXPECTED_ENGINE_MAIN_SHA = "ed36e9243714f32b57159dd97eeeb20d66231a7b"
EXPECTED_ENGINE_REPO = "khfy7wpr5p-maker/musicxml-to-guitar-tab-engine"
EXPECTED_ENGINE_CANDIDATE_BLOB_SHA = "146de2c2591f9ac3183552237f40401e632412d5"
EXPECTED_ENGINE_TUNING_BLOB_SHA = "06b1f76b6815ddb87cd39ac69e6ff03b018cc377"
EXPECTED_CHECKPOINT_RETENTION_EVIDENCE_SHA256 = "53f4ea1491b37dfc8360278f852927229f7a3ba6f10a6f8c9a3fb8fb8df80c71"
EXPECTED_MODEL_ARTIFACT_SHA256 = "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314"
EXPECTED_FEATURE_SCHEMA_SHA256 = "617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285"
EXPECTED_PROTOCOL_SHA256 = "db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02"
EXPECTED_REVIEW_EVIDENCE_SHA256 = "f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140"

MODEL_PATH = "evidence/stage7g_e4_guitarset_observed_voicing_development_model_v2.json"
FINAL_EVIDENCE_PATH = "evidence/stage7g_e4_guitarset_observed_voicing_final_v2.json"
RETENTION_DECISION_PATH = "evidence/stage7g_e4_guitarset_observed_voicing_checkpoint_retention_v2.json"

STANDARD_TUNING = [64, 59, 55, 50, 45, 40]
CANDIDATE_FRET_DOMAIN = [0, 20]
SOURCE_OBSERVED_FRET_DOMAIN = [0, 19]


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _load_json(path: str | Path, *, name: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be one JSON object")
    return payload


def build_shadow_integration_review_v2(
    *,
    retention_decision_path: str | Path,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    """Authorize only a fail-closed offline Node adapter review for the retained v2 model."""

    retention = validate_checkpoint_retention_decision_v2(
        retention_decision_path,
        model_path=model_path,
        final_evidence_path=final_evidence_path,
    )
    if retention.get("evidence_sha256") != EXPECTED_CHECKPOINT_RETENTION_EVIDENCE_SHA256:
        raise ValueError("v2 checkpoint-retention evidence identity drift")
    required_retention = {
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
        "fret20_quality_authority": False,
        "candidate_fret_domain": CANDIDATE_FRET_DOMAIN,
        "source_observed_fret_domain": SOURCE_OBSERVED_FRET_DOMAIN,
        "retained_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "next_gate": "SHADOW_INTEGRATION_REVIEW",
    }
    for key, expected in required_retention.items():
        if retention.get(key) != expected:
            raise ValueError(f"retention boundary {key!r} drift")

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-shadow-integration-review-v2",
        "status": "SHADOW_INTEGRATION_REVIEW_PASS_OFFLINE_NON_AUTHORITATIVE_V2_ADAPTER_ELIGIBLE_RUNTIME_CLOSED",
        "base_training_main_sha": EXPECTED_TRAINING_MAIN_SHA,
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v2",
        "accepted_checkpoint_retention_evidence_sha256": retention["evidence_sha256"],
        "retained_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "candidate_fret_domain": CANDIDATE_FRET_DOMAIN,
        "source_observed_fret_domain": SOURCE_OBSERVED_FRET_DOMAIN,
        "fret20_candidate_scoring_authorized": True,
        "fret20_quality_authority": False,
        "runtime_repo": EXPECTED_ENGINE_REPO,
        "runtime_main_sha": EXPECTED_ENGINE_MAIN_SHA,
        "runtime_candidate_contract": {
            "document_type": "GuitarVoicingCandidateModel",
            "contract_version": "1.0.0",
            "policy": "STANDARD_SIX_STRING_DISTINCT_STRING_1.0",
            "minimum_fret": 0,
            "maximum_fret": 20,
            "aggregate_candidate_limit": 10000,
            "distinct_strings_required": True,
            "exact_target_midi_round_trip_required": True,
            "standard_tuning_midi_by_string": STANDARD_TUNING,
            "module_path": "src/music/guitarVoicingCandidateModel.js",
            "module_blob_sha": EXPECTED_ENGINE_CANDIDATE_BLOB_SHA,
            "tuning_module_path": "src/guitar/tuning.js",
            "tuning_module_blob_sha": EXPECTED_ENGINE_TUNING_BLOB_SHA,
        },
        "compatibility": {
            "fret_domain_exact_match": True,
            "standard_tuning_match": True,
            "distinct_string_semantics_match": True,
            "exact_pitch_multiset_preservable": True,
            "complete_runtime_candidate_set_available": True,
            "portable_linear_inference_possible": True,
            "python_hex_float_transport_requires_explicit_node_parser": True,
            "positive_fret20_gold_available": False,
        },
        "mandatory_offline_adapter_policy": {
            "candidate_source": "EXACT_COMPLETE_GuitarVoicingCandidateModel_GROUP_CANDIDATES_ONLY",
            "canonical_candidate": "SORTED_[targetMidi,string,fret]_MULTISET",
            "diagnostic_output_only": True,
            "no_candidate_filtering": True,
            "no_candidate_generation": True,
            "no_candidate_mutation": True,
            "complete_candidate_set_required": True,
            "standard_tuning_only": True,
            "require_exact_feature_schema_identity": True,
            "require_exact_model_artifact_identity": True,
            "require_exact_protocol_identity": True,
            "require_node_python_score_parity_before_controlled_offline_execution": True,
            "fret20_scoring_semantics": "ALLOWED_AS_PREREGISTERED_CANDIDATE_DOMAIN_NO_POSITIVE_GOLD_QUALITY_CLAIM",
            "optimizer_decision_effect": False,
            "canonical_result_effect": False,
            "tab_output_effect": False,
        },
        "shadow_integration_authorized": True,
        "offline_node_adapter_implementation_authorized": True,
        "shadow_execution_authorized": False,
        "live_or_user_input_authorized": False,
        "authoritative_decision_effect_authorized": False,
        "canonical_result_effect_authorized": False,
        "checkpoint_mutation_authorized": False,
        "refit_authorized": False,
        "tuning_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "next_gate": "OFFLINE_NODE_SHADOW_ADAPTER_V2_IMPLEMENTATION_AND_CROSS_LANGUAGE_PARITY",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def validate_shadow_integration_review_v2(
    review_path: str | Path,
    *,
    retention_decision_path: str | Path,
    model_path: str | Path,
    final_evidence_path: str | Path,
) -> dict:
    review = _load_json(review_path, name="v2 shadow integration review")
    verify_sealed_json(review, "evidence_sha256")
    if review.get("evidence_sha256") != EXPECTED_REVIEW_EVIDENCE_SHA256:
        raise ValueError("v2 shadow integration review identity drift")
    expected = build_shadow_integration_review_v2(
        retention_decision_path=retention_decision_path,
        model_path=model_path,
        final_evidence_path=final_evidence_path,
    )
    if review != expected:
        raise ValueError("v2 shadow integration review drift")
    return review
