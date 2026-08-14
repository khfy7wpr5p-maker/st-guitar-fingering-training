from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .intake import ParsedSource
from .synthetic_behavior import (
    EXPECTED_SIGNS,
    FEATURE_NAMES,
    FOCUS_FEATURE,
    STYLES,
    BehaviorMetrics,
    BehaviorRow,
    behavior_cross_validation_report,
    build_behavior_rows,
    deterministic_style_folds,
)


def _group_event_rows(rows: tuple[BehaviorRow, ...]) -> dict[str, list[BehaviorRow]]:
    grouped: dict[str, list[BehaviorRow]] = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)
    if not grouped:
        raise ValueError("no synthetic pairwise behavior events")
    for event_rows in grouped.values():
        preferred = [row for row in event_rows if row.observed == 1]
        if len(preferred) != 1 or len(event_rows) < 2:
            raise ValueError("each pairwise event must contain one preferred candidate and at least one alternative")
        feature_lengths = {len(row.features) for row in event_rows}
        if len(feature_lengths) != 1:
            raise ValueError("inconsistent pairwise feature dimensions")
    return grouped


def build_pairwise_training_matrix(rows: tuple[BehaviorRow, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Build symmetric preferred-vs-alternative feature differences.

    For every event and every non-preferred candidate, emit both
    preferred-minus-alternative (label 1) and its exact inverse (label 0).
    This keeps the training objective aligned with within-event ranking rather
    than independent candidate classification.
    """
    grouped = _group_event_rows(rows)
    differences: list[tuple[float, ...]] = []
    labels: list[int] = []

    for event_rows in grouped.values():
        preferred = next(row for row in event_rows if row.observed == 1)
        preferred_features = np.asarray(preferred.features, dtype=np.float64)
        for alternative in event_rows:
            if alternative.observed == 1:
                continue
            alternative_features = np.asarray(alternative.features, dtype=np.float64)
            difference = preferred_features - alternative_features
            differences.append(tuple(float(value) for value in difference))
            labels.append(1)
            differences.append(tuple(float(-value) for value in difference))
            labels.append(0)

    X = np.asarray(differences, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)
    if X.ndim != 2 or not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("invalid synthetic pairwise training matrix")
    return X, y


def train_pairwise_behavior_ranker(rows: tuple[BehaviorRow, ...]):
    X, y = build_pairwise_training_matrix(rows)
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, fit_intercept=False, random_state=0),
    )
    model.fit(X, y)
    return model


def evaluate_pairwise_behavior_ranker(model, rows: tuple[BehaviorRow, ...]) -> BehaviorMetrics:
    grouped = _group_event_rows(rows)
    correct = 0
    reciprocal: list[float] = []
    random_top1: list[float] = []

    for event_rows in grouped.values():
        X = np.asarray([row.features for row in event_rows], dtype=np.float64)
        if not np.isfinite(X).all():
            raise ValueError("invalid synthetic pairwise evaluation matrix")
        scores = np.asarray(model.decision_function(X), dtype=np.float64)
        ranked = sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))
        observed_index = next(index for index, row in enumerate(event_rows) if row.observed == 1)
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


def pairwise_coefficient_report(model, style: str) -> dict:
    if style not in FEATURE_NAMES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")
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
        "feature_space": "standardized_pairwise_differences",
        "coefficients": values,
        "expected_direction_match": matches,
        "expected_direction_matches": sum(matches.values()),
        "expected_direction_total": len(matches),
        "focus_feature": focus,
        "focus_expected_sign": expected[focus],
        "focus_direction_match": matches[focus],
    }


def pairwise_behavior_cross_validation_report(
    sources: Iterable[ParsedSource],
    style: str,
    folds: int = 5,
) -> dict:
    """Evaluate one pairwise specialist with deterministic family-isolated folds."""
    if style not in STYLES:
        raise ValueError(f"unsupported synthetic behavior style: {style}")
    sources = tuple(sources)
    family_ids = tuple(sorted({source.family_id for source in sources}))
    fold_family_ids = deterministic_style_folds(family_ids, folds=folds)
    rows = build_behavior_rows(sources, style)
    if not rows:
        raise ValueError("no synthetic pairwise behavior rows for cross-validation")

    fold_reports = []
    coefficient_values: dict[str, list[float]] = {name: [] for name in FEATURE_NAMES[style]}
    direction_matches: dict[str, int] = {name: 0 for name in EXPECTED_SIGNS[style]}

    for fold_index, validation_ids_tuple in enumerate(fold_family_ids):
        validation_ids = set(validation_ids_tuple)
        train_ids = set(family_ids) - validation_ids
        if not train_ids or train_ids & validation_ids:
            raise AssertionError("family leakage in pairwise synthetic behavior cross-validation")

        train_rows = tuple(row for row in rows if row.family_id in train_ids)
        validation_rows = tuple(row for row in rows if row.family_id in validation_ids)
        if {row.family_id for row in train_rows} & {row.family_id for row in validation_rows}:
            raise AssertionError("family leakage across pairwise synthetic behavior rows")

        model = train_pairwise_behavior_ranker(train_rows)
        metrics = evaluate_pairwise_behavior_ranker(model, validation_rows)
        coefficients = pairwise_coefficient_report(model, style)
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
        "model_kind": "pairwise_logistic_ranking_specialist",
        "family_count": len(family_ids),
        "fold_count": folds,
        "family_isolated": True,
        "previous_context": "teacher_forced_previous_voicing" if style == "common_tone" else "none",
        "macro_top1": float(np.mean([fold["top1"] for fold in fold_reports])),
        "macro_mrr": float(np.mean([fold["mrr"] for fold in fold_reports])),
        "macro_uniform_random_top1": float(np.mean([fold["uniform_random_top1"] for fold in fold_reports])),
        "macro_top1_over_random": float(np.mean([fold["top1_over_random"] for fold in fold_reports])),
        "mean_standardized_pairwise_coefficients": {
            name: float(np.mean(values)) for name, values in coefficient_values.items()
        },
        "expected_direction_match_folds": direction_matches,
        "focus_feature": focus,
        "focus_expected_sign": EXPECTED_SIGNS[style][focus],
        "focus_direction_match_folds": direction_matches[focus],
        "folds": fold_reports,
        "checkpoint_retained": False,
    }


def compare_behavior_rankers(
    sources: Iterable[ParsedSource],
    style: str,
    folds: int = 5,
) -> dict:
    """Compare candidate-level and pairwise specialists on the same source families."""
    sources = tuple(sources)
    baseline = behavior_cross_validation_report(sources, style, folds=folds)
    pairwise = pairwise_behavior_cross_validation_report(sources, style, folds=folds)
    if baseline["family_count"] != pairwise["family_count"]:
        raise AssertionError("baseline/pairwise family count mismatch")
    if baseline["fold_count"] != pairwise["fold_count"]:
        raise AssertionError("baseline/pairwise fold count mismatch")
    if not np.isclose(baseline["macro_uniform_random_top1"], pairwise["macro_uniform_random_top1"]):
        raise AssertionError("baseline/pairwise random baseline mismatch")

    return {
        "style": style,
        "family_count": pairwise["family_count"],
        "fold_count": pairwise["fold_count"],
        "family_isolated": baseline["family_isolated"] and pairwise["family_isolated"],
        "baseline": baseline,
        "pairwise": pairwise,
        "top1_delta": pairwise["macro_top1"] - baseline["macro_top1"],
        "mrr_delta": pairwise["macro_mrr"] - baseline["macro_mrr"],
        "pairwise_top1_win": pairwise["macro_top1"] > baseline["macro_top1"],
        "pairwise_focus_direction_all_folds": pairwise["focus_direction_match_folds"] == folds,
        "checkpoint_retained": False,
    }
