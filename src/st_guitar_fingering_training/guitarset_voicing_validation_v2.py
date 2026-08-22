from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import platform
from typing import Iterable
import zipfile

import numpy as np

from .guitarset_observed_gold import (
    _validated_comp_members,
    archive_sha256,
    derive_strum_voicings,
    extract_comp_jams,
)
from .guitarset_split import (
    ROLE_UNTOUCHED_FINAL,
    ROLE_VALIDATION,
    build_split_contract,
    parse_comp_member_identity,
)
from .guitarset_voicing_development import DevelopmentEvent, low_total_fret_key
from .guitarset_voicing_development_v2 import (
    enumerate_voicing_candidates_v2,
    evaluate_model_v2,
    event_identity_sha256_v2,
    feature_vector_v2,
    verify_sealed_json,
)
from .guitarset_voicing_prereg_v2 import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    GUITARSET_SOURCE_OBSERVED_MAX_FRET,
    GUITARSET_SPLIT_VERSION,
    GUITARSET_VOICING_MAX_FRET,
    assert_frozen_protocol,
    protocol_payload,
)
from .guitarset_voicing_validation import (
    SealedLinearVoicingScorer,
    recording_block_bootstrap_mrr,
)

VALIDATION_PERFORMER = "03"
UNTOUCHED_FINAL_PERFORMER = "02"
EXPECTED_VALIDATION_RECORDINGS = 30
EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256 = "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314"
EXPECTED_DEVELOPMENT_EVIDENCE_SHA256 = "177cc54ef38c619f475074f9e1c529865772d182a135faf4f4cdf50ee2c64351"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _decode_hex_vector(values, *, field: str) -> tuple[float, ...]:
    if not isinstance(values, list) or len(values) != 28 or not all(isinstance(value, str) for value in values):
        raise ValueError(f"sealed v2 model field {field!r} is not an exact 28D hexadecimal vector")
    try:
        decoded = tuple(float.fromhex(value) for value in values)
    except ValueError as exc:
        raise ValueError(f"sealed v2 model field {field!r} contains invalid hexadecimal float") from exc
    if not all(math.isfinite(value) for value in decoded):
        raise ValueError(f"sealed v2 model field {field!r} contains non-finite values")
    return decoded


def load_sealed_development_scorer_v2(path: str | Path) -> tuple[SealedLinearVoicingScorer, dict]:
    assert_frozen_protocol()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sealed GuitarSet v2 DEVELOPMENT model must be one JSON object")
    verify_sealed_json(payload, "artifact_sha256")
    if payload.get("artifact_sha256") != EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256:
        raise ValueError("GuitarSet v2 DEVELOPMENT model artifact identity drift")
    required = {
        "schema": "st-guitar-guitarset-observed-voicing-development-model-v2",
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v2",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": GUITARSET_SPLIT_VERSION,
        "training_role": "DEVELOPMENT",
        "validation_only_artifact": True,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "fret20_quality_authority": False,
        "observed_fret20_positive_gold_count": 0,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"sealed GuitarSet v2 DEVELOPMENT model field {key!r} drift")
    if payload.get("candidate_fret_domain") != [0, 20] or payload.get("source_observed_fret_domain") != [0, 19]:
        raise ValueError("sealed GuitarSet v2 DEVELOPMENT domain identity drift")
    if payload.get("training_performers") != ["00", "01", "04", "05"]:
        raise ValueError("sealed GuitarSet v2 DEVELOPMENT performer set drift")
    params = payload.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("sealed GuitarSet v2 DEVELOPMENT model parameters missing")
    mean = _decode_hex_vector(params.get("scaler_mean_hex"), field="scaler_mean_hex")
    scale = _decode_hex_vector(params.get("scaler_scale_hex"), field="scaler_scale_hex")
    coef = _decode_hex_vector(params.get("logistic_coef_hex"), field="logistic_coef_hex")
    return SealedLinearVoicingScorer(mean=mean, scale=scale, coef=coef), payload


