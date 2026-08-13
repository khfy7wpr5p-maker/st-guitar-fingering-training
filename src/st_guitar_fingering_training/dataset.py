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


def valid_single_note_candidates(pitch_midi: int, tuning: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    out = []
    for string_no, open_midi in enumerate(tuning, start=1):
        fret = pitch_midi - open_midi
        if 0 <= fret <= MAX_FRET:
            out.append((string_no, fret))
    return tuple(out)


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
