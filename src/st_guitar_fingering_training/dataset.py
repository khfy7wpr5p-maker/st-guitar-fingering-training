from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from collections import defaultdict

from .intake import ParsedSource, MAX_FRET


@dataclass(frozen=True)
class CandidateRow:
    family_id: str
    event_id: str
    pitch_midi: int
    string: int
    fret: int
    observed: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class VoicingCandidateRow:
    family_id: str
    event_id: str
    pitches_midi: tuple[int, ...]
    placements: tuple[tuple[int, int, int], ...]
    observed: int
    features: tuple[float, ...]


VoicingPlacement = tuple[int, int, int]  # (pitch_midi, string, fret)
Voicing = tuple[VoicingPlacement, ...]


def valid_single_note_candidates(pitch_midi: int, tuning: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    out = []
    for string_no, open_midi in enumerate(tuning, start=1):
        fret = pitch_midi - open_midi
        if 0 <= fret <= MAX_FRET:
            out.append((string_no, fret))
    return tuple(out)


def valid_chord_voicings(pitches_midi: Iterable[int], tuning: tuple[int, ...]) -> tuple[Voicing, ...]:
    """Enumerate physically valid simultaneous pitch→string/fret assignments.

    Each simultaneous note must use a distinct string. Duplicate pitches are allowed,
    but equivalent assignments are deduplicated so swapping two identical pitches does
    not create duplicate voicing candidates.
    """
    pitches = tuple(sorted(int(p) for p in pitches_midi))
    if len(pitches) < 2:
        raise ValueError("voicing candidates require at least two simultaneous pitches")
    if len(pitches) > len(tuning):
        return ()

    per_pitch = tuple(valid_single_note_candidates(pitch, tuning) for pitch in pitches)
    if any(not candidates for candidates in per_pitch):
        return ()

    out: set[Voicing] = set()

    def visit(index: int, used_strings: frozenset[int], chosen: tuple[VoicingPlacement, ...]) -> None:
        if index == len(pitches):
            out.add(tuple(sorted(chosen)))
            return
        pitch = pitches[index]
        for string_no, fret in per_pitch[index]:
            if string_no in used_strings:
                continue
            visit(
                index + 1,
                used_strings | {string_no},
                chosen + ((pitch, string_no, fret),),
            )

    visit(0, frozenset(), ())
    return tuple(sorted(out))


def _feature_vector(pitch: int, string: int, fret: int, prev_pitch: int | None) -> tuple[float, ...]:
    string_one_hot = tuple(1.0 if string == i else 0.0 for i in range(1, 7))
    return (
        pitch / 127.0,
        (pitch % 12) / 11.0,
        fret / MAX_FRET,
        1.0 if fret == 0 else 0.0,
        0.0 if prev_pitch is None else max(-24, min(24, pitch - prev_pitch)) / 24.0,
        *string_one_hot,
    )


def _voicing_feature_vector(voicing: Voicing) -> tuple[float, ...]:
    if not voicing:
        raise ValueError("empty voicing")
    pitches = [pitch for pitch, _, _ in voicing]
    strings = [string for _, string, _ in voicing]
    frets = [fret for _, _, fret in voicing]
    if any(not 1 <= string <= 6 for string in strings):
        raise ValueError("Chord/Voicing Dataset v1 supports six-string guitars only")

    string_mask = tuple(1.0 if string_no in strings else 0.0 for string_no in range(1, 7))
    pitch_range = max(pitches) - min(pitches)
    fret_span = max(frets) - min(frets)
    string_span = max(strings) - min(strings)
    open_count = sum(fret == 0 for fret in frets)
    adjacent_pairs = sum(abs(a - b) == 1 for a, b in zip(sorted(strings), sorted(strings)[1:]))

    return (
        len(voicing) / 6.0,
        min(pitches) / 127.0,
        max(pitches) / 127.0,
        min(pitch_range, 48) / 48.0,
        min(frets) / MAX_FRET,
        max(frets) / MAX_FRET,
        sum(frets) / (len(frets) * MAX_FRET),
        fret_span / MAX_FRET,
        open_count / len(frets),
        string_span / 5.0,
        adjacent_pairs / max(1, len(strings) - 1),
        *string_mask,
    )


def build_candidate_rows(sources: Iterable[ParsedSource]) -> tuple[CandidateRow, ...]:
    rows = []
    for source in sources:
        prev_pitch = None
        for index, event in enumerate(source.events):
            if event.is_chord:
                prev_pitch = None
                continue
            placement = event.placements[0]
            candidates = valid_single_note_candidates(placement.sounding_midi, event.tuning)
            if (placement.string, placement.fret) not in candidates:
                raise ValueError("observed placement missing from physical candidate set")
            event_id = f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"
            for string_no, fret in candidates:
                rows.append(CandidateRow(
                    family_id=source.family_id,
                    event_id=event_id,
                    pitch_midi=placement.sounding_midi,
                    string=string_no,
                    fret=fret,
                    observed=int((string_no, fret) == (placement.string, placement.fret)),
                    features=_feature_vector(placement.sounding_midi, string_no, fret, prev_pitch),
                ))
            prev_pitch = placement.sounding_midi
    return tuple(rows)


def build_voicing_candidate_rows(sources: Iterable[ParsedSource]) -> tuple[VoicingCandidateRow, ...]:
    """Build one ranking group per physically validated chord/polyphonic event."""
    rows: list[VoicingCandidateRow] = []
    for source in sources:
        if len(source.tuning) != 6:
            raise ValueError("Chord/Voicing Dataset v1 supports six-string guitars only")
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue

            observed: Voicing = tuple(sorted(
                (placement.sounding_midi, placement.string, placement.fret)
                for placement in event.placements
            ))
            pitches = tuple(sorted(placement.sounding_midi for placement in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if not candidates:
                raise ValueError("chord event has no physically valid voicing candidates")
            if observed not in candidates:
                raise ValueError("observed chord voicing missing from physical candidate set")

            event_id = f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"
            for candidate in candidates:
                rows.append(VoicingCandidateRow(
                    family_id=source.family_id,
                    event_id=event_id,
                    pitches_midi=pitches,
                    placements=candidate,
                    observed=int(candidate == observed),
                    features=_voicing_feature_vector(candidate),
                ))
    return tuple(rows)


def split_families(sources: Iterable[ParsedSource], validation_count: int = 2):
    groups: dict[str, list[ParsedSource]] = defaultdict(list)
    for source in sources:
        groups[source.family_id].append(source)
    ordered_ids = sorted(groups, key=lambda family_id: sha256(family_id.encode()).hexdigest())
    if len(ordered_ids) <= validation_count:
        raise ValueError("not enough source families for requested split")
    validation_ids = set(ordered_ids[-validation_count:])
    train = tuple(source for family_id in ordered_ids if family_id not in validation_ids for source in groups[family_id])
    validation = tuple(source for family_id in ordered_ids if family_id in validation_ids for source in groups[family_id])
    if {s.family_id for s in train} & {s.family_id for s in validation}:
        raise AssertionError("family leakage across train/validation")
    return train, validation