def verify_development_evidence_v2(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    verify_sealed_json(payload, "evidence_sha256")
    if payload.get("evidence_sha256") != EXPECTED_DEVELOPMENT_EVIDENCE_SHA256:
        raise ValueError("GuitarSet v2 DEVELOPMENT evidence identity drift")
    if not payload.get("development_pass") or payload.get("sealed_development_model_artifact_sha256") != EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256:
        raise ValueError("GuitarSet v2 DEVELOPMENT evidence does not authorize validation")
    if payload.get("validation_performer_opened") or payload.get("final_access_authorized"):
        raise ValueError("GuitarSet v2 DEVELOPMENT evidence scientific boundary drift")
    if payload.get("runtime_connection_authorized") or payload.get("production_authorized"):
        raise ValueError("GuitarSet v2 DEVELOPMENT evidence authority drift")
    return payload


def _validation_member(source_member: str) -> bool:
    performer, _, _ = parse_comp_member_identity(source_member)
    return performer == VALIDATION_PERFORMER


def _contains_fret20(candidate) -> bool:
    return any(fret == GUITARSET_VOICING_MAX_FRET for _, _, fret in candidate)


def load_validation_events_v2(path: str | Path) -> tuple[tuple[DevelopmentEvent, ...], dict]:
    assert_frozen_protocol()
    path = Path(path)
    observed_archive_sha = archive_sha256(path)
    if observed_archive_sha != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise ValueError("GuitarSet source archive SHA-256 does not match v2 preregistration")

    notes = []
    quarantined = []
    with zipfile.ZipFile(path) as archive:
        members = _validated_comp_members(path, archive)
        contract = build_split_contract(members, source_archive_sha256=observed_archive_sha)
        if contract["performer_roles"][ROLE_VALIDATION] != [VALIDATION_PERFORMER]:
            raise ValueError("frozen v2 validation performer drift")
        if contract["performer_roles"][ROLE_UNTOUCHED_FINAL] != [UNTOUCHED_FINAL_PERFORMER]:
            raise ValueError("frozen v2 untouched-final performer drift")
        validation_members = tuple(member for member in members if _validation_member(member))
        if len(validation_members) != EXPECTED_VALIDATION_RECORDINGS:
            raise ValueError("unexpected GuitarSet v2 VALIDATION recording count")
        # One-shot boundary: only performer 03 JAMS bytes are read here.
        for member in validation_members:
            accepted, rejected = extract_comp_jams(member, archive.read(member))
            notes.extend(accepted)
            quarantined.extend(rejected)

    voicings = derive_strum_voicings(notes)
    events = []
    single_candidate = 0
    full_candidate_count = 0
    fret20_candidate_count = 0
    fret20_candidate_event_count = 0
    observed_fret20_positive_count = 0
    for voicing in voicings:
        performer, _, _ = parse_comp_member_identity(voicing.source_member)
        if performer != VALIDATION_PERFORMER:
            raise AssertionError("non-validation voicing entered v2 one-shot validation loader")
        observed_fret20_positive_count += sum(
            fret == GUITARSET_VOICING_MAX_FRET for _, _, fret in voicing.placements
        )
        pitches = tuple(pitch for pitch, _, _ in voicing.placements)
        candidates = enumerate_voicing_candidates_v2(pitches)
        if not candidates:
            raise ValueError("GuitarSet v2 VALIDATION voicing has no physical candidates")
        if voicing.placements not in candidates:
            raise ValueError("observed GuitarSet v2 VALIDATION voicing missing from exact candidate set")
        full_candidate_count += len(candidates)
        local_fret20 = sum(_contains_fret20(candidate) for candidate in candidates)
        fret20_candidate_count += local_fret20
        if local_fret20:
            fret20_candidate_event_count += 1
        if len(candidates) == 1:
            single_candidate += 1
            continue
        events.append(
            DevelopmentEvent(
                performer=performer,
                recording_id=voicing.recording_id,
                voicing_id=voicing.voicing_id,
                observed=voicing.placements,
                candidates=candidates,
            )
        )

    if observed_fret20_positive_count != 0:
        raise ValueError("GuitarSet v2 VALIDATION unexpectedly contains positive fret-20 gold")
    events.sort(key=lambda event: (event.recording_id, event.voicing_id))
    if len({event.voicing_id for event in events}) != len(events):
        raise AssertionError("duplicate GuitarSet v2 VALIDATION voicing IDs")
    return tuple(events), {
        "recordings": EXPECTED_VALIDATION_RECORDINGS,
        "accepted_notes": len(notes),
        "quarantined_notes": len(quarantined),
        "derived_voicings": len(voicings),
        "ambiguous_voicings": len(events),
        "single_candidate_voicings": single_candidate,
        "full_candidate_count_across_all_voicings": full_candidate_count,
        "performer": VALIDATION_PERFORMER,
        "source_observed_max_fret": GUITARSET_SOURCE_OBSERVED_MAX_FRET,
        "target_candidate_max_fret": GUITARSET_VOICING_MAX_FRET,
        "observed_fret20_positive_gold_count": observed_fret20_positive_count,
        "fret20_candidate_event_count": fret20_candidate_event_count,
        "fret20_candidate_count_across_all_voicings": fret20_candidate_count,
        "fret20_quality_authority": False,
    }


def _mrr_delta_by_recording_v2(scorer: SealedLinearVoicingScorer, events: Iterable[DevelopmentEvent]) -> dict[str, tuple[float, ...]]:
    by_recording: dict[str, list[float]] = {}
    for event in events:
        matrix = np.asarray([feature_vector_v2(candidate) for candidate in event.candidates], dtype=np.float64)
        scores = np.asarray(scorer.decision_function(matrix), dtype=np.float64)
        learned_order = sorted(range(len(event.candidates)), key=lambda i: (-float(scores[i]), event.candidates[i]))
        baseline_order = sorted(range(len(event.candidates)), key=lambda i: low_total_fret_key(event.candidates[i]))
        observed_index = event.candidates.index(event.observed)
        learned_rank = learned_order.index(observed_index) + 1
        baseline_rank = baseline_order.index(observed_index) + 1
        by_recording.setdefault(event.recording_id, []).append((1.0 / learned_rank) - (1.0 / baseline_rank))
    return {key: tuple(values) for key, values in sorted(by_recording.items())}


def _validation_gate(source_summary: dict, metrics: dict, bootstrap: dict) -> tuple[bool, dict]:
    protocol = protocol_payload()["validation"]
    thresholds = protocol["pass"]
    gate = {
        "minimum_ambiguous_events": {
            "required": protocol["minimum_ambiguous_events"],
            "observed": source_summary["ambiguous_voicings"],
            "pass": source_summary["ambiguous_voicings"] >= protocol["minimum_ambiguous_events"],
        },
        "event_top1_delta": {
            "required_gte": thresholds["event_top1_delta_vs_baseline_gte"],
            "observed": metrics["event_top1_delta"],
            "pass": metrics["event_top1_delta"] >= thresholds["event_top1_delta_vs_baseline_gte"],
        },
        "event_mrr_delta": {
            "required_gte": thresholds["event_mrr_delta_vs_baseline_gte"],
            "observed": metrics["event_mrr_delta"],
            "pass": metrics["event_mrr_delta"] >= thresholds["event_mrr_delta_vs_baseline_gte"],
        },
        "recording_macro_top1_delta": {
            "required_gt": thresholds["recording_macro_top1_delta_gt"],
            "observed": metrics["recording_macro_top1_delta"],
            "pass": metrics["recording_macro_top1_delta"] > thresholds["recording_macro_top1_delta_gt"],
        },
        "recording_macro_mrr_delta": {
            "required_gt": thresholds["recording_macro_mrr_delta_gt"],
            "observed": metrics["recording_macro_mrr_delta"],
            "pass": metrics["recording_macro_mrr_delta"] > thresholds["recording_macro_mrr_delta_gt"],
        },
        "recording_block_bootstrap_mrr_delta_lower_bound": {
            "required_gt": thresholds["recording_block_bootstrap"]["lower_bound_gt"],
            "observed": bootstrap["lower_bound"],
            "pass": bootstrap["lower_bound"] > thresholds["recording_block_bootstrap"]["lower_bound_gt"],
        },
        "fret20_positive_gold_absent": {
            "required": 0,
            "observed": source_summary["observed_fret20_positive_gold_count"],
            "pass": source_summary["observed_fret20_positive_gold_count"] == 0,
        },
    }
    return all(item["pass"] for item in gate.values()), gate


def run_validation_once_v2(
    archive_path: str | Path,
    *,
    sealed_model_path: str | Path,
    development_evidence_path: str | Path,
) -> dict:
    assert_frozen_protocol()
    development_evidence = verify_development_evidence_v2(development_evidence_path)
    scorer, model_payload = load_sealed_development_scorer_v2(sealed_model_path)
    if development_evidence["sealed_development_model_artifact_sha256"] != model_payload["artifact_sha256"]:
        raise ValueError("GuitarSet v2 DEVELOPMENT model/evidence binding drift")

    events, source_summary = load_validation_events_v2(archive_path)
    metrics = evaluate_model_v2(scorer, events)
    deltas_by_recording = _mrr_delta_by_recording_v2(scorer, events)
    pooled_delta = sum(sum(values) for values in deltas_by_recording.values()) / sum(len(values) for values in deltas_by_recording.values())
    if abs(pooled_delta - metrics["event_mrr_delta"]) > 1e-12:
        raise AssertionError("v2 validation MRR bootstrap input disagrees with canonical evaluation")
    bootstrap = recording_block_bootstrap_mrr(deltas_by_recording)
    validation_pass, gate = _validation_gate(source_summary, metrics, bootstrap)

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-validation-evidence-v2",
        "status": "VALIDATION_PASS_FINAL_STILL_CLOSED" if validation_pass else "VALIDATION_FAIL_STOP",
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "sealed_development_evidence_sha256": development_evidence["evidence_sha256"],
        "sealed_development_model_artifact_sha256": model_payload["artifact_sha256"],
        "split_version": GUITARSET_SPLIT_VERSION,
        "candidate_fret_domain": [0, GUITARSET_VOICING_MAX_FRET],
        "source_observed_fret_domain": [0, GUITARSET_SOURCE_OBSERVED_MAX_FRET],
        "fret20_quality_authority": False,
        "validation_performer": VALIDATION_PERFORMER,
        "validation_performer_opened": True,
        "validation_policy": "ONE_SHOT_GATE_NO_TUNING",
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "validation_source_counts": source_summary,
        "validation_event_identity_sha256": event_identity_sha256_v2(events),
        "metrics": metrics,
        "recording_block_bootstrap": bootstrap,
        "gate": gate,
        "validation_pass": validation_pass,
        "untouched_final_performer": UNTOUCHED_FINAL_PERFORMER,
        "untouched_final_performer_opened": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "final_access_authorized": False,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "next_gate": "OBSERVED_VOICING_MODEL_V2_UNTOUCHED_FINAL_OPEN" if validation_pass else "STOP_VALIDATION_GATE_FAILED",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def verify_validation_evidence_v2(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("GuitarSet v2 validation evidence must be one JSON object")
    claimed = payload.get("evidence_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("GuitarSet v2 validation evidence is missing SHA-256 seal")
    core = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    if _canonical_sha256(core) != claimed:
        raise ValueError("GuitarSet v2 validation evidence SHA-256 mismatch")
