from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
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
)
from .guitarset_voicing_final import final_recording_block_bootstrap_mrr
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
from .guitarset_voicing_validation_v2 import (
    EXPECTED_DEVELOPMENT_EVIDENCE_SHA256,
    EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
    load_sealed_development_scorer_v2,
    verify_validation_evidence_v2,
)

UNTOUCHED_FINAL_PERFORMER = "02"
VALIDATION_PERFORMER = "03"
EXPECTED_FINAL_RECORDINGS = 30
EXPECTED_FINAL_ACCEPTED_NOTES = 7194
EXPECTED_FINAL_DERIVED_VOICINGS = 2210
EXPECTED_VALIDATION_EVIDENCE_SHA256 = "2df8a41bf9c319c481984d116b473ebb78a4569faf36b2a5ec3a883f6b96d987"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def verify_final_open_preconditions_v2(
    *,
    validation_evidence_path: str | Path,
    sealed_model_path: str | Path,
):
    """Fail closed unless the exact accepted v2 validation PASS and DEVELOPMENT model are present."""

    assert_frozen_protocol()
    validation = json.loads(Path(validation_evidence_path).read_text(encoding="utf-8"))
    verify_validation_evidence_v2(validation)
    if validation.get("evidence_sha256") != EXPECTED_VALIDATION_EVIDENCE_SHA256:
        raise ValueError("accepted GuitarSet v2 validation evidence identity drift")
    expected = {
        "status": "VALIDATION_PASS_FINAL_STILL_CLOSED",
        "validation_pass": True,
        "validation_performer": VALIDATION_PERFORMER,
        "untouched_final_performer": UNTOUCHED_FINAL_PERFORMER,
        "validation_performer_opened": True,
        "untouched_final_performer_opened": False,
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "final_access_authorized": False,
        "fret20_quality_authority": False,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": GUITARSET_SPLIT_VERSION,
        "sealed_development_evidence_sha256": EXPECTED_DEVELOPMENT_EVIDENCE_SHA256,
        "sealed_development_model_artifact_sha256": EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
        "next_gate": "OBSERVED_VOICING_MODEL_V2_UNTOUCHED_FINAL_OPEN",
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ValueError(f"GuitarSet v2 validation precondition field {key!r} drift")
    if validation.get("candidate_fret_domain") != [0, 20] or validation.get("source_observed_fret_domain") != [0, 19]:
        raise ValueError("GuitarSet v2 validation domain identity drift")

    scorer, model = load_sealed_development_scorer_v2(sealed_model_path)
    if model.get("artifact_sha256") != validation["sealed_development_model_artifact_sha256"]:
        raise ValueError("GuitarSet v2 validation/model identity mismatch")
    return scorer, model, validation


def _final_member(source_member: str) -> bool:
    performer, _, _ = parse_comp_member_identity(source_member)
    return performer == UNTOUCHED_FINAL_PERFORMER


def _contains_fret20(candidate) -> bool:
    return any(fret == GUITARSET_VOICING_MAX_FRET for _, _, fret in candidate)


def load_final_events_v2(path: str | Path) -> tuple[tuple[DevelopmentEvent, ...], dict]:
    """Read only untouched performer 02 bytes after exact archive/split validation."""

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
        final_members = tuple(member for member in members if _final_member(member))
        if len(final_members) != EXPECTED_FINAL_RECORDINGS:
            raise ValueError("unexpected GuitarSet v2 UNTOUCHED_FINAL recording count")
        # One-shot boundary: only performer 02 JAMS bytes are read here.
        for member in final_members:
            accepted, rejected = extract_comp_jams(member, archive.read(member))
            notes.extend(accepted)
            quarantined.extend(rejected)

    if len(notes) != EXPECTED_FINAL_ACCEPTED_NOTES:
        raise ValueError("unexpected GuitarSet v2 UNTOUCHED_FINAL accepted-note count")
    voicings = derive_strum_voicings(notes)
    if len(voicings) != EXPECTED_FINAL_DERIVED_VOICINGS:
        raise ValueError("unexpected GuitarSet v2 UNTOUCHED_FINAL derived-voicing count")

    events: list[DevelopmentEvent] = []
    single_candidate = 0
    full_candidate_count = 0
    fret20_candidate_count = 0
    fret20_candidate_event_count = 0
    observed_fret20_positive_count = 0
    for voicing in voicings:
        performer, _, _ = parse_comp_member_identity(voicing.source_member)
        if performer != UNTOUCHED_FINAL_PERFORMER:
            raise AssertionError("non-final voicing entered GuitarSet v2 untouched-final loader")
        observed_fret20_positive_count += sum(
            fret == GUITARSET_VOICING_MAX_FRET for _, _, fret in voicing.placements
        )
        pitches = tuple(pitch for pitch, _, _ in voicing.placements)
        candidates = enumerate_voicing_candidates_v2(pitches)
        if not candidates:
            raise ValueError("GuitarSet v2 UNTOUCHED_FINAL voicing has no physical candidates")
        if voicing.placements not in candidates:
            raise ValueError("observed GuitarSet v2 UNTOUCHED_FINAL voicing missing from exact candidate set")
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
        raise ValueError("GuitarSet v2 UNTOUCHED_FINAL unexpectedly contains positive fret-20 gold")
    events.sort(key=lambda event: (event.recording_id, event.voicing_id))
    if len({event.voicing_id for event in events}) != len(events):
        raise AssertionError("duplicate GuitarSet v2 UNTOUCHED_FINAL voicing IDs")

    return tuple(events), {
        "recordings": EXPECTED_FINAL_RECORDINGS,
        "accepted_notes": len(notes),
        "quarantined_notes": len(quarantined),
        "derived_voicings": len(voicings),
        "ambiguous_voicings": len(events),
        "single_candidate_voicings": single_candidate,
        "full_candidate_count_across_all_voicings": full_candidate_count,
        "performer": UNTOUCHED_FINAL_PERFORMER,
        "source_observed_max_fret": GUITARSET_SOURCE_OBSERVED_MAX_FRET,
        "target_candidate_max_fret": GUITARSET_VOICING_MAX_FRET,
        "observed_fret20_positive_gold_count": observed_fret20_positive_count,
        "fret20_candidate_event_count": fret20_candidate_event_count,
        "fret20_candidate_count_across_all_voicings": fret20_candidate_count,
        "fret20_quality_authority": False,
    }


def _mrr_delta_by_recording_v2(scorer, events: Iterable[DevelopmentEvent]) -> dict[str, tuple[float, ...]]:
    by_recording: dict[str, list[float]] = {}
    for event in events:
        matrix = np.asarray([feature_vector_v2(candidate) for candidate in event.candidates], dtype=np.float64)
        scores = np.asarray(scorer.decision_function(matrix), dtype=np.float64)
        if not np.isfinite(scores).all():
            raise ValueError("sealed GuitarSet v2 model produced non-finite final scores")
        learned_order = sorted(range(len(event.candidates)), key=lambda index: (-float(scores[index]), event.candidates[index]))
        baseline_order = sorted(range(len(event.candidates)), key=lambda index: low_total_fret_key(event.candidates[index]))
        observed_index = event.candidates.index(event.observed)
        learned_rank = learned_order.index(observed_index) + 1
        baseline_rank = baseline_order.index(observed_index) + 1
        by_recording.setdefault(event.recording_id, []).append((1.0 / learned_rank) - (1.0 / baseline_rank))
    return {key: tuple(values) for key, values in sorted(by_recording.items())}


def _final_gate_v2(source_summary: dict, metrics: dict, bootstrap: dict) -> tuple[bool, dict]:
    thresholds = protocol_payload()["final"]["pass"]
    gate = {
        "event_top1_delta": {
            "required_gt": thresholds["event_top1_delta_vs_baseline_gt"],
            "observed": metrics["event_top1_delta"],
            "pass": metrics["event_top1_delta"] > thresholds["event_top1_delta_vs_baseline_gt"],
        },
        "event_mrr_delta": {
            "required_gt": thresholds["event_mrr_delta_vs_baseline_gt"],
            "observed": metrics["event_mrr_delta"],
            "pass": metrics["event_mrr_delta"] > thresholds["event_mrr_delta_vs_baseline_gt"],
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


def run_final_once_v2(
    archive_path: str | Path,
    *,
    sealed_model_path: str | Path,
    validation_evidence_path: str | Path,
) -> dict:
    """Execute the authorized one-shot performer-02 v2 final gate without fitting or tuning."""

    scorer, model, validation = verify_final_open_preconditions_v2(
        validation_evidence_path=validation_evidence_path,
        sealed_model_path=sealed_model_path,
    )
    events, source_summary = load_final_events_v2(archive_path)
    metrics = evaluate_model_v2(scorer, events)
    deltas_by_recording = _mrr_delta_by_recording_v2(scorer, events)
    pooled_delta = sum(sum(values) for values in deltas_by_recording.values()) / sum(len(values) for values in deltas_by_recording.values())
    if abs(pooled_delta - metrics["event_mrr_delta"]) > 1e-12:
        raise AssertionError("v2 final MRR bootstrap input disagrees with canonical evaluation")
    bootstrap = final_recording_block_bootstrap_mrr(deltas_by_recording)
    final_pass, gate = _final_gate_v2(source_summary, metrics, bootstrap)

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-final-evidence-v2",
        "status": "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY" if final_pass else "FINAL_FAIL_STOP",
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "split_version": GUITARSET_SPLIT_VERSION,
        "candidate_fret_domain": [0, GUITARSET_VOICING_MAX_FRET],
        "source_observed_fret_domain": [0, GUITARSET_SOURCE_OBSERVED_MAX_FRET],
        "fret20_quality_authority": False,
        "final_policy": "ONE_SHOT_GATE_NO_REFIT_NO_TUNING",
        "untouched_final_performer": UNTOUCHED_FINAL_PERFORMER,
        "untouched_final_performer_opened": True,
        "accepted_validation_evidence_sha256": validation["evidence_sha256"],
        "sealed_development_evidence_sha256": validation["sealed_development_evidence_sha256"],
        "sealed_development_model_artifact_sha256": model["artifact_sha256"],
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "final_source_counts": source_summary,
        "final_event_identity_sha256": event_identity_sha256_v2(events),
        "metrics": metrics,
        "recording_block_bootstrap": bootstrap,
        "gate": gate,
        "final_pass": final_pass,
        "checkpoint_retention_review_eligible": final_pass,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "shadow_integration_authorized": False,
        "next_gate": "CHECKPOINT_RETENTION_REVIEW" if final_pass else "STOP_FINAL_GATE_FAILED",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def verify_final_evidence_v2(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("GuitarSet v2 final evidence must be one JSON object")
    claimed = payload.get("evidence_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("GuitarSet v2 final evidence is missing SHA-256 seal")
    core = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    if _canonical_sha256(core) != claimed:
        raise ValueError("GuitarSet v2 final evidence SHA-256 mismatch")
