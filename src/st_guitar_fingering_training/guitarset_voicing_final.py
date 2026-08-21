from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
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
from .guitarset_voicing_development import (
    Candidate,
    enumerate_voicing_candidates,
    evaluate_model,
    event_identity_sha256,
    feature_vector,
    low_total_fret_key,
    verify_sealed_json,
)
from .guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    assert_frozen_protocol,
    protocol_payload,
)
from .guitarset_voicing_validation import (
    EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
    load_sealed_development_scorer,
)

UNTOUCHED_FINAL_PERFORMER = "02"
VALIDATION_PERFORMER = "03"
EXPECTED_FINAL_RECORDINGS = 30
EXPECTED_FINAL_ACCEPTED_NOTES = 7194
EXPECTED_FINAL_DERIVED_VOICINGS = 2210
EXPECTED_VALIDATION_EVIDENCE_SHA256 = (
    "13b706076205abea42a436d10cf019a36445035e08172054989191121ff59e51"
)
FINAL_BOOTSTRAP_REPETITIONS = 2000
FINAL_BOOTSTRAP_SEED = 0
FINAL_CONFIDENCE = 0.95
FINAL_BOOTSTRAP_LOWER_INDEX = 49
FINAL_BOOTSTRAP_UPPER_INDEX = 1949


@dataclass(frozen=True)
class FinalEvent:
    performer: str
    recording_id: str
    voicing_id: str
    observed: Candidate
    candidates: tuple[Candidate, ...]


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def verify_final_open_preconditions(
    *,
    validation_evidence_path: str | Path,
    sealed_model_path: str | Path,
):
    """Fail closed unless the exact accepted validation PASS and model seal are present."""

    assert_frozen_protocol()
    validation = json.loads(Path(validation_evidence_path).read_text(encoding="utf-8"))
    if not isinstance(validation, dict):
        raise ValueError("validation evidence must be one JSON object")
    verify_sealed_json(validation, "evidence_sha256")
    if validation.get("evidence_sha256") != EXPECTED_VALIDATION_EVIDENCE_SHA256:
        raise ValueError("accepted validation evidence identity drift")
    expected_validation = {
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
        "final_access_authorized": False,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "sealed_development_model_artifact_sha256": EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256,
        "next_gate": "OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW",
    }
    for key, expected in expected_validation.items():
        if validation.get(key) != expected:
            raise ValueError(f"validation precondition field {key!r} drift")

    scorer, model_payload = load_sealed_development_scorer(sealed_model_path)
    if model_payload.get("artifact_sha256") != validation["sealed_development_model_artifact_sha256"]:
        raise ValueError("validation evidence/model artifact identity mismatch")
    return scorer, model_payload, validation


def _final_member(source_member: str) -> bool:
    performer, _, _ = parse_comp_member_identity(source_member)
    return performer == UNTOUCHED_FINAL_PERFORMER


