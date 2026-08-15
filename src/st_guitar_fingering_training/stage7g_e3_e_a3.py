from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Mapping

import numpy as np

from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource, parse_guitar_musicxml
from .synthetic import family_to_musicxml, generate_synthetic_family
from .synthetic_balanced import balanced_family_indices
from .synthetic_behavior import _feature_vector, build_behavior_rows
from .synthetic_pairwise import (
    build_pairwise_training_matrix,
    pairwise_behavior_cross_validation_report,
    train_pairwise_behavior_ranker,
)
from .target_free_musicxml import TargetFreeSource


A3_STYLES = ("open_low", "compact")
EXPECTED_TRAINING_EVENTS = {"open_low": 480, "compact": 480}
EXPECTED_PAIRWISE_MATRIX_SHAPES = {
    "open_low": (6900, 4),
    "compact": (7708, 4),
}
EXPECTED_STAGE7B_C2_MACRO_TOP1 = {"open_low": 1.0, "compact": 1.0}


def _stage7b_style_sources() -> dict[str, tuple[ParsedSource, ...]]:
    groups: dict[str, list[ParsedSource]] = {style: [] for style in A3_STYLES}
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for family_index in balanced_family_indices(100):
            family = generate_synthetic_family(family_index, events_per_family=24)
            if family.style not in groups:
                continue
            path = root / f"{family.family_id}.xml"
            path.write_text(family_to_musicxml(family), encoding="utf-8")
            groups[family.style].append(parse_guitar_musicxml(path, family_id=family.family_id))
    result = {style: tuple(groups[style]) for style in A3_STYLES}
    if any(len(result[style]) != 20 for style in A3_STYLES):
        raise AssertionError("Stage 7B reconstruction requires exactly 20 families per A3 specialist")
    return result


def reconstruct_frozen_open_low_compact_specialists() -> tuple[dict[str, object], dict]:
    """Reconstruct the already-approved Stage 7B open_low and compact specialists.

    Training data is synthetic RULE_PREFERRED data only. This function never
    reads E3-E Teacher-GOLD, never serializes a checkpoint, and fails closed if
    the historical Stage 7B-C2 reconstruction guard changes.
    """

    groups = _stage7b_style_sources()
    models: dict[str, object] = {}
    guard: dict[str, dict] = {}

    for style in A3_STYLES:
        sources = groups[style]
        rows = build_behavior_rows(sources, style)
        event_ids = {row.event_id for row in rows}
        X, _ = build_pairwise_training_matrix(rows)
        cv = pairwise_behavior_cross_validation_report(sources, style, folds=5)

        expected_events = EXPECTED_TRAINING_EVENTS[style]
        expected_shape = EXPECTED_PAIRWISE_MATRIX_SHAPES[style]
        expected_top1 = EXPECTED_STAGE7B_C2_MACRO_TOP1[style]
        if len(event_ids) != expected_events:
            raise AssertionError(f"{style} Stage 7B training-event reconstruction drift")
        if tuple(X.shape) != expected_shape:
            raise AssertionError(f"{style} Stage 7B pairwise matrix reconstruction drift")
        if not np.isclose(float(cv["macro_top1"]), expected_top1, rtol=0.0, atol=1e-15):
            raise AssertionError(f"{style} Stage 7B-C2 macro Top-1 reconstruction drift")

        models[style] = train_pairwise_behavior_ranker(rows)
        guard[style] = {
            "synthetic_families": len(sources),
            "training_events": len(event_ids),
            "pairwise_matrix_shape": list(X.shape),
            "stage7b_c2_macro_top1": float(cv["macro_top1"]),
            "checkpoint_retained": False,
        }

    return models, {
        "status": "PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION",
        "balanced_synthetic_families": 100,
        "specialists": guard,
        "teacher_gold_used": False,
        "checkpoint_retained": False,
    }


def _winner(candidates: tuple[Voicing, ...], model: object, style: str) -> Voicing:
    features = np.asarray(
        [_feature_vector(style, candidate, None) for candidate in candidates],
        dtype=np.float64,
    )
    scores = np.asarray(model.decision_function(features), dtype=np.float64)
    if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
        raise ValueError(f"invalid A3 specialist score vector for {style}")
    index = max(range(len(candidates)), key=lambda item: (scores[item], -item))
    return candidates[index]


def _event_id(source: TargetFreeSource, event, index: int) -> str:
    return f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"


