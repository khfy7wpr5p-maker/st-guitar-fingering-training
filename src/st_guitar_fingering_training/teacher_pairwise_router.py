from __future__ import annotations

from dataclasses import dataclass
from math import log1p
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .dataset import Voicing, valid_chord_voicings
from .intake import MAX_FRET
from .synthetic_behavior import deterministic_style_folds


TEACHER_PAIRWISE_ROUTER_LABEL = "teacher_prefers_compact_over_open_low"

TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES = (
    "chord_size",
    "pitch_span",
    "mean_pitch",
    "candidate_count_log1p",
    "candidate_open_fraction",
    "candidate_mean_fret_mean",
    "candidate_span_mean",
    "open_top_open_ratio",
    "open_top_mean_fret",
    "open_top_max_fret",
    "open_top_fret_span",
    "compact_top_open_ratio",
    "compact_top_mean_fret",
    "compact_top_max_fret",
    "compact_top_fret_span",
)


@dataclass(frozen=True)
class TeacherPairwiseRouterRow:
    family_id: str
    event_id: str
    teacher_prefers_compact: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class TeacherPairwiseRouterMetrics:
    events: int
    accuracy: float
    always_open_low_accuracy: float
    balanced_accuracy: float
    open_low_recall: float
    compact_recall: float
    predicted_compact: int
    family_accuracy: dict[str, float]
    family_always_open_low_accuracy: dict[str, float]


def _voicing_stats(voicing: Voicing) -> tuple[float, float, float, float]:
    if not voicing:
        raise ValueError("voicing must not be empty")
    frets = [fret for _, _, fret in voicing]
    return (
        sum(fret == 0 for fret in frets) / len(frets),
        sum(frets) / len(frets),
        max(frets),
        max(frets) - min(frets),
    )


def teacher_pairwise_router_feature_vector(
    pitches: tuple[int, ...],
    tuning: tuple[int, ...],
    open_low_top1: Voicing,
    compact_top1: Voicing,
) -> tuple[float, ...]:
    """Build the fixed Stage 7G-E1 target-blind pairwise router features.

    The teacher response, family identity, source identity, and observed source TAB
    are intentionally absent. The feature vector uses only current chord pitches,
    deterministic physical candidates, and the geometry of the two already-frozen
    specialist proposals.
    """

    pitches = tuple(sorted(int(value) for value in pitches))
    tuning = tuple(int(value) for value in tuning)
    if len(tuning) != 6:
        raise ValueError("Stage 7G-E1 supports six-string guitar tuning only")
    if len(pitches) < 2:
        raise ValueError("Stage 7G-E1 requires a chord with at least two pitches")
    if open_low_top1 == compact_top1:
        raise ValueError("Stage 7G-E1 requires an open_low-vs-compact disagreement")

    candidates = valid_chord_voicings(pitches, tuning)
    if len(candidates) < 2:
        raise ValueError("Stage 7G-E1 requires an ambiguous deterministic candidate set")
    if open_low_top1 not in candidates or compact_top1 not in candidates:
        raise ValueError("both specialist proposals must belong to the deterministic candidate set")

    candidate_stats = [_voicing_stats(candidate) for candidate in candidates]
    open_stats = _voicing_stats(open_low_top1)
    compact_stats = _voicing_stats(compact_top1)

    values = (
        len(pitches) / 6.0,
        (max(pitches) - min(pitches)) / 48.0,
        (sum(pitches) / len(pitches)) / 127.0,
        log1p(len(candidates)),
        sum(stats[0] > 0.0 for stats in candidate_stats) / len(candidate_stats),
        float(np.mean([stats[1] for stats in candidate_stats])) / MAX_FRET,
        float(np.mean([stats[3] for stats in candidate_stats])) / MAX_FRET,
        open_stats[0],
        open_stats[1] / MAX_FRET,
        open_stats[2] / MAX_FRET,
        open_stats[3] / MAX_FRET,
        compact_stats[0],
        compact_stats[1] / MAX_FRET,
        compact_stats[2] / MAX_FRET,
        compact_stats[3] / MAX_FRET,
    )
    array = np.asarray(values, dtype=np.float64)
    if len(values) != len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES) or not np.isfinite(array).all():
        raise AssertionError("invalid Stage 7G-E1 pairwise router feature vector")
    return tuple(float(value) for value in values)


