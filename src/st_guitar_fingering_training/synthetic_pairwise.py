from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .synthetic_behavior import (
    EXPECTED_SIGNS,
    FEATURE_NAMES,
    FOCUS_FEATURE,
    BehaviorMetrics,
    BehaviorRow,
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
