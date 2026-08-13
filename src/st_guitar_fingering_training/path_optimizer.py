from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .context import _observed_voicing
from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource
from .sequence_context import _next_chord_events, sequence_rows_for_event

MAX_PATH_STATES_PER_EVENT = 256
MAX_PATH_TRANSITIONS_PER_SOURCE = 5_000_000


@dataclass(frozen=True)
class PathRankingMetrics:
    events: int
    top1_accuracy: float
    sources: int
    exact_source_rate: float


def _positive_log_scores(model, rows) -> np.ndarray:
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    if X.ndim != 2 or X.shape[0] == 0 or not np.isfinite(X).all():
        raise ValueError("invalid path-decoder feature matrix")
    probabilities = model.predict_proba(X)[:, 1]
    probabilities = np.clip(probabilities, 1e-12, 1.0)
    return np.log(probabilities)


def _viterbi_indices(initial_scores: Sequence[float], transition_scores: Sequence[np.ndarray]) -> tuple[int, ...]:
    previous = np.asarray(initial_scores, dtype=np.float64)
    if previous.ndim != 1 or previous.size == 0 or not np.isfinite(previous).all():
        raise ValueError("initial path scores must be a finite non-empty vector")
    backpointers: list[np.ndarray] = []
    for matrix in transition_scores:
        matrix = np.asarray(matrix, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[0] != previous.size or matrix.shape[1] == 0:
            raise ValueError("transition matrix shape does not match path states")
        if not np.isfinite(matrix).all():
            raise ValueError("non-finite transition path score")
        current = np.empty(matrix.shape[1], dtype=np.float64)
        pointer = np.empty(matrix.shape[1], dtype=np.int64)
        for current_index in range(matrix.shape[1]):
            totals = previous + matrix[:, current_index]
            best_previous = int(np.argmax(totals))
            current[current_index] = totals[best_previous]
            pointer[current_index] = best_previous
        backpointers.append(pointer)
        previous = current
    last = int(np.argmax(previous))
    path = [last]
    for pointer in reversed(backpointers):
        last = int(pointer[last])
        path.append(last)
    path.reverse()
    return tuple(path)


def decode_source_sequence_path(model, source: ParsedSource) -> tuple[Voicing, ...]:
    chord_items = [(index, event) for index, event in enumerate(source.events) if event.is_chord]
    if not chord_items:
        return ()
    next_by_index = _next_chord_events(source)
    candidates_by_event: list[tuple[Voicing, ...]] = []
    for _, event in chord_items:
        pitches = tuple(sorted(p.sounding_midi for p in event.placements))
        candidates = valid_chord_voicings(pitches, event.tuning)
        if not candidates:
            raise ValueError("path event has no physically valid voicing candidates")
        if len(candidates) > MAX_PATH_STATES_PER_EVENT:
            raise ValueError("path event exceeds bounded candidate-state limit")
        candidates_by_event.append(candidates)
    initial_index, initial_event = chord_items[0]
    initial_rows = sequence_rows_for_event(source, initial_event, initial_index, None, next_by_index[initial_index])
    initial_scores = _positive_log_scores(model, initial_rows)
    transition_budget = 0
    transition_matrices: list[np.ndarray] = []
    for position in range(1, len(chord_items)):
        index, event = chord_items[position]
        previous_candidates = candidates_by_event[position - 1]
        current_candidates = candidates_by_event[position]
        transition_budget += len(previous_candidates) * len(current_candidates)
        if transition_budget > MAX_PATH_TRANSITIONS_PER_SOURCE:
            raise ValueError("source exceeds bounded path-transition budget")
        matrix = np.empty((len(previous_candidates), len(current_candidates)), dtype=np.float64)
        for previous_index, previous in enumerate(previous_candidates):
            rows = sequence_rows_for_event(source, event, index, previous, next_by_index[index])
            if tuple(row.placements for row in rows) != current_candidates:
                raise AssertionError("path candidate ordering changed across previous states")
            matrix[previous_index, :] = _positive_log_scores(model, rows)
        transition_matrices.append(matrix)
    selected_indices = _viterbi_indices(initial_scores, transition_matrices)
    return tuple(candidates_by_event[position][state_index] for position, state_index in enumerate(selected_indices))


def evaluate_sequence_path_decoder(model, sources: Iterable[ParsedSource]) -> PathRankingMetrics:
    correct = 0
    events = 0
    source_exact: list[float] = []
    for source in sources:
        chord_events = [event for event in source.events if event.is_chord]
        if not chord_events:
            continue
        selected = decode_source_sequence_path(model, source)
        if len(selected) != len(chord_events):
            raise AssertionError("path decoder returned wrong number of chord states")
        source_correct = True
        source_ambiguous = 0
        for event, chosen in zip(chord_events, selected):
            pitches = tuple(sorted(p.sounding_midi for p in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if len(candidates) <= 1:
                continue
            observed = _observed_voicing(event)
            is_correct = chosen == observed
            correct += int(is_correct)
            events += 1
            source_ambiguous += 1
            source_correct = source_correct and is_correct
        if source_ambiguous:
            source_exact.append(float(source_correct))
    if not events or not source_exact:
        raise ValueError("no ambiguous path evaluation events")
    return PathRankingMetrics(events=events, top1_accuracy=correct / events, sources=len(source_exact), exact_source_rate=float(np.mean(source_exact)))