def load_final_events(path: str | Path) -> tuple[tuple[FinalEvent, ...], dict]:
    """Read only performer 02 bytes after exact archive/split identity is verified."""

    assert_frozen_protocol()
    path = Path(path)
    observed_archive_sha = archive_sha256(path)
    if observed_archive_sha != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise ValueError("GuitarSet source archive SHA-256 does not match preregistration")

    notes = []
    quarantined = []
    with zipfile.ZipFile(path) as archive:
        members = _validated_comp_members(path, archive)
        contract = build_split_contract(members, source_archive_sha256=observed_archive_sha)
        if contract["performer_roles"][ROLE_VALIDATION] != [VALIDATION_PERFORMER]:
            raise ValueError("frozen validation performer drift")
        if contract["performer_roles"][ROLE_UNTOUCHED_FINAL] != [UNTOUCHED_FINAL_PERFORMER]:
            raise ValueError("frozen untouched-final performer drift")
        final_members = tuple(member for member in members if _final_member(member))
        if len(final_members) != EXPECTED_FINAL_RECORDINGS:
            raise ValueError("unexpected GuitarSet UNTOUCHED_FINAL recording count")

        for member in final_members:
            accepted, rejected = extract_comp_jams(member, archive.read(member))
            notes.extend(accepted)
            quarantined.extend(rejected)

    if len(notes) != EXPECTED_FINAL_ACCEPTED_NOTES:
        raise ValueError("unexpected GuitarSet UNTOUCHED_FINAL accepted-note count")
    voicings = derive_strum_voicings(notes)
    if len(voicings) != EXPECTED_FINAL_DERIVED_VOICINGS:
        raise ValueError("unexpected GuitarSet UNTOUCHED_FINAL derived-voicing count")

    events: list[FinalEvent] = []
    single_candidate = 0
    full_candidate_count = 0
    for voicing in voicings:
        performer, _, _ = parse_comp_member_identity(voicing.source_member)
        if performer != UNTOUCHED_FINAL_PERFORMER:
            raise AssertionError("non-final voicing entered untouched-final loader")
        pitches = tuple(pitch for pitch, _, _ in voicing.placements)
        candidates = enumerate_voicing_candidates(pitches)
        if not candidates:
            raise ValueError("GuitarSet UNTOUCHED_FINAL voicing has no physical candidates")
        if voicing.placements not in candidates:
            raise ValueError("observed GuitarSet UNTOUCHED_FINAL voicing missing from exact candidate set")
        full_candidate_count += len(candidates)
        if len(candidates) == 1:
            single_candidate += 1
            continue
        events.append(
            FinalEvent(
                performer=performer,
                recording_id=voicing.recording_id,
                voicing_id=voicing.voicing_id,
                observed=voicing.placements,
                candidates=candidates,
            )
        )

    events.sort(key=lambda event: (event.recording_id, event.voicing_id))
    if len({event.voicing_id for event in events}) != len(events):
        raise AssertionError("duplicate GuitarSet UNTOUCHED_FINAL voicing IDs")
    return tuple(events), {
        "recordings": EXPECTED_FINAL_RECORDINGS,
        "accepted_notes": len(notes),
        "quarantined_notes": len(quarantined),
        "derived_voicings": len(voicings),
        "ambiguous_voicings": len(events),
        "single_candidate_voicings": single_candidate,
        "full_candidate_count_across_all_voicings": full_candidate_count,
        "performer": UNTOUCHED_FINAL_PERFORMER,
    }


def _mrr_delta_by_recording(scorer, events: Iterable[FinalEvent]) -> dict[str, tuple[float, ...]]:
    by_recording: dict[str, list[float]] = {}
    for event in events:
        matrix = np.asarray([feature_vector(candidate) for candidate in event.candidates], dtype=np.float64)
        scores = np.asarray(scorer.decision_function(matrix), dtype=np.float64)
        if not np.isfinite(scores).all():
            raise ValueError("sealed model produced non-finite final scores")
        learned_order = sorted(
            range(len(event.candidates)),
            key=lambda index: (-float(scores[index]), event.candidates[index]),
        )
        baseline_order = sorted(
            range(len(event.candidates)),
            key=lambda index: low_total_fret_key(event.candidates[index]),
        )
        observed_index = event.candidates.index(event.observed)
        learned_rank = learned_order.index(observed_index) + 1
        baseline_rank = baseline_order.index(observed_index) + 1
        by_recording.setdefault(event.recording_id, []).append(
            float((1.0 / learned_rank) - (1.0 / baseline_rank))
        )
    return {key: tuple(values) for key, values in sorted(by_recording.items())}


