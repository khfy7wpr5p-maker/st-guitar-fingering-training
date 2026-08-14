from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log1p
from typing import Iterable, Mapping

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .dataset import Voicing, valid_chord_voicings
from .intake import MAX_FRET, ParsedSource
from .synthetic_behavior import _feature_vector, deterministic_style_folds


STATELESS_ROUTER_STYLES = (
    "open_low",
    "compact",
    "mid_position",
    "high_position",
)

ROUTER_LABEL_SEMANTICS = "specialist_top1_matches_observed_behavior_not_teacher_gold"

ROUTER_FEATURE_NAMES = (
    "chord_size",
    "pitch_span",
    "mean_pitch",
    "candidate_count_log1p",
    "candidate_open_fraction",
    "candidate_mean_fret_mean",
    "candidate_span_mean",
    "top_open_ratio",
    "top_mean_fret",
    "top_max_fret",
    "top_fret_span",
    "specialist_score_margin",
    "specialist_score_spread",
    "style_open_low",
    "style_compact",
    "style_mid_position",
    "style_high_position",
)


@dataclass(frozen=True)
class RouterRow:
    family_id: str
    event_id: str
    style: str
    success: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class RouterMetrics:
    events: int
    router_top1: float
    always_open_low_top1: float
    stateless_oracle_coverage: float
    selected_style_counts: dict[str, int]


def _event_id(source: ParsedSource, event, index: int) -> str:
    return f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"


def _observed_voicing(event) -> Voicing:
    return tuple(sorted(
        (placement.sounding_midi, placement.string, placement.fret)
        for placement in event.placements
    ))


def _voicing_stats(voicing: Voicing) -> tuple[float, float, float, float]:
    frets = [fret for _, _, fret in voicing]
    open_ratio = sum(fret == 0 for fret in frets) / len(frets)
    mean_fret = sum(frets) / len(frets)
    max_fret = max(frets)
    fret_span = max(frets) - min(frets)
    return open_ratio, mean_fret, max_fret, fret_span


def _router_feature_vector(
    pitches: tuple[int, ...],
    candidates: tuple[Voicing, ...],
    top_candidate: Voicing,
    specialist_scores: np.ndarray,
    style: str,
) -> tuple[float, ...]:
    """Build target-blind router features.

    The observed real voicing is intentionally absent from this signature. The
    router may use only the current pitches, deterministic physical candidate
    set, and one frozen stateless specialist's own prediction geometry.
    """
    if style not in STATELESS_ROUTER_STYLES:
        raise ValueError(f"unsupported stateless router style: {style}")
    if len(candidates) < 2:
        raise ValueError("stateless router requires an ambiguous candidate set")
    scores = np.asarray(specialist_scores, dtype=np.float64)
    if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
        raise ValueError("invalid specialist score vector")

    candidate_stats = [_voicing_stats(candidate) for candidate in candidates]
    top_open, top_mean, top_max, top_span = _voicing_stats(top_candidate)
    sorted_scores = np.sort(scores)
    margin = float(sorted_scores[-1] - sorted_scores[-2])
    spread = float(sorted_scores[-1] - sorted_scores[0])
    style_one_hot = tuple(float(style == item) for item in STATELESS_ROUTER_STYLES)

    values = (
        len(pitches) / 6.0,
        (max(pitches) - min(pitches)) / 48.0,
        (sum(pitches) / len(pitches)) / 127.0,
        log1p(len(candidates)),
        sum(stats[0] > 0.0 for stats in candidate_stats) / len(candidate_stats),
        float(np.mean([stats[1] for stats in candidate_stats])) / MAX_FRET,
        float(np.mean([stats[3] for stats in candidate_stats])) / MAX_FRET,
        top_open,
        top_mean / MAX_FRET,
        top_max / MAX_FRET,
        top_span / MAX_FRET,
        margin,
        spread,
        *style_one_hot,
    )
    if len(values) != len(ROUTER_FEATURE_NAMES) or not np.isfinite(np.asarray(values)).all():
        raise AssertionError("invalid stateless router feature vector")
    return tuple(float(value) for value in values)