def _validate_rows(rows: tuple[TeacherPairwiseRouterRow, ...]) -> None:
    if not rows:
        raise ValueError("no Teacher-GOLD pairwise router rows")
    event_ids: set[str] = set()
    for row in rows:
        if not row.family_id or not row.event_id:
            raise ValueError("family_id and event_id are required")
        if row.event_id in event_ids:
            raise ValueError("duplicate Teacher-GOLD pairwise event_id")
        event_ids.add(row.event_id)
        if row.teacher_prefers_compact not in (0, 1):
            raise ValueError("Teacher-GOLD pairwise target must be binary and decisive")
        if len(row.features) != len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES):
            raise ValueError("Teacher-GOLD pairwise feature dimension mismatch")
        if not np.isfinite(np.asarray(row.features, dtype=np.float64)).all():
            raise ValueError("Teacher-GOLD pairwise features must be finite")


def train_teacher_pairwise_router(rows: Iterable[TeacherPairwiseRouterRow]):
    rows = tuple(rows)
    _validate_rows(rows)
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in rows], dtype=np.int64)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("training fold must contain both teacher preference classes")
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            C=1.0,
            solver="lbfgs",
            random_state=0,
        ),
    )
    model.fit(X, y)
    return model


def evaluate_teacher_pairwise_router(
    model,
    rows: Iterable[TeacherPairwiseRouterRow],
) -> TeacherPairwiseRouterMetrics:
    rows = tuple(rows)
    _validate_rows(rows)
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in rows], dtype=np.int64)
    probabilities = np.asarray(model.predict_proba(X), dtype=np.float64)
    classes = list(model.classes_)
    if 1 not in classes or probabilities.shape != (len(rows), 2):
        raise ValueError("pairwise router must expose binary class probabilities")
    compact_column = classes.index(1)
    predicted = (probabilities[:, compact_column] >= 0.5).astype(np.int64)

    open_mask = y == 0
    compact_mask = y == 1
    if not open_mask.any() or not compact_mask.any():
        raise ValueError("validation rows must contain both teacher preference classes")

    open_recall = float(np.mean(predicted[open_mask] == 0))
    compact_recall = float(np.mean(predicted[compact_mask] == 1))

    family_accuracy: dict[str, float] = {}
    family_baseline: dict[str, float] = {}
    for family_id in sorted({row.family_id for row in rows}):
        indices = [index for index, row in enumerate(rows) if row.family_id == family_id]
        family_accuracy[family_id] = float(np.mean(predicted[indices] == y[indices]))
        family_baseline[family_id] = float(np.mean(y[indices] == 0))

    return TeacherPairwiseRouterMetrics(
        events=len(rows),
        accuracy=float(np.mean(predicted == y)),
        always_open_low_accuracy=float(np.mean(y == 0)),
        balanced_accuracy=(open_recall + compact_recall) / 2.0,
        open_low_recall=open_recall,
        compact_recall=compact_recall,
        predicted_compact=int(np.sum(predicted == 1)),
        family_accuracy=family_accuracy,
        family_always_open_low_accuracy=family_baseline,
    )


