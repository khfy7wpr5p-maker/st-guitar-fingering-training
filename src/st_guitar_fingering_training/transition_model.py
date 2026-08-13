from __future__ import annotations

from typing import Iterable

import numpy as np

from .context import _event_id, _observed_voicing, transition_feature_vector
from .dataset import Voicing, VoicingCandidateRow, valid_chord_voicings
from .intake import GuitarEvent, ParsedSource
from .sequence_context import _next_chord_events, sequence_rows_for_event
from .training import RankingMetrics

DEFAULT_TRANSITION_WEIGHT = 0.25


def transition_rows_for_event(
    source: ParsedSource,
    event: GuitarEvent,
    index: int,
    previous: Voicing,
) -> tuple[VoicingCandidateRow, ...]:
    if not event.is_chord:
        raise ValueError("transition rows require a chord/polyphonic event")
    observed = _observed_voicing(event)
    pitches = tuple(sorted(p.sounding_midi for p in event.placements))
    candidates = valid_chord_voicings(pitches, event.tuning)
    if not candidates or observed not in candidates:
        raise ValueError("invalid transition voicing candidate set")
    event_id = _event_id(source, event, index) + ":transition"
    return tuple(
        VoicingCandidateRow(
            family_id=source.family_id,
            event_id=event_id,
            pitches_midi=pitches,
            placements=candidate,
            observed=int(candidate == observed),
            features=transition_feature_vector(candidate, previous),
        )
        for candidate in candidates
    )


def build_transition_training_rows(sources: Iterable[ParsedSource]) -> tuple[VoicingCandidateRow, ...]:
    """Teacher-forced training rows for adjacent observed chord transitions.

    The first chord of each source has no incoming transition and is skipped.
    Training may use the previous observed voicing because it belongs to the training
    partition. Validation rollout never uses the previous observed voicing.
    """
    rows: list[VoicingCandidateRow] = []
    for source in sources:
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            observed = _observed_voicing(event)
            if previous is not None:
                rows.extend(transition_rows_for_event(source, event, index, previous))
            previous = observed
    return tuple(rows)


def _group_log_probabilities(model, rows) -> np.ndarray:
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    if X.ndim != 2 or X.shape[0] == 0 or not np.isfinite(X).all():
        raise ValueError("invalid transition score matrix")
    logits = np.asarray(model.decision_function(X), dtype=np.float64)
    if logits.ndim != 1 or logits.shape[0] != X.shape[0] or not np.isfinite(logits).all():
        raise ValueError("invalid transition logits")
    shifted = logits - np.max(logits)
    log_z = np.log(np.exp(shifted).sum())
    return shifted - log_z


def _rank_combined_rows(sequence_model, transition_model, sequence_rows, transition_rows, weight: float):
    if not np.isfinite(weight) or weight < 0.0 or weight > 1.0:
        raise ValueError("transition weight must be finite and within [0, 1]")
    if tuple(row.placements for row in sequence_rows) != tuple(row.placements for row in transition_rows):
        raise AssertionError("sequence/transition candidate ordering mismatch")
    unary = _group_log_probabilities(sequence_model, sequence_rows)
    transition = _group_log_probabilities(transition_model, transition_rows)
    scores = unary + weight * transition
    ranked = sorted(
        zip(sequence_rows, scores),
        key=lambda item: (-item[1], tuple(item[0].placements)),
    )
    return [row for row, _ in ranked]


def evaluate_transition_ranker_teacher_forced(model, sources: Iterable[ParsedSource]) -> RankingMetrics:
    reciprocal: list[float] = []
    correct = 0
    for source in sources:
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            observed = _observed_voicing(event)
            if previous is None:
                previous = observed
                continue
            rows = transition_rows_for_event(source, event, index, previous)
            if len(rows) == 1:
                previous = observed
                continue
            scores = _group_log_probabilities(model, rows)
            ranked = [row for row, _ in sorted(zip(rows, scores), key=lambda item: (-item[1], tuple(item[0].placements)))]
            ranks = [position + 1 for position, row in enumerate(ranked) if row.observed == 1]
            if len(ranks) != 1:
                raise ValueError("each transition event must have exactly one observed candidate")
            rank = ranks[0]
            correct += int(rank == 1)
            reciprocal.append(1.0 / rank)
            previous = observed
    if not reciprocal:
        raise ValueError("no ambiguous transition evaluation events")
    return RankingMetrics(len(reciprocal), correct / len(reciprocal), float(np.mean(reciprocal)))


def evaluate_combined_transition_rollout(
    sequence_model,
    transition_model,
    sources: Iterable[ParsedSource],
    transition_weight: float = DEFAULT_TRANSITION_WEIGHT,
) -> RankingMetrics:
    """Deployment-like greedy rollout with separate unary and transition models.

    Previous context is always the model-selected voicing. No observed validation
    string/fret placement is fed back into either model. Future context remains the
    Stage 6E pitch-only lookahead contract.
    """
    reciprocal: list[float] = []
    correct = 0
    for source in sources:
        next_by_index = _next_chord_events(source)
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            sequence_rows = sequence_rows_for_event(source, event, index, previous, next_by_index[index])
            if len(sequence_rows) == 1:
                previous = sequence_rows[0].placements
                continue
            if previous is None:
                unary = _group_log_probabilities(sequence_model, sequence_rows)
                ranked = [row for row, _ in sorted(zip(sequence_rows, unary), key=lambda item: (-item[1], tuple(item[0].placements)))]
            else:
                transition_rows = transition_rows_for_event(source, event, index, previous)
                ranked = _rank_combined_rows(
                    sequence_model,
                    transition_model,
                    sequence_rows,
                    transition_rows,
                    transition_weight,
                )
            ranks = [position + 1 for position, row in enumerate(ranked) if row.observed == 1]
            if len(ranks) != 1:
                raise ValueError("each combined event must have exactly one observed candidate")
            rank = ranks[0]
            correct += int(rank == 1)
            reciprocal.append(1.0 / rank)
            previous = ranked[0].placements
    if not reciprocal:
        raise ValueError("no ambiguous combined transition evaluation events")
    return RankingMetrics(len(reciprocal), correct / len(reciprocal), float(np.mean(reciprocal)))
