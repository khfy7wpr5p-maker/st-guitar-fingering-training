from __future__ import annotations

from typing import Iterable

import numpy as np

from .dataset import MAX_FRET, Voicing, VoicingCandidateRow, _voicing_feature_vector, valid_chord_voicings
from .intake import GuitarEvent, ParsedSource
from .training import RankingMetrics


def _observed_voicing(event: GuitarEvent) -> Voicing:
    return tuple(sorted((p.sounding_midi, p.string, p.fret) for p in event.placements))


def _event_id(source: ParsedSource, event: GuitarEvent, index: int) -> str:
    return f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"


def transition_feature_vector(candidate: Voicing, previous: Voicing | None) -> tuple[float, ...]:
    if previous is None:
        return (0.0,) * 10

    cf = [f for _, _, f in candidate]
    pf = [f for _, _, f in previous]
    cs = {s for _, s, _ in candidate}
    ps = {s for _, s, _ in previous}
    cc = sum(cf) / len(cf)
    pc = sum(pf) / len(pf)
    cspan = max(cf) - min(cf)
    pspan = max(pf) - min(pf)
    copen = sum(f == 0 for f in cf)
    popen = sum(f == 0 for f in pf)
    shared_pitch_strings = {(p, s) for p, s, _ in candidate} & {(p, s) for p, s, _ in previous}
    shared_pitches = {p for p, _, _ in candidate} & {p for p, _, _ in previous}
    overlap = len(cs & ps)
    union = len(cs | ps)
    cbp = min(p for p, _, _ in candidate)
    pbp = min(p for p, _, _ in previous)
    cbs = max(s for p, s, _ in candidate if p == cbp)
    pbs = max(s for p, s, _ in previous if p == pbp)

    return (
        1.0,
        (cc - pc) / MAX_FRET,
        abs(cc - pc) / MAX_FRET,
        abs(min(cf) - min(pf)) / MAX_FRET,
        abs(max(cf) - max(pf)) / MAX_FRET,
        overlap / 6.0,
        overlap / max(1, union),
        len(shared_pitch_strings) / max(1, len(shared_pitches)),
        abs(cspan - pspan) / MAX_FRET,
        abs(cbs - pbs) / 5.0 + abs(copen - popen) / 6.0,
    )


def context_feature_vector(candidate: Voicing, previous: Voicing | None) -> tuple[float, ...]:
    return _voicing_feature_vector(candidate) + transition_feature_vector(candidate, previous)


def context_rows_for_event(source: ParsedSource, event: GuitarEvent, index: int, previous: Voicing | None) -> tuple[VoicingCandidateRow, ...]:
    if not event.is_chord:
        raise ValueError("context voicing rows require a chord/polyphonic event")
    observed = _observed_voicing(event)
    pitches = tuple(sorted(p.sounding_midi for p in event.placements))
    candidates = valid_chord_voicings(pitches, event.tuning)
    if not candidates or observed not in candidates:
        raise ValueError("invalid context voicing candidate set")
    eid = _event_id(source, event, index)
    return tuple(
        VoicingCandidateRow(
            family_id=source.family_id,
            event_id=eid,
            pitches_midi=pitches,
            placements=c,
            observed=int(c == observed),
            features=context_feature_vector(c, previous),
        )
        for c in candidates
    )


def build_context_training_rows(sources: Iterable[ParsedSource]) -> tuple[VoicingCandidateRow, ...]:
    rows = []
    for source in sources:
        previous = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            rows.extend(context_rows_for_event(source, event, index, previous))
            previous = _observed_voicing(event)
    return tuple(rows)


def _rank_rows(model, rows):
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    if X.ndim != 2 or X.shape[0] == 0 or not np.isfinite(X).all():
        raise ValueError("invalid context evaluation feature matrix")
    scores = model.predict_proba(X)[:, 1]
    return [row for row, _ in sorted(zip(rows, scores), key=lambda x: (-x[1], tuple(x[0].placements)))]


def evaluate_context_ranker_rollout(model, sources: Iterable[ParsedSource]) -> RankingMetrics:
    reciprocal = []
    correct = 0
    for source in sources:
        previous = None
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            rows = context_rows_for_event(source, event, index, previous)
            if len(rows) == 1:
                previous = rows[0].placements
                continue
            ranked = _rank_rows(model, rows)
            ranks = [i + 1 for i, row in enumerate(ranked) if row.observed == 1]
            if len(ranks) != 1:
                raise ValueError("each context event must have exactly one observed candidate")
            rank = ranks[0]
            correct += int(rank == 1)
            reciprocal.append(1.0 / rank)
            previous = ranked[0].placements
    if not reciprocal:
        raise ValueError("no ambiguous context evaluation events")
    return RankingMetrics(len(reciprocal), correct / len(reciprocal), float(np.mean(reciprocal)))