def teacher_pairwise_router_cross_validation_report(
    rows: Iterable[TeacherPairwiseRouterRow],
    folds: int = 5,
) -> dict:
    """Run the preregistered family-isolated Stage 7G-E1 diagnostic CV.

    No validation family contributes rows to a fitted fold model. The report is a
    research diagnostic only; it never retains a checkpoint or authorizes production.
    """

    rows = tuple(rows)
    _validate_rows(rows)
    family_ids = tuple(sorted({row.family_id for row in rows}))
    fold_family_ids = deterministic_style_folds(family_ids, folds=folds)

    fold_reports: list[dict] = []
    all_family_accuracy: dict[str, float] = {}
    all_family_baseline: dict[str, float] = {}
    total_correct = 0.0
    total_baseline_correct = 0.0
    total_events = 0

    for fold_index, validation_tuple in enumerate(fold_family_ids):
        validation_ids = set(validation_tuple)
        train_ids = set(family_ids) - validation_ids
        if not train_ids or train_ids & validation_ids:
            raise AssertionError("family leakage in Teacher-GOLD pairwise router CV")

        train_rows = tuple(row for row in rows if row.family_id in train_ids)
        validation_rows = tuple(row for row in rows if row.family_id in validation_ids)
        if {row.family_id for row in train_rows} & {row.family_id for row in validation_rows}:
            raise AssertionError("Teacher-GOLD train/validation families overlap")

        model = train_teacher_pairwise_router(train_rows)
        metrics = evaluate_teacher_pairwise_router(model, validation_rows)
        all_family_accuracy.update(metrics.family_accuracy)
        all_family_baseline.update(metrics.family_always_open_low_accuracy)
        total_correct += metrics.accuracy * metrics.events
        total_baseline_correct += metrics.always_open_low_accuracy * metrics.events
        total_events += metrics.events

        fold_reports.append({
            "fold": fold_index + 1,
            "train_families": sorted(train_ids),
            "validation_families": sorted(validation_ids),
            "train_family_count": len(train_ids),
            "validation_family_count": len(validation_ids),
            "validation_events": metrics.events,
            "accuracy": metrics.accuracy,
            "always_open_low_accuracy": metrics.always_open_low_accuracy,
            "accuracy_delta_vs_always_open_low": metrics.accuracy - metrics.always_open_low_accuracy,
            "balanced_accuracy": metrics.balanced_accuracy,
            "open_low_recall": metrics.open_low_recall,
            "compact_recall": metrics.compact_recall,
            "predicted_compact": metrics.predicted_compact,
        })

    if set(all_family_accuracy) != set(family_ids) or set(all_family_baseline) != set(family_ids):
        raise AssertionError("family-isolated CV did not evaluate every family exactly once")

    macro_family_accuracy = float(np.mean(list(all_family_accuracy.values())))
    macro_family_baseline = float(np.mean(list(all_family_baseline.values())))
    event_weighted_accuracy = total_correct / total_events
    event_weighted_baseline = total_baseline_correct / total_events

    return {
        "stage": "7G-E1",
        "status": "DIAGNOSTIC_PROTOCOL",
        "router_kind": "teacher_gold_target_blind_open_low_vs_compact_router",
        "label_semantics": TEACHER_PAIRWISE_ROUTER_LABEL,
        "feature_names": list(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES),
        "feature_count": len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES),
        "family_count": len(family_ids),
        "event_count": len(rows),
        "fold_count": folds,
        "family_isolated": True,
        "target_in_features": False,
        "hyperparameter_search": False,
        "macro_family_accuracy": macro_family_accuracy,
        "macro_family_always_open_low_accuracy": macro_family_baseline,
        "macro_family_accuracy_delta_vs_always_open_low": macro_family_accuracy - macro_family_baseline,
        "event_weighted_accuracy": event_weighted_accuracy,
        "event_weighted_always_open_low_accuracy": event_weighted_baseline,
        "event_weighted_accuracy_delta_vs_always_open_low": event_weighted_accuracy - event_weighted_baseline,
        "macro_fold_balanced_accuracy": float(np.mean([fold["balanced_accuracy"] for fold in fold_reports])),
        "macro_fold_open_low_recall": float(np.mean([fold["open_low_recall"] for fold in fold_reports])),
        "macro_fold_compact_recall": float(np.mean([fold["compact_recall"] for fold in fold_reports])),
        "folds": fold_reports,
        "checkpoint_retained": False,
        "production_integration": False,
    }