def build_open_low_compact_disagreement_inventory(
    sources: Iterable[TargetFreeSource],
    *,
    specialist_models: Mapping[str, object],
) -> dict:
    """Build an aggregate-only A3 inventory from target-free E3-E sources.

    No teacher task is created here. The returned object contains counts and a
    digest of disagreement event IDs, but not per-event specialist predictions.
    """

    if set(specialist_models) != set(A3_STYLES):
        raise ValueError("A3 requires exactly frozen open_low and compact specialists")
    source_rows = tuple(sources)
    if not source_rows:
        raise ValueError("A3 requires at least one eligible target-free source")

    family_ids = [source.family_id for source in source_rows]
    source_hashes = [source.source_sha256.lower() for source in source_rows]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("A3 source families must be unique")
    if len(source_hashes) != len(set(source_hashes)):
        raise ValueError("A3 source hashes must be unique")
    if any(len(source.tuning) != 6 for source in source_rows):
        raise ValueError("A3 supports six-string target-free sources only")

    per_family: dict[str, dict] = {}
    disagreement_ids: list[str] = []
    candidate_counts: list[int] = []
    total_events = 0
    chord_events = 0
    zero_candidate_chords = 0
    single_candidate_chords = 0
    ambiguous_chords = 0
    disagreements = 0

    for source in sorted(source_rows, key=lambda item: item.family_id):
        fam = {
            "pitched_events": len(source.events),
            "chord_events": 0,
            "zero_candidate_chords": 0,
            "single_candidate_chords": 0,
            "ambiguous_chords": 0,
            "open_low_compact_disagreements": 0,
        }
        total_events += len(source.events)
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            chord_events += 1
            fam["chord_events"] += 1
            candidates = valid_chord_voicings(event.pitches_midi, event.tuning)
            if not candidates:
                zero_candidate_chords += 1
                fam["zero_candidate_chords"] += 1
                continue
            if len(candidates) == 1:
                single_candidate_chords += 1
                fam["single_candidate_chords"] += 1
                continue

            ambiguous_chords += 1
            fam["ambiguous_chords"] += 1
            candidate_counts.append(len(candidates))
            open_low = _winner(candidates, specialist_models["open_low"], "open_low")
            compact = _winner(candidates, specialist_models["compact"], "compact")
            if open_low != compact:
                disagreements += 1
                fam["open_low_compact_disagreements"] += 1
                disagreement_ids.append(_event_id(source, event, index))

        fam["disagreement_rate_among_ambiguous"] = (
            fam["open_low_compact_disagreements"] / fam["ambiguous_chords"]
            if fam["ambiguous_chords"]
            else 0.0
        )
        per_family[source.family_id] = fam

    if ambiguous_chords <= 0:
        raise ValueError("A3 found no deterministic ambiguous chord events")
    if disagreements != len(disagreement_ids) or len(disagreement_ids) != len(set(disagreement_ids)):
        raise AssertionError("A3 disagreement event identity accounting failed")

    digest = sha256("\n".join(sorted(disagreement_ids)).encode("utf-8")).hexdigest()
    families_with_disagreement = sum(
        row["open_low_compact_disagreements"] > 0 for row in per_family.values()
    )

    return {
        "schema": "st-guitar-stage7g-e3-e-a3-disagreement-inventory-v1",
        "stage": "7G-E3-E-A3",
        "status": "TARGET_BLIND_OPEN_LOW_COMPACT_INVENTORY_COMPLETE",
        "eligible_families": len(source_rows),
        "families_with_disagreement": families_with_disagreement,
        "pitched_events": total_events,
        "chord_events": chord_events,
        "zero_candidate_chords": zero_candidate_chords,
        "single_candidate_chords": single_candidate_chords,
        "ambiguous_chords": ambiguous_chords,
        "open_low_compact_disagreements": disagreements,
        "disagreement_rate_among_ambiguous": disagreements / ambiguous_chords,
        "disagreement_event_id_set_digest_sha256": digest,
        "disagreement_event_id_digest_method": "sha256(newline-joined sorted exact event ids; no trailing newline)",
        "ambiguous_candidate_count_min": min(candidate_counts),
        "ambiguous_candidate_count_max": max(candidate_counts),
        "ambiguous_candidate_count_mean": float(np.mean(candidate_counts)),
        "families": per_family,
        "teacher_gold_generated": False,
        "teacher_gold_answers_read": False,
        "router_scored": False,
        "e3e_model_fit": False,
        "threshold_selected": False,
        "checkpoint_retained": False,
        "production_integration": False,
    }