def _validate_models(models: Mapping[str, object]) -> None:
    missing = set(STATELESS_ROUTER_STYLES) - set(models)
    if missing:
        raise ValueError(f"missing stateless specialists: {sorted(missing)}")


def build_stateless_router_rows(
    real_sources: Iterable[ParsedSource],
    specialist_models: Mapping[str, object],
) -> tuple[tuple[RouterRow, ...], dict]:
    """Create real-behavior router supervision without target feature leakage.

    `success` is an evaluation/training label derived from whether a frozen
    specialist's Top-1 candidate equals the observed Guitar Pro voicing. The
    observed voicing never enters the feature vector. `common_tone` is excluded
    from Stage 7D-A because Stage 7C-R1 measured it with teacher-forced previous
    real voicing context; rollout-safe context is deferred to a later stage.
    """
    _validate_models(specialist_models)
    sources = tuple(real_sources)
    if not sources:
        raise ValueError("no real sources for stateless router")

    rows: list[RouterRow] = []
    chord_events = 0
    ambiguous_events = 0
    single_candidate_events = 0

    for source in sources:
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            chord_events += 1
            observed = _observed_voicing(event)
            pitches = tuple(sorted(placement.sounding_midi for placement in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if observed not in candidates:
                raise ValueError("real observed voicing missing from deterministic candidate set")
            if len(candidates) == 1:
                single_candidate_events += 1
                continue
            ambiguous_events += 1
            event_id = _event_id(source, event, index)

            for style in STATELESS_ROUTER_STYLES:
                X = np.asarray(
                    [_feature_vector(style, candidate, None) for candidate in candidates],
                    dtype=np.float64,
                )
                scores = np.asarray(specialist_models[style].decision_function(X), dtype=np.float64)
                if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
                    raise ValueError("invalid frozen specialist scores")
                winner = max(range(len(candidates)), key=lambda item: (scores[item], -item))
                top_candidate = candidates[winner]
                rows.append(RouterRow(
                    family_id=source.family_id,
                    event_id=event_id,
                    style=style,
                    success=int(top_candidate == observed),
                    features=_router_feature_vector(
                        pitches,
                        candidates,
                        top_candidate,
                        scores,
                        style,
                    ),
                ))

    if not rows:
        raise ValueError("no ambiguous real events for stateless router")
    audit = {
        "stage": "7D-A",
        "router_kind": "target_blind_stateless_specialist_success_router",
        "label_semantics": ROUTER_LABEL_SEMANTICS,
        "styles": list(STATELESS_ROUTER_STYLES),
        "common_tone_included": False,
        "observed_target_in_features": False,
        "chord_events": chord_events,
        "ambiguous_events": ambiguous_events,
        "single_candidate_events_excluded": single_candidate_events,
        "rows_per_ambiguous_event": len(STATELESS_ROUTER_STYLES),
        "physical_candidates": "deterministic_only",
    }
    return tuple(rows), audit


def _group_router_rows(rows: tuple[RouterRow, ...]) -> dict[str, list[RouterRow]]:
    grouped: dict[str, list[RouterRow]] = defaultdict(list)
    for row in rows:
        if row.style not in STATELESS_ROUTER_STYLES:
            raise ValueError("router row contains unsupported style")
        if row.success not in (0, 1):
            raise ValueError("router success label must be binary")
        if len(row.features) != len(ROUTER_FEATURE_NAMES):
            raise ValueError("router feature dimension mismatch")
        grouped[row.event_id].append(row)
    if not grouped:
        raise ValueError("no stateless router events")
    expected = set(STATELESS_ROUTER_STYLES)
    for event_rows in grouped.values():
        if {row.style for row in event_rows} != expected or len(event_rows) != len(expected):
            raise ValueError("each router event must contain exactly the four stateless specialists")
        if len({row.family_id for row in event_rows}) != 1:
            raise ValueError("router event cannot span families")
    return grouped


def train_stateless_router(rows: tuple[RouterRow, ...]):
    _group_router_rows(rows)
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.success for row in rows], dtype=np.int64)
    if not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("router training requires finite features and both success classes")
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
    )
    model.fit(X, y)
    return model


