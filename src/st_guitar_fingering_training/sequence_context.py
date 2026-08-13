from __future__ import annotations

from typing import Iterable

import numpy as np

from .context import _event_id, _observed_voicing, _rank_rows, context_feature_vector
from .dataset import Voicing, VoicingCandidateRow, valid_chord_voicings
from .intake import GuitarEvent, MAX_FRET, ParsedSource
from .training import RankingMetrics


_LOOKAHEAD_FEATURES = 14


def _next_chord_events(source: ParsedSource) -> dict[int, GuitarEvent | None]:
    chord_indexes = [index for index, event in enumerate(source.events) if event.is_chord]
    out: dict[int, GuitarEvent | None] = {}
    for position, index in enumerate(chord_indexes):
        out[index] = source.events[chord_indexes[position + 1]] if position + 1 < len(chord_indexes) else None
    return out


def _bass_string(voicing: Voicing) -> int:
    bass_pitch = min(pitch for pitch, _, _ in voicing)
    return max(string for pitch, string, _ in voicing if pitch == bass_pitch)


def lookahead_feature_vector(candidate: Voicing, next_event: GuitarEvent | None) -> tuple[float, ...]:
    """Describe candidate compatibility with the next chord using pitch-only future truth.

    The next event's observed string/fret placement is never read. Future context is
    limited to next sounding pitches, tuning, and the physically enumerable candidate
    set derived from those values.
    """
    if next_event is None:
        return (0.0,) * _LOOKAHEAD_FEATURES
    if not next_event.is_chord:
        raise ValueError("lookahead requires a chord/polyphonic next event")

    next_pitches = tuple(sorted(p.sounding_midi for p in next_event.placements))
    next_candidates = valid_chord_voicings(next_pitches, next_event.tuning)
    if not next_candidates:
        raise ValueError("next chord has no physically valid voicing candidates")

    current_pitches = {p for p, _, _ in candidate}
    next_pitch_set = set(next_pitches)
    shared_pitches = current_pitches & next_pitch_set
    pitch_union = current_pitches | next_pitch_set

    current_frets = [fret for _, _, fret in candidate]
    current_strings = {string for _, string, _ in candidate}
    current_center = sum(current_frets) / len(current_frets)
    current_span = max(current_frets) - min(current_frets)
    current_open = sum(fret == 0 for fret in current_frets)
    current_bass_string = _bass_string(candidate)

    center_moves = []
    lower_moves = []
    upper_moves = []
    string_jaccards = []
    string_overlaps = []
    shared_pitch_string_continuities = []
    span_changes = []
    open_changes = []
    bass_string_moves = []

    candidate_pitch_strings = {(pitch, string) for pitch, string, _ in candidate}

    for nxt in next_candidates:
        next_frets = [fret for _, _, fret in nxt]
        next_strings = {string for _, string, _ in nxt}
        next_center = sum(next_frets) / len(next_frets)
        overlap = len(current_strings & next_strings)
        union = len(current_strings | next_strings)
        next_pitch_strings = {(pitch, string) for pitch, string, _ in nxt}

        center_moves.append(abs(current_center - next_center) / MAX_FRET)
        lower_moves.append(abs(min(current_frets) - min(next_frets)) / MAX_FRET)
        upper_moves.append(abs(max(current_frets) - max(next_frets)) / MAX_FRET)
        string_overlaps.append(overlap / 6.0)
        string_jaccards.append(overlap / max(1, union))
        shared_pitch_string_continuities.append(
            len(candidate_pitch_strings & next_pitch_strings) / max(1, len(shared_pitches))
            if shared_pitches
            else 0.0
        )
        span_changes.append(abs(current_span - (max(next_frets) - min(next_frets))) / MAX_FRET)
        open_changes.append(abs(current_open - sum(fret == 0 for fret in next_frets)) / 6.0)
        bass_string_moves.append(abs(current_bass_string - _bass_string(nxt)) / 5.0)

    return (
        1.0,
        len(next_pitches) / 6.0,
        min(next_pitches) / 127.0,
        max(next_pitches) / 127.0,
        len(shared_pitches) / max(1, len(pitch_union)),
        min(center_moves),
        min(lower_moves),
        min(upper_moves),
        max(string_overlaps),
        max(string_jaccards),
        max(shared_pitch_string_continuities),
        min(span_changes),
        min(open_changes),
        min(bass_string_moves),
    )


def sequence_feature_vector(
    candidate: Voicing,
    previous: Voicing | None,
    next_event: GuitarEvent | None,
) -> tuple[float, ...]:
    return context_feature_vector(candidate, previous) + lookahead_feature_vector(candidate, next_event)


def sequence_rows_for_event(
    source: ParsedSource,
    event: GuitarEvent,
    index: int,
    previous: Voicing | None,
    next_event: GuitarEvent | None,
) -> tuple[VoicingCandidateRow, ...]:
    if not event.is_chord:
        raise ValueError("sequence voicing rows require a chord/polyphonic event")
    observed = _observed_voicing(event)
    pitches = tuple(sorted(p.sounding_midi for p in event.placements))
    candidates = valid_chord_voicings(pitches, event.tuning)
    if not candidates or observed not in candidates:
        raise ValueError("invalid sequence voicing candidate set")
    event_id = _event_id(source, event, index)
    return tuple(
        VoicingCandidateRow(
            family_id=source.family_id,
            event_id=event_id,
            pitches_midi=pitches,
            placements=candidate,
            observed=int(candidate == observed),
            features=sequence_feature_vector(candidate, previous, next_event),
        )
        for candidate in candidates
    )


def build_sequence_training_rows(sources: Iterable[ParsedSource]) -> tuple[VoicingCandidateRow, ...]:
    """Build training rows with past observed context and future pitch-only context."""
    rows: list[VoicingCandidateRow] = []
    for source in sources:
        next_by_index = _next_chord_events(source)
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            rows.extend(sequence_rows_for_event(source, event, index, previous, next_by_index[index]))
            previous = _observed_voicing(event)
    return tuple(rows)


def evaluate_sequence_ranker_rollout(model, sources: Iterable[ParsedSource]) -> RankingMetrics:
    """Deployment-like rollout: past context is model output; future is pitch-only."""
    reciprocal = []
    correct = 0
    for source in sources:
        next_by_index = _next_chord_events(source)
        previous: Voicing | None = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            rows = sequence_rows_for_event(source, event, index, previous, next_by_index[index])
            if len(rows) == 1:
                previous = rows[0].placements
                continue
            ranked = _rank_rows(model, rows)
            ranks = [position + 1 for position, row in enumerate(ranked) if row.observed == 1]
            if len(ranks) != 1:
                raise ValueError("each sequence event must have exactly one observed candidate")
            rank = ranks[0]
            correct += int(rank == 1)
            reciprocal.append(1.0 / rank)
            previous = ranked[0].placements
    if not reciprocal:
        raise ValueError("no ambiguous sequence evaluation events")
    return RankingMetrics(len(reciprocal), correct / len(reciprocal), float(np.mean(reciprocal)))
