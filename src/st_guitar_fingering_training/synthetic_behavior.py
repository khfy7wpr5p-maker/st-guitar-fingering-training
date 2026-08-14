from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource
from .synthetic import MAX_SYNTH_FRET

STYLES = ("open_low", "compact", "mid_position", "high_position", "common_tone")

FEATURE_NAMES = {
    "open_low": ("open_ratio", "mean_fret", "max_fret", "fret_span"),
    "compact": ("fret_span", "mean_fret", "max_fret", "open_ratio"),
    "mid_position": ("distance_to_fret5", "fret_span", "open_ratio", "mean_fret"),
    "high_position": ("distance_to_fret9", "fret_span", "open_ratio", "mean_fret"),
    "common_tone": (
        "shared_pitch_same_string_ratio",
        "position_center_move",
        "string_overlap_ratio",
        "fret_span",
        "mean_fret",
    ),
}

# Stage 7B's coefficient gate is intentionally limited to the five explicit
# behavior hypotheses. Auxiliary coefficients remain reported for inspection,
# but correlated features are not assigned unsupported sign expectations.
EXPECTED_SIGNS = {
    "open_low": {"open_ratio": 1},
    "compact": {"fret_span": -1},
    "mid_position": {"distance_to_fret5": -1},
    "high_position": {"distance_to_fret9": -1},
    "common_tone": {"shared_pitch_same_string_ratio": 1},
}

FOCUS_FEATURE = {
    "open_low": "open_ratio",
    "compact": "fret_span",
    "mid_position": "distance_to_fret5",
    "high_position": "distance_to_fret9",
    "common_tone": "shared_pitch_same_string_ratio",
}


@dataclass(frozen=True)
class BehaviorRow:
    family_id: str
    event_id: str
    observed: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class BehaviorMetrics:
    events: int
    top1_accuracy: float
    mean_reciprocal_rank: float
    uniform_top1_baseline: float


def _voicing_stats(voicing: Voicing) -> tuple[float, float, float, float]:
    frets = [fret for _, _, fret in voicing]
    mean_fret = sum(frets) / len(frets)
    max_fret = max(frets)
    span = max(frets) - min(frets)
    open_ratio = sum(fret == 0 for fret in frets) / len(frets)
    return open_ratio, mean_fret, max_fret, span


def _feature_vector(style: str, voicing: Voicing, previous: Voicing | None) -> tuple[float, ...]:
    if style not in STYLES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")
    open_ratio, mean_fret, max_fret, span = _voicing_stats(voicing)

    if style == "open_low":
        return (open_ratio, mean_fret / MAX_SYNTH_FRET, max_fret / MAX_SYNTH_FRET, span / MAX_SYNTH_FRET)
    if style == "compact":
        return (span / MAX_SYNTH_FRET, mean_fret / MAX_SYNTH_FRET, max_fret / MAX_SYNTH_FRET, open_ratio)
    if style == "mid_position":
        return (abs(mean_fret - 5.0) / MAX_SYNTH_FRET, span / MAX_SYNTH_FRET, open_ratio, mean_fret / MAX_SYNTH_FRET)
    if style == "high_position":
        return (abs(mean_fret - 9.0) / MAX_SYNTH_FRET, span / MAX_SYNTH_FRET, open_ratio, mean_fret / MAX_SYNTH_FRET)

    if previous is None:
        raise ValueError("common_tone features require previous voicing")
    previous_pairs = {(pitch, string) for pitch, string, _ in previous}
    current_pairs = {(pitch, string) for pitch, string, _ in voicing}
    previous_strings = {string for _, string, _ in previous}
    current_strings = {string for _, string, _ in voicing}
    previous_center = sum(fret for _, _, fret in previous) / len(previous)
    shared_ratio = len(previous_pairs & current_pairs) / len(voicing)
    overlap_ratio = len(previous_strings & current_strings) / len(voicing)
    center_move = abs(mean_fret - previous_center) / MAX_SYNTH_FRET
    return (shared_ratio, center_move, overlap_ratio, span / MAX_SYNTH_FRET, mean_fret / MAX_SYNTH_FRET)