def final_recording_block_bootstrap_mrr(
    deltas_by_recording: dict[str, tuple[float, ...]],
    *,
    repetitions: int = FINAL_BOOTSTRAP_REPETITIONS,
    seed: int = FINAL_BOOTSTRAP_SEED,
) -> dict:
    """Frozen pre-outcome final bootstrap; literal order-statistic indices 49/1949."""

    if repetitions != FINAL_BOOTSTRAP_REPETITIONS or seed != FINAL_BOOTSTRAP_SEED:
        raise ValueError("final bootstrap repetitions/seed are frozen at 2000/0")
    recording_ids = tuple(sorted(deltas_by_recording))
    if not recording_ids or any(not deltas_by_recording[key] for key in recording_ids):
        raise ValueError("final recording-block bootstrap requires non-empty ambiguous-event blocks")

    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(repetitions):
        total = 0.0
        count = 0
        for _slot in recording_ids:
            key = recording_ids[rng.randrange(len(recording_ids))]
            block = deltas_by_recording[key]
            total += sum(block)
            count += len(block)
        if count <= 0:
            raise AssertionError("bootstrap sampled zero final events")
        samples.append(total / count)

    ordered = sorted(samples)
    if not (0 <= FINAL_BOOTSTRAP_LOWER_INDEX < FINAL_BOOTSTRAP_UPPER_INDEX < repetitions):
        raise AssertionError("frozen final bootstrap order-statistic indices are invalid")
    return {
        "method": "RECORDING_BLOCK_RESAMPLE_WITH_REPLACEMENT_POOL_EVENT_MRR_DELTA",
        "repetitions": repetitions,
        "seed": seed,
        "confidence": FINAL_CONFIDENCE,
        "recording_block_count": len(recording_ids),
        "lower_order_statistic_index_zero_based": FINAL_BOOTSTRAP_LOWER_INDEX,
        "upper_order_statistic_index_zero_based": FINAL_BOOTSTRAP_UPPER_INDEX,
        "lower_bound": float(ordered[FINAL_BOOTSTRAP_LOWER_INDEX]),
        "upper_bound": float(ordered[FINAL_BOOTSTRAP_UPPER_INDEX]),
        "bootstrap_mean": float(sum(samples) / len(samples)),
        "sample_identity_sha256": _canonical_sha256([float(value).hex() for value in samples]),
    }


def _final_gate(metrics: dict, bootstrap: dict) -> tuple[bool, dict]:
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
    }
    return all(item["pass"] for item in gate.values()), gate


def run_final_once(
    archive_path: str | Path,
    *,
    sealed_model_path: str | Path,
    validation_evidence_path: str | Path,
) -> dict:
    """Execute the authorized one-shot performer-02 final gate without fitting or tuning."""

    assert_frozen_protocol()
    scorer, model_payload, validation = verify_final_open_preconditions(
        validation_evidence_path=validation_evidence_path,
        sealed_model_path=sealed_model_path,
    )
    events, source_summary = load_final_events(archive_path)
    metrics = evaluate_model(scorer, events)
    deltas_by_recording = _mrr_delta_by_recording(scorer, events)
    pooled_delta = sum(sum(values) for values in deltas_by_recording.values()) / sum(
        len(values) for values in deltas_by_recording.values()
    )
    if abs(pooled_delta - metrics["event_mrr_delta"]) > 1e-12:
        raise AssertionError("final MRR bootstrap input disagrees with canonical evaluation")
    bootstrap = final_recording_block_bootstrap_mrr(deltas_by_recording)
    final_pass, gate = _final_gate(metrics, bootstrap)

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-final-evidence-v1",
        "status": (
            "FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY"
            if final_pass
            else "FINAL_FAIL_STOP"
        ),
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "final_policy": "ONE_SHOT_GATE_NO_REFIT_NO_TUNING",
        "untouched_final_performer": UNTOUCHED_FINAL_PERFORMER,
        "untouched_final_performer_opened": True,
        "accepted_validation_evidence_sha256": validation["evidence_sha256"],
        "sealed_development_model_artifact_sha256": model_payload["artifact_sha256"],
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "final_source_counts": source_summary,
        "final_event_identity_sha256": event_identity_sha256(events),
        "metrics": metrics,
        "recording_block_bootstrap": bootstrap,
        "gate": gate,
        "final_pass": final_pass,
        "checkpoint_retention_review_eligible": final_pass,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
        "next_gate": "CHECKPOINT_RETENTION_REVIEW" if final_pass else "STOP_FINAL_GATE_FAILED",
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}
