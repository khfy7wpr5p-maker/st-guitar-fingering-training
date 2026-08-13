from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from .dataset import CandidateRow


@dataclass(frozen=True)
class RankingMetrics:
    events: int
    top1_accuracy: float
    mean_reciprocal_rank: float


def _matrix(rows: tuple[CandidateRow, ...]):
    X = np.asarray([r.features for r in rows], dtype=np.float64)
    y = np.asarray([r.observed for r in rows], dtype=np.int64)
    if not np.isfinite(X).all():
        raise ValueError("non-finite training features")
    return X, y


def train_logistic_ranker(train_rows: tuple[CandidateRow, ...]):
    X, y = _matrix(train_rows)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("training rows need positive and negative candidates")
    model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0)
    model.fit(X, y)
    return model


def evaluate_ranker(model, rows: tuple[CandidateRow, ...]) -> RankingMetrics:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)
    reciprocal = []
    correct = 0
    for event_rows in grouped.values():
        X, _ = _matrix(tuple(event_rows))
        scores = model.predict_proba(X)[:, 1]
        ranked = sorted(zip(event_rows, scores), key=lambda x: (-x[1], x[0].string, x[0].fret))
        observed_ranks = [i + 1 for i, (row, _) in enumerate(ranked) if row.observed == 1]
        if len(observed_ranks) != 1:
            raise ValueError("each event must have exactly one observed placement")
        rank = observed_ranks[0]
        correct += int(rank == 1)
        reciprocal.append(1.0 / rank)
    if not reciprocal:
        raise ValueError("no evaluation events")
    return RankingMetrics(events=len(reciprocal), top1_accuracy=correct / len(reciprocal), mean_reciprocal_rank=float(np.mean(reciprocal)))