def deterministic_style_folds(family_ids: Iterable[str], folds: int = 5) -> tuple[tuple[str, ...], ...]:
    ids = sorted(set(family_ids), key=lambda value: sha256(value.encode()).hexdigest())
    if folds < 2 or len(ids) < folds:
        raise ValueError("invalid fold count for synthetic behavior families")
    result = tuple(tuple(ids[index::folds]) for index in range(folds))
    flattened = [item for fold in result for item in fold]
    if sorted(flattened) != sorted(ids) or len(flattened) != len(set(flattened)):
        raise AssertionError("synthetic behavior folds must be exhaustive and disjoint")
    return result


def build_behavior_rows(sources: Iterable[ParsedSource], style: str) -> tuple[BehaviorRow, ...]:
    if style not in STYLES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")
    rows: list[BehaviorRow] = []
    for source in sources:
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            observed: Voicing = tuple(sorted((p.sounding_midi, p.string, p.fret) for p in event.placements))
            pitches = tuple(sorted(p.sounding_midi for p in event.placements))
            candidates = tuple(
                candidate
                for candidate in valid_chord_voicings(pitches, event.tuning)
                if max(fret for _, _, fret in candidate) <= MAX_SYNTH_FRET
            )
            if observed not in candidates:
                raise ValueError("synthetic preferred voicing missing from bounded candidate set")

            # The first common-tone event has no previous voicing and is generated with
            # a compact fallback. Skip it so this specialist measures continuity only.
            if style == "common_tone" and previous is None:
                previous = observed
                continue

            event_id = f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"
            for candidate in candidates:
                rows.append(BehaviorRow(
                    family_id=source.family_id,
                    event_id=event_id,
                    observed=int(candidate == observed),
                    features=_feature_vector(style, candidate, previous),
                ))
            if style == "common_tone":
                previous = observed
    return tuple(rows)


def train_behavior_ranker(rows: tuple[BehaviorRow, ...]):
    if not rows:
        raise ValueError("no synthetic behavior training rows")
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.observed for row in rows], dtype=np.int64)
    if not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("invalid synthetic behavior training matrix")
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
    )
    model.fit(X, y)
    return model


def evaluate_behavior_ranker(model, rows: tuple[BehaviorRow, ...]) -> BehaviorMetrics:
    grouped: dict[str, list[BehaviorRow]] = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)
    if not grouped:
        raise ValueError("no synthetic behavior evaluation events")

    correct = 0
    reciprocal: list[float] = []
    random_top1: list[float] = []
    for event_rows in grouped.values():
        X = np.asarray([row.features for row in event_rows], dtype=np.float64)
        scores = model.predict_proba(X)[:, 1]
        ranked = sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))
        observed_indices = [index for index, row in enumerate(event_rows) if row.observed == 1]
        if len(observed_indices) != 1:
            raise ValueError("each synthetic behavior event must have one preferred candidate")
        observed_index = observed_indices[0]
        rank = next(position + 1 for position, (index, _) in enumerate(ranked) if index == observed_index)
        correct += int(rank == 1)
        reciprocal.append(1.0 / rank)
        random_top1.append(1.0 / len(event_rows))

    return BehaviorMetrics(
        events=len(grouped),
        top1_accuracy=correct / len(grouped),
        mean_reciprocal_rank=float(np.mean(reciprocal)),
        uniform_top1_baseline=float(np.mean(random_top1)),
    )


def coefficient_report(model, style: str) -> dict:
    names = FEATURE_NAMES[style]
    logistic = model.named_steps["logisticregression"]
    coefficients = logistic.coef_[0]
    if len(coefficients) != len(names):
        raise AssertionError("feature/coefficient length mismatch")
    values = {name: float(value) for name, value in zip(names, coefficients)}
    expected = EXPECTED_SIGNS[style]
    matches = {
        name: bool(np.sign(values[name]) == sign)
        for name, sign in expected.items()
    }
    focus = FOCUS_FEATURE[style]
    return {
        "feature_space": "standardized",
        "coefficients": values,
        "expected_direction_match": matches,
        "expected_direction_matches": sum(matches.values()),
        "expected_direction_total": len(matches),
        "focus_feature": focus,
        "focus_expected_sign": expected[focus],
        "focus_direction_match": matches[focus],
    }


