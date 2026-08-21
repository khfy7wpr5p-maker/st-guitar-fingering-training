from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
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
    canonical_candidate,
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

VALIDATION_PERFORMER = "03"
UNTOUCHED_FINAL_PERFORMER = "02"
EXPECTED_VALIDATION_RECORDINGS = 30
EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256 = (
    "5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869"
)
VALIDATION_BOOTSTRAP_REPETITIONS = 2000
VALIDATION_BOOTSTRAP_SEED = 0
VALIDATION_CONFIDENCE = 0.95


@dataclass(frozen=True)
class ValidationEvent:
    performer: str
    recording_id: str
    voicing_id: str
    observed: Candidate
    candidates: tuple[Candidate, ...]


class SealedLinearVoicingScorer:
    """Inference-only scorer reconstructed from the sealed DEVELOPMENT artifact."""

    def __init__(self, *, mean: Iterable[float], scale: Iterable[float], coef: Iterable[float]):
        self.mean = np.asarray(tuple(mean), dtype=np.float64)
        self.scale = np.asarray(tuple(scale), dtype=np.float64)
        self.coef = np.asarray(tuple(coef), dtype=np.float64)
        if self.mean.shape != (28,) or self.scale.shape != (28,) or self.coef.shape != (28,):
            raise ValueError("sealed GuitarSet model must contain exactly 28 parameters per vector")
        if not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or not np.isfinite(self.coef).all():
            raise ValueError("sealed GuitarSet model contains non-finite parameters")
        if np.any(self.scale <= 0):
            raise ValueError("sealed GuitarSet model scaler contains non-positive scale")

    def decision_function(self, X) -> np.ndarray:
        matrix = np.asarray(X, dtype=np.float64)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.ndim != 2 or matrix.shape[1] != 28 or not np.isfinite(matrix).all():
            raise ValueError("validation scorer requires finite Nx28 feature matrix")
        return ((matrix - self.mean) / self.scale) @ self.coef


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _decode_hex_vector(values, *, field: str) -> tuple[float, ...]:
    if not isinstance(values, list) or len(values) != 28 or not all(isinstance(value, str) for value in values):
        raise ValueError(f"sealed model field {field!r} is not an exact 28D hexadecimal vector")
    try:
        decoded = tuple(float.fromhex(value) for value in values)
    except ValueError as exc:
        raise ValueError(f"sealed model field {field!r} contains invalid hexadecimal float") from exc
    if not all(math.isfinite(value) for value in decoded):
        raise ValueError(f"sealed model field {field!r} contains non-finite values")
    return decoded


def load_sealed_development_scorer(path: str | Path) -> tuple[SealedLinearVoicingScorer, dict]:
    assert_frozen_protocol()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sealed DEVELOPMENT model artifact must be one JSON object")
    verify_sealed_json(payload, "artifact_sha256")
    if payload.get("artifact_sha256") != EXPECTED_DEVELOPMENT_MODEL_ARTIFACT_SHA256:
        raise ValueError("DEVELOPMENT model artifact identity drift")
    required = {
        "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v1",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "training_role": "DEVELOPMENT",
        "validation_only_artifact": True,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"sealed DEVELOPMENT model field {key!r} drift")
    if payload.get("training_performers") != ["00", "01", "04", "05"]:
        raise ValueError("sealed DEVELOPMENT model performer set drift")
    params = payload.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("sealed DEVELOPMENT model parameters missing")
    mean = _decode_hex_vector(params.get("scaler_mean_hex"), field="scaler_mean_hex")
    scale = _decode_hex_vector(params.get("scaler_scale_hex"), field="scaler_scale_hex")
    coef = _decode_hex_vector(params.get("logistic_coef_hex"), field="logistic_coef_hex")
    scorer = SealedLinearVoicingScorer(mean=mean, scale=scale, coef=coef)
    return scorer, payload


def _validation_member(source_member: str) -> bool:
    performer, _, _ = parse_comp_member_identity(source_member)
    return performer == VALIDATION_PERFORMER


def load_validation_events(path: str | Path) -> tuple[tuple[ValidationEvent, ...], dict]:
    """Read only performer 03 JAMS bytes after archive/split identity is verified."""

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
        validation_members = tuple(member for member in members if _validation_member(member))
        if len(validation_members) != EXPECTED_VALIDATION_RECORDINGS:
            raise ValueError("unexpected GuitarSet VALIDATION recording count")

        # Critical leakage boundary: no DEVELOPMENT refit and no performer 02 read.
        for member in validation_members:
            accepted, rejected = extract_comp_jams(member, archive.read(member))
            notes.extend(accepted)
            quarantined.extend(rejected)

    voicings = derive_strum_voicings(notes)
    events: list[ValidationEvent] = []
    single_candidate = 0
    full_candidate_count = 0
    for voicing in voicings:
        performer, _, _ = parse_comp_member_identity(voicing.source_member)
        if performer != VALIDATION_PERFORMER:
            raise AssertionError("non-validation voicing entered one-shot validation loader")
        pitches = tuple(pitch for pitch, _, _ in voicing.placements)
        candidates = enumerate_voicing_candidates(pitches)
        if not candidates:
            raise ValueError("GuitarSet VALIDATION voicing has no physical candidates")
        if voicing.placements not in candidates:
            raise ValueError("observed GuitarSet VALIDATION voicing missing from exact candidate set")
        full_candidate_count += len(candidates)
        if len(candidates) == 1:
            single_candidate += 1
            continue
        events.append(
            ValidationEvent(
                performer=performer,
                recording_id=voicing.recording_id,
                voicing_id=voicing.voicing_id,
                observed=voicing.placements,
                candidates=candidates,
            )
        )

    events.sort(key=lambda event: (event.recording_id, event.voicing_id))
    if len({event.voicing_id for event in events}) != len(events):
        raise AssertionError("duplicate GuitarSet VALIDATION voicing IDs")
    summary = {
        "recordings": EXPECTED_VALIDATION_RECORDINGS,
        "accepted_notes": len(notes),
        "quarantined_notes": len(quarantined),
        "derived_voicings": len(voicings),
        "ambiguous_voicings": len(events),
        "single_candidate_voicings": single_candidate,
        "full_candidate_count_across_all_voicings": full_candidate_count,
        "performer": VALIDATION_PERFORMER,
    }
    return tuple(events), summary


