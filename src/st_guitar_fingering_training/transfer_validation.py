from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

import numpy as np

from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource
from .synthetic import MAX_SYNTH_FRET
from .synthetic_behavior import BehaviorRow, STYLES, _feature_vector, build_behavior_rows
from .synthetic_pairwise import evaluate_pairwise_behavior_ranker, train_pairwise_behavior_ranker


REAL_LABEL_SEMANTICS = "observed_behavior_not_teacher_gold"


def _event_id(source: ParsedSource, event, index: int) -> str:
    return f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"


def _observed_voicing(event) -> Voicing:
    return tuple(sorted(
        (placement.sounding_midi, placement.string, placement.fret)
        for placement in event.placements
    ))


def build_real_transfer_rows(
    sources: Iterable[ParsedSource],
    style: str,
) -> tuple[tuple[BehaviorRow, ...], dict]:
    """Build evaluation-only rows for one frozen synthetic specialist.

    Real observed voicings are labels for evaluation only. Candidate generation
    remains deterministic and spans the intake contract's full physical fret
    range; candidates above the synthetic 0..12 training range are retained and
    counted as out-of-training-range rather than silently removed.
    """
    if style not in STYLES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")

    rows: list[BehaviorRow] = []
    chord_events = 0
    ambiguous_events = 0
    single_candidate_events = 0
    common_tone_context_skips = 0
    observed_above_training_range = 0
    candidate_above_training_range = 0

    for source in tuple(sources):
        if len(source.tuning) != 6:
            raise ValueError("Stage 7C transfer validation supports six-string guitars only")
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            chord_events += 1
            observed = _observed_voicing(event)
            pitches = tuple(sorted(placement.sounding_midi for placement in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if not candidates:
                raise ValueError("real transfer chord event has no physically valid candidates")
            if observed not in candidates:
                raise ValueError("real observed voicing missing from deterministic candidate set")

            if max(fret for _, _, fret in observed) > MAX_SYNTH_FRET:
                observed_above_training_range += 1
            if any(max(fret for _, _, fret in candidate) > MAX_SYNTH_FRET for candidate in candidates):
                candidate_above_training_range += 1

            if style == "common_tone" and previous is None:
                previous = observed
                common_tone_context_skips += 1
                continue

            if len(candidates) == 1:
                single_candidate_events += 1
                if style == "common_tone":
                    previous = observed
                continue

            ambiguous_events += 1
            eid = _event_id(source, event, index)
            for candidate in candidates:
                rows.append(BehaviorRow(
                    family_id=source.family_id,
                    event_id=eid,
                    observed=int(candidate == observed),
                    features=_feature_vector(style, candidate, previous),
                ))
            if style == "common_tone":
                previous = observed

    audit = {
        "style": style,
        "real_training_rows": 0,
        "chord_events": chord_events,
        "ambiguous_evaluation_events": ambiguous_events,
        "single_candidate_events_excluded": single_candidate_events,
        "common_tone_first_chord_context_skips": common_tone_context_skips,
        "observed_above_synthetic_training_fret_events": observed_above_training_range,
        "candidate_set_above_synthetic_training_fret_events": candidate_above_training_range,
        "synthetic_training_max_fret": MAX_SYNTH_FRET,
        "real_candidate_fret_range_retained": True,
    }
    return tuple(rows), audit


def _normalize_synthetic_groups(
    synthetic_sources_by_style: Mapping[str, Iterable[ParsedSource]],
) -> dict[str, tuple[ParsedSource, ...]]:
    if set(synthetic_sources_by_style) != set(STYLES):
        raise ValueError("Stage 7C requires exactly one synthetic source group for each specialist")
    groups = {style: tuple(synthetic_sources_by_style[style]) for style in STYLES}
    if any(not groups[style] for style in STYLES):
        raise ValueError("every Stage 7C specialist requires synthetic training sources")
    return groups


def train_frozen_synthetic_specialists(
    synthetic_sources_by_style: Mapping[str, Iterable[ParsedSource]],
) -> dict[str, object]:
    """Fit the five pairwise specialists from synthetic data only.

    The returned estimators are in-memory diagnostic models. No checkpoint is
    serialized or promoted by Stage 7C.
    """
    groups = _normalize_synthetic_groups(synthetic_sources_by_style)

    models: dict[str, object] = {}
    seen_families: set[str] = set()
    seen_hashes: set[str] = set()
    for style in STYLES:
        sources = groups[style]
        family_ids = {source.family_id for source in sources}
        source_hashes = {source.source_sha256 for source in sources}
        if seen_families & family_ids or seen_hashes & source_hashes:
            raise ValueError("synthetic specialist source groups must be disjoint")
        seen_families |= family_ids
        seen_hashes |= source_hashes

        rows = build_behavior_rows(sources, style)
        if not rows:
            raise ValueError(f"no synthetic training rows for specialist: {style}")
        models[style] = train_pairwise_behavior_ranker(rows)
    return models


def _family_metrics(model, rows: tuple[BehaviorRow, ...]) -> dict:
    by_family: dict[str, list[BehaviorRow]] = defaultdict(list)
    for row in rows:
        by_family[row.family_id].append(row)
    if not by_family:
        raise ValueError("no real transfer families with ambiguous evaluation events")

    reports = {}
    for family_id, family_rows in sorted(by_family.items()):
        metrics = evaluate_pairwise_behavior_ranker(model, tuple(family_rows))
        reports[family_id] = {
            "events": metrics.events,
            "top1": metrics.top1_accuracy,
            "mrr": metrics.mean_reciprocal_rank,
            "uniform_random_top1": metrics.uniform_top1_baseline,
        }
    return reports


def _top1_observed_by_event(model, rows: tuple[BehaviorRow, ...]) -> dict[str, bool]:
    grouped: dict[str, list[BehaviorRow]] = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)
    result: dict[str, bool] = {}
    for event_id, event_rows in grouped.items():
        X = np.asarray([row.features for row in event_rows], dtype=np.float64)
        if not np.isfinite(X).all():
            raise ValueError("non-finite real transfer feature matrix")
        scores = np.asarray(model.decision_function(X), dtype=np.float64)
        winner = max(range(len(event_rows)), key=lambda index: (scores[index], -index))
        result[event_id] = bool(event_rows[winner].observed)
    return result


def real_transfer_report(
    models: Mapping[str, object],
    synthetic_sources_by_style: Mapping[str, Iterable[ParsedSource]],
    real_sources: Iterable[ParsedSource],
) -> dict:
    """Evaluate frozen synthetic specialists on an independent real corpus.

    This is a diagnostic transfer test, not training, adaptation, checkpoint
    selection, or production integration. Specialist coverage is an oracle-like
    behavior-bank coverage diagnostic and must not be used as a deployed gating
    policy because it asks whether *any* specialist matched the observed choice.
    """
    if set(models) != set(STYLES):
        raise ValueError("Stage 7C requires all five fitted specialists")
    groups = _normalize_synthetic_groups(synthetic_sources_by_style)

    real_sources = tuple(real_sources)
    if not real_sources:
        raise ValueError("no real transfer sources")

    synthetic_families = {
        source.family_id
        for style in STYLES
        for source in groups[style]
    }
    synthetic_hashes = {
        source.source_sha256
        for style in STYLES
        for source in groups[style]
    }
    real_families = {source.family_id for source in real_sources}
    real_hashes = {source.source_sha256 for source in real_sources}
    if synthetic_families & real_families:
        raise ValueError("synthetic/real family overlap in Stage 7C transfer evaluation")
    if synthetic_hashes & real_hashes:
        raise ValueError("synthetic/real source hash overlap in Stage 7C transfer evaluation")

    specialist_reports = {}
    top1_matches_by_style: dict[str, dict[str, bool]] = {}
    for style in STYLES:
        rows, audit = build_real_transfer_rows(real_sources, style)
        if not rows:
            raise ValueError(f"no ambiguous real transfer events for specialist: {style}")
        metrics = evaluate_pairwise_behavior_ranker(models[style], rows)
        families = _family_metrics(models[style], rows)
        top1_matches_by_style[style] = _top1_observed_by_event(models[style], rows)
        specialist_reports[style] = {
            "events": metrics.events,
            "evaluated_families": len(families),
            "event_weighted_top1": metrics.top1_accuracy,
            "event_weighted_mrr": metrics.mean_reciprocal_rank,
            "uniform_random_top1": metrics.uniform_top1_baseline,
            "macro_family_top1": float(np.mean([item["top1"] for item in families.values()])),
            "macro_family_mrr": float(np.mean([item["mrr"] for item in families.values()])),
            "families": families,
            "audit": audit,
            "previous_context": (
                "observed_previous_real_voicing_diagnostic"
                if style == "common_tone"
                else "none"
            ),
        }

    common_event_ids = set.intersection(
        *(set(top1_matches_by_style[style]) for style in STYLES)
    )
    if not common_event_ids:
        raise ValueError("no common ambiguous real events across all specialists")
    covered = sum(
        any(top1_matches_by_style[style][event_id] for style in STYLES)
        for event_id in common_event_ids
    )

    return {
        "stage": "7C",
        "status": "DIAGNOSTIC",
        "model_bank": "five_frozen_synthetic_pairwise_specialists",
        "synthetic_training_families": len(synthetic_families),
        "real_evaluation_families": len(real_families),
        "domain_disjoint": True,
        "real_training_rows": 0,
        "real_model_fit": False,
        "real_label_semantics": REAL_LABEL_SEMANTICS,
        "specialists": specialist_reports,
        "specialist_coverage": {
            "meaning": "oracle_like_diagnostic_not_deployment_policy",
            "common_events": len(common_event_ids),
            "any_specialist_top1_matches_observed": covered,
            "top1_coverage": covered / len(common_event_ids),
        },
        "checkpoint_retained": False,
        "production_integration": False,
    }