def behavior_cross_validation_report(
    sources: Iterable[ParsedSource],
    style: str,
    folds: int = 5,
) -> dict:
    """Evaluate one synthetic behavior specialist with family-isolated folds.

    The five behavior styles are intentionally evaluated independently. For
    common_tone, previous-voicing context is the observed previous voicing
    inside the same synthetic family; the report marks that context explicitly
    as teacher-forced diagnostic context. No model/checkpoint is serialized.
    """
    if style not in STYLES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")
    sources = tuple(sources)
    family_ids = tuple(sorted({source.family_id for source in sources}))
    fold_family_ids = deterministic_style_folds(family_ids, folds=folds)
    rows = build_behavior_rows(sources, style)
    if not rows:
        raise ValueError("no synthetic behavior rows for cross-validation")

    fold_reports = []
    coefficient_values: dict[str, list[float]] = {name: [] for name in FEATURE_NAMES[style]}
    direction_matches: dict[str, int] = {name: 0 for name in EXPECTED_SIGNS[style]}

    for fold_index, validation_ids_tuple in enumerate(fold_family_ids):
        validation_ids = set(validation_ids_tuple)
        train_ids = set(family_ids) - validation_ids
        if not train_ids or train_ids & validation_ids:
            raise AssertionError("family leakage in synthetic behavior cross-validation")

        train_rows = tuple(row for row in rows if row.family_id in train_ids)
        validation_rows = tuple(row for row in rows if row.family_id in validation_ids)
        if {row.family_id for row in train_rows} & {row.family_id for row in validation_rows}:
            raise AssertionError("family leakage across synthetic behavior rows")

        model = train_behavior_ranker(train_rows)
        metrics = evaluate_behavior_ranker(model, validation_rows)
        coefficients = coefficient_report(model, style)
        for name, value in coefficients["coefficients"].items():
            coefficient_values[name].append(value)
        for name, matched in coefficients["expected_direction_match"].items():
            direction_matches[name] += int(matched)

        fold_reports.append({
            "fold": fold_index + 1,
            "train_families": sorted(train_ids),
            "validation_families": sorted(validation_ids),
            "train_family_count": len(train_ids),
            "validation_family_count": len(validation_ids),
            "validation_events": metrics.events,
            "top1": metrics.top1_accuracy,
            "mrr": metrics.mean_reciprocal_rank,
            "uniform_random_top1": metrics.uniform_top1_baseline,
            "top1_over_random": metrics.top1_accuracy - metrics.uniform_top1_baseline,
            "coefficients": coefficients,
        })

    focus = FOCUS_FEATURE[style]
    return {
        "style": style,
        "model_kind": "logistic_ranking_specialist",
        "family_count": len(family_ids),
        "fold_count": folds,
        "family_isolated": True,
        "previous_context": "teacher_forced_previous_voicing" if style == "common_tone" else "none",
        "macro_top1": float(np.mean([fold["top1"] for fold in fold_reports])),
        "macro_mrr": float(np.mean([fold["mrr"] for fold in fold_reports])),
        "macro_uniform_random_top1": float(np.mean([fold["uniform_random_top1"] for fold in fold_reports])),
        "macro_top1_over_random": float(np.mean([fold["top1_over_random"] for fold in fold_reports])),
        "mean_standardized_coefficients": {
            name: float(np.mean(values)) for name, values in coefficient_values.items()
        },
        "expected_direction_match_folds": direction_matches,
        "focus_feature": focus,
        "focus_expected_sign": EXPECTED_SIGNS[style][focus],
        "focus_direction_match_folds": direction_matches[focus],
        "folds": fold_reports,
        "checkpoint_retained": False,
    }