def _mrr_delta_by_recording(
    scorer: SealedLinearVoicingScorer, events: Iterable[ValidationEvent]
) -> dict[str, tuple[float, ...]]:
    by_recording: dict[str, list[float]] = {}
    for event in events:
        matrix = np.asarray([feature_vector(candidate) for candidate in event.candidates], dtype=np.float64)
        scores = np.asarray(scorer.decision_function(matrix), dtype=np.float64)
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
        delta = (1.0 / learned_rank) - (1.0 / baseline_rank)
        by_recording.setdefault(event.recording_id, []).append(float(delta))
    return {key: tuple(values) for key, values in sorted(by_recording.items())}


def recording_block_bootstrap_mrr(
    deltas_by_recording: dict[str, tuple[float, ...]],
    *,
    repetitions: int = VALIDATION_BOOTSTRAP_REPETITIONS,
    seed: int = VALIDATION_BOOTSTRAP_SEED,
) -> dict:
    """Frozen v1 bootstrap: resample recordings, pool their event-level MRR deltas."""

    if repetitions != VALIDATION_BOOTSTRAP_REPETITIONS or seed != VALIDATION_BOOTSTRAP_SEED:
        raise ValueError("validation bootstrap repetitions/seed are frozen at 2000/0")
    recording_ids = tuple(sorted(deltas_by_recording))
    if not recording_ids or any(not deltas_by_recording[key] for key in recording_ids):
        raise ValueError("recording-block bootstrap requires non-empty ambiguous-event blocks")

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
            raise AssertionError("bootstrap sampled zero validation events")
        samples.append(total / count)

    ordered = sorted(samples)
    alpha = 1.0 - VALIDATION_CONFIDENCE
    lower_index = max(0, math.ceil((alpha / 2.0) * repetitions) - 1)
    upper_index = min(repetitions - 1, math.ceil((1.0 - alpha / 2.0) * repetitions) - 1)
    return {
        "method": "RECORDING_BLOCK_RESAMPLE_WITH_REPLACEMENT_POOL_EVENT_MRR_DELTA",
        "repetitions": repetitions,
        "seed": seed,
        "confidence": VALIDATION_CONFIDENCE,
        "recording_block_count": len(recording_ids),
        "lower_order_statistic_index_zero_based": lower_index,
        "upper_order_statistic_index_zero_based": upper_index,
        "lower_bound": float(ordered[lower_index]),
        "upper_bound": float(ordered[upper_index]),
        "bootstrap_mean": float(sum(samples) / len(samples)),
        "sample_identity_sha256": _canonical_sha256([float(value).hex() for value in samples]),
    }


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
    }
    return all(item["pass"] for item in gate.values()), gate


def run_validation_once(
    archive_path: str | Path,
    *,
    sealed_model_path: str | Path,
) -> dict:
    """Execute the frozen one-shot performer-03 gate without fitting any model."""

    assert_frozen_protocol()
    scorer, model_payload = load_sealed_development_scorer(sealed_model_path)
    events, source_summary = load_validation_events(archive_path)
    metrics = evaluate_model(scorer, events)
    deltas_by_recording = _mrr_delta_by_recording(scorer, events)
    pooled_delta = sum(sum(values) for values in deltas_by_recording.values()) / sum(
        len(values) for values in deltas_by_recording.values()
    )
    if abs(pooled_delta - metrics["event_mrr_delta"]) > 1e-12:
        raise AssertionError("validation MRR bootstrap input disagrees with canonical evaluation")
    bootstrap = recording_block_bootstrap_mrr(deltas_by_recording)
    validation_pass, gate = _validation_gate(source_summary, metrics, bootstrap)

    core = {
        "schema": "st-guitar-guitarset-observed-voicing-validation-evidence-v1",
        "status": "VALIDATION_PASS_FINAL_STILL_CLOSED" if validation_pass else "VALIDATION_FAIL_STOP",
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "sealed_development_model_artifact_sha256": model_payload["artifact_sha256"],
        "split_version": "GUITARSET-SPLIT.v1",
        "validation_performer": VALIDATION_PERFORMER,
        "validation_performer_opened": True,
        "validation_policy": "ONE_SHOT_GATE_NO_TUNING",
        "model_refit_performed": False,
        "hyperparameter_tuning_performed": False,
        "validation_source_counts": source_summary,
        "validation_event_identity_sha256": event_identity_sha256(events),
        "metrics": metrics,
        "recording_block_bootstrap": bootstrap,
        "gate": gate,
        "validation_pass": validation_pass,
        "untouched_final_performer": UNTOUCHED_FINAL_PERFORMER,
        "untouched_final_performer_opened": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "final_access_authorized": False,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "next_gate": (
            "OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW"
            if validation_pass
            else "STOP_VALIDATION_GATE_FAILED"
        ),
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def verify_validation_evidence(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("validation evidence must be one JSON object")
    claimed = payload.get("evidence_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("validation evidence is missing SHA-256 seal")
    core = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    if _canonical_sha256(core) != claimed:
        raise ValueError("validation evidence SHA-256 mismatch")
