from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from .dataset import Voicing, valid_chord_voicings
from .guitarset_checkpoint_retention import validate_checkpoint_retention_decision
from .guitarset_voicing_development import (
    Candidate,
    canonical_candidate,
    enumerate_voicing_candidates,
    feature_vector,
)
from .guitarset_voicing_prereg import GUITARSET_VOICING_MAX_FRET
from .guitarset_voicing_validation import load_sealed_development_scorer
from .intake import MAX_FRET


EXPECTED_CHECKPOINT_RETENTION_EVIDENCE_SHA256 = (
    "81ee73897a2e401696137f4ae950354b8c8fdde24b6a6fe2d16b612ae027d722"
)
EXPECTED_MODEL_ARTIFACT_SHA256 = (
    "5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869"
)
STANDARD_TUNING = (64, 59, 55, 50, 45, 40)  # strings 1..6, high E to low E


def _normalize_candidate(candidate: Iterable[Iterable[int]]) -> Candidate:
    rows = []
    for placement in candidate:
        values = tuple(placement)
        if len(values) != 3:
            raise ValueError("candidate placement must be (pitch_midi, string, fret)")
        pitch, string, fret = (int(value) for value in values)
        rows.append((pitch, string, fret))
    normalized = tuple(sorted(rows))
    if not normalized:
        raise ValueError("candidate must contain at least one placement")
    if len({string for _, string, _ in normalized}) != len(normalized):
        raise ValueError("candidate reuses a string")
    return normalized


def _json_candidate(candidate: Candidate | None):
    if candidate is None:
        return None
    return [[int(pitch), int(string), int(fret)] for pitch, string, fret in candidate]


def build_shadow_observation(
    *,
    pitches_midi: Iterable[int],
    tuning: Iterable[int],
    authoritative_candidates: Iterable[Iterable[Iterable[int]]],
    authoritative_selected_candidate: Iterable[Iterable[int]] | None,
    model_path: str | Path,
    final_evidence_path: str | Path,
    retention_decision_path: str | Path,
) -> dict:
    """Build a non-authoritative shadow observation without changing engine output.

    The learned model is permitted to score only when the caller supplies the complete
    authoritative `valid_chord_voicings()` set and that entire set is inside the frozen
    GuitarSet model domain (standard tuning, frets 0..19). If the authoritative engine
    exposes any valid 20..24-fret candidate, the shadow model is not run; candidates are
    never truncated to make the event fit the learned model.
    """

    if MAX_FRET != 24 or GUITARSET_VOICING_MAX_FRET != 19:
        raise RuntimeError("engine/model fret boundary drift")

    tuning_tuple = tuple(int(value) for value in tuning)
    if tuning_tuple != STANDARD_TUNING:
        raise ValueError("GuitarSet shadow model supports frozen standard tuning only")

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    if not 2 <= len(pitches) <= 6 or any(not 0 <= pitch <= 127 for pitch in pitches):
        raise ValueError("shadow voicing requires 2..6 MIDI pitches in range 0..127")

    supplied = tuple(_normalize_candidate(candidate) for candidate in authoritative_candidates)
    if len(set(supplied)) != len(supplied):
        raise ValueError("authoritative candidate set contains duplicates")

    expected_authority: tuple[Voicing, ...] = valid_chord_voicings(pitches, tuning_tuple)
    if not expected_authority:
        raise ValueError("authoritative physical candidate set is empty")
    if tuple(sorted(supplied)) != expected_authority:
        raise ValueError("shadow seam requires the complete exact valid_chord_voicings() set")

    selected = None
    if authoritative_selected_candidate is not None:
        selected = _normalize_candidate(authoritative_selected_candidate)
        if selected not in expected_authority:
            raise ValueError("authoritative selected candidate is outside physical authority set")

    retention = validate_checkpoint_retention_decision(
        retention_decision_path,
        model_path=model_path,
        final_evidence_path=final_evidence_path,
    )
    if retention.get("evidence_sha256") != EXPECTED_CHECKPOINT_RETENTION_EVIDENCE_SHA256:
        raise ValueError("checkpoint retention evidence identity drift")
    if retention.get("retained_model_artifact_sha256") != EXPECTED_MODEL_ARTIFACT_SHA256:
        raise ValueError("retained checkpoint identity drift")
    if not retention.get("checkpoint_retention_authorized"):
        raise ValueError("checkpoint retention is not authorized")
    for key in (
        "checkpoint_mutation_authorized",
        "refit_authorized",
        "tuning_authorized",
        "shadow_integration_authorized",
        "runtime_connection_authorized",
        "production_authorized",
    ):
        if retention.get(key) is not False:
            raise ValueError(f"retention boundary {key!r} must remain false before shadow review")

    out_of_model_domain = tuple(
        candidate
        for candidate in expected_authority
        if any(fret > GUITARSET_VOICING_MAX_FRET for _, _, fret in candidate)
    )
    base = {
        "schema": "st-guitar-guitarset-observed-voicing-shadow-observation-v1",
        "mode": "OFFLINE_NON_AUTHORITATIVE_SHADOW_ONLY",
        "physical_candidate_authority": "valid_chord_voicings",
        "retained_model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "checkpoint_retention_evidence_sha256": EXPECTED_CHECKPOINT_RETENTION_EVIDENCE_SHA256,
        "pitches_midi": list(pitches),
        "tuning_midi_by_string": list(tuning_tuple),
        "authoritative_candidate_count": len(expected_authority),
        "authoritative_selected_candidate": _json_candidate(selected),
        "authoritative_decision_effect_authorized": False,
        "checkpoint_mutation_authorized": False,
        "refit_authorized": False,
        "tuning_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }

    if out_of_model_domain:
        return {
            **base,
            "status": "SHADOW_NOT_SCORED_MODEL_DOMAIN_INCOMPLETE",
            "shadow_scored": False,
            "model_domain_complete": False,
            "out_of_model_domain_candidate_count": len(out_of_model_domain),
            "shadow_model_top_candidate": None,
            "agreement_with_authoritative_selection": None,
            "candidate_scores": [],
        }

    model_candidates = enumerate_voicing_candidates(pitches)
    if model_candidates != expected_authority:
        raise AssertionError("frozen GuitarSet candidate set disagrees with physical authority")

    scorer, model_payload = load_sealed_development_scorer(model_path)
    if model_payload.get("artifact_sha256") != EXPECTED_MODEL_ARTIFACT_SHA256:
        raise ValueError("loaded shadow scorer identity drift")
    matrix = np.asarray([feature_vector(candidate) for candidate in expected_authority], dtype=np.float64)
    scores = np.asarray(scorer.decision_function(matrix), dtype=np.float64)
    if scores.shape != (len(expected_authority),) or not np.isfinite(scores).all():
        raise ValueError("shadow scorer returned invalid scores")

    order = sorted(
        range(len(expected_authority)),
        key=lambda index: (-float(scores[index]), expected_authority[index]),
    )
    top = expected_authority[order[0]]
    candidate_scores = [
        {
            "candidate": _json_candidate(expected_authority[index]),
            "score_hex": float(scores[index]).hex(),
            "rank": rank,
        }
        for rank, index in enumerate(order, start=1)
    ]

    return {
        **base,
        "status": "SHADOW_SCORED_NON_AUTHORITATIVE",
        "shadow_scored": True,
        "model_domain_complete": True,
        "out_of_model_domain_candidate_count": 0,
        "shadow_model_top_candidate": _json_candidate(top),
        "agreement_with_authoritative_selection": None if selected is None else top == selected,
        "candidate_scores": candidate_scores,
    }
