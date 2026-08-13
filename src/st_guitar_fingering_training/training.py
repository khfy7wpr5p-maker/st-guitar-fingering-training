from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class RankingMetrics:
    events: int
    top1_accuracy: float
    mean_reciprocal_rank: float


def _matrix(rows):
    X = np.asarray([r.features for r in rows], dtype=np.float64)
    y = np.asarray([r.observed for r in rows], dtype=np.int64)
    if X.ndim != 2 or X.shape[0] == 0:
        raise ValueError("training/evaluation rows must form a non-empty 2D feature matrix")
    if not np.isfinite(X).all():
        raise ValueError("non-finite training features")
    return X, y


def filter_ambiguous_ranking_rows(rows):
    """Keep only event groups with at least two physical candidates.

    Single-candidate chord events are valid musical events but not ranking problems.
    Including them in ranking evaluation would make every method trivially correct
    and inflate Top-1/MRR. The returned rows preserve original event grouping.
    """
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)
    kept = []
    for event_rows in grouped.values():
        if len(event_rows) > 1:
            kept.extend(event_rows)
    return tuple(kept)


def train_logistic_ranker(train_rows):
    X, y = _matrix(train_rows)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("training rows need positive and negative candidates")
    model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0)
    model.fit(X, y)
    return model


def _candidate_tie_key(row):
    placements = getattr(row, "placements", None)
    if placements is not None:
        return tuple(placements)
    return (getattr(row, "string", 0), getattr(row, "fret", 0))


def _metrics_from_ranked_groups(grouped, ranker) -> RankingMetrics:
    reciprocal = []
    correct = 0
    for event_rows in grouped.values():
        ranked = ranker(event_rows)
        observed_ranks = [i + 1 for i, row in enumerate(ranked) if row.observed == 1]
        if len(observed_ranks) != 1:
            raise ValueError("each event must have exactly one observed candidate")
        rank = observed_ranks[0]
        correct += int(rank == 1)
        reciprocal.append(1.0 / rank)
    if not reciprocal:
        raise ValueError("no evaluation events")
    return RankingMetrics(
        events=len(reciprocal),
        top1_accuracy=correct / len(reciprocal),
        mean_reciprocal_rank=float(np.mean(reciprocal)),
    )


def evaluate_ranker(model, rows) -> RankingMetrics:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.event_id].append(row)

    def ranker(event_rows):
        X, _ = _matrix(tuple(event_rows))
        scores = model.predict_proba(X)[:, 1]
        ranked_pairs = sorted(
            zip(event_rows, scores),
            key=lambda x: (-x[1], _candidate_tie_key(x[0])),
        )
        return [row for row, _ in ranked_pairs]

    return _metrics_from_ranked_groups(grouped, ranker)


def evaluate_low_total_fret_voicing_baseline(rows) -> RankingMetrics:
    """Evaluate a deterministic chord baseline on the same ranking groups.

    The baseline prefers, in order: lower total fret cost, lower maximum fret,
    smaller fret span, more open strings, then a deterministic placement order.
    This is only a comparison baseline; it is not a pedagogical fingering rule.
    """
    grouped = defaultdict(list)
    for row in rows:
        placements = getattr(row, "placements", None)
        if placements is None:
            raise ValueError("voicing baseline requires rows with placements")
        grouped[row.event_id].append(row)

    def ranker(event_rows):
        def key(row):
            frets = [fret for _, _, fret in row.placements]
            return (
                sum(frets),
                max(frets),
                max(frets) - min(frets),
                -sum(fret == 0 for fret in frets),
                tuple(row.placements),
            )

        return sorted(event_rows, key=key)

    return _metrics_from_ranked_groups(grouped, ranker)