def evaluate_stateless_router(model, rows: tuple[RouterRow, ...]) -> RouterMetrics:
    grouped = _group_router_rows(rows)
    correct = 0
    always_open = 0
    oracle = 0
    selected = Counter()

    for event_rows in grouped.values():
        ordered = sorted(event_rows, key=lambda row: STATELESS_ROUTER_STYLES.index(row.style))
        X = np.asarray([row.features for row in ordered], dtype=np.float64)
        probabilities = np.asarray(model.predict_proba(X)[:, 1], dtype=np.float64)
        winner = max(range(len(ordered)), key=lambda item: (probabilities[item], -item))
        chosen = ordered[winner]
        selected[chosen.style] += 1
        correct += chosen.success
        always_open += next(row.success for row in ordered if row.style == "open_low")
        oracle += int(any(row.success for row in ordered))

    events = len(grouped)
    return RouterMetrics(
        events=events,
        router_top1=correct / events,
        always_open_low_top1=always_open / events,
        stateless_oracle_coverage=oracle / events,
        selected_style_counts={style: selected.get(style, 0) for style in STATELESS_ROUTER_STYLES},
    )


def stateless_router_cross_validation_report(
    rows: tuple[RouterRow, ...],
    folds: int = 5,
) -> dict:
    """Family-isolated CV for the first target-blind specialist router.

    Real observed behavior is used only to form binary specialist-success
    labels inside the training folds and to score validation outcomes. No
    validation family contributes rows to the fitted router.
    """
    grouped = _group_router_rows(rows)
    family_ids = tuple(sorted({row.family_id for row in rows}))
    fold_family_ids = deterministic_style_folds(family_ids, folds=folds)

    fold_reports = []
    for fold_index, validation_tuple in enumerate(fold_family_ids):
        validation_ids = set(validation_tuple)
        train_ids = set(family_ids) - validation_ids
        if not train_ids or train_ids & validation_ids:
            raise AssertionError("family leakage in stateless router CV")
        train_rows = tuple(row for row in rows if row.family_id in train_ids)
        validation_rows = tuple(row for row in rows if row.family_id in validation_ids)
        if {row.family_id for row in train_rows} & {row.family_id for row in validation_rows}:
            raise AssertionError("router train/validation families overlap")

        model = train_stateless_router(train_rows)
        metrics = evaluate_stateless_router(model, validation_rows)
        fold_reports.append({
            "fold": fold_index + 1,
            "train_families": sorted(train_ids),
            "validation_families": sorted(validation_ids),
            "train_family_count": len(train_ids),
            "validation_family_count": len(validation_ids),
            "validation_events": metrics.events,
            "router_top1": metrics.router_top1,
            "always_open_low_top1": metrics.always_open_low_top1,
            "router_delta_vs_open_low": metrics.router_top1 - metrics.always_open_low_top1,
            "stateless_oracle_coverage": metrics.stateless_oracle_coverage,
            "selected_style_counts": metrics.selected_style_counts,
        })

    return {
        "stage": "7D-A",
        "status": "DIAGNOSTIC_PROTOCOL",
        "router_kind": "target_blind_stateless_specialist_success_router",
        "family_count": len(family_ids),
        "fold_count": folds,
        "family_isolated": True,
        "observed_target_in_features": False,
        "label_semantics": ROUTER_LABEL_SEMANTICS,
        "styles": list(STATELESS_ROUTER_STYLES),
        "common_tone_included": False,
        "macro_router_top1": float(np.mean([fold["router_top1"] for fold in fold_reports])),
        "macro_always_open_low_top1": float(np.mean([fold["always_open_low_top1"] for fold in fold_reports])),
        "macro_router_delta_vs_open_low": float(np.mean([fold["router_delta_vs_open_low"] for fold in fold_reports])),
        "macro_stateless_oracle_coverage": float(np.mean([fold["stateless_oracle_coverage"] for fold in fold_reports])),
        "events": len(grouped),
        "folds": fold_reports,
        "checkpoint_retained": False,
        "production_integration": False,
    }
