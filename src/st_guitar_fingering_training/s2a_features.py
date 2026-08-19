from __future__ import annotations

from hashlib import sha256
from itertools import combinations
import json
from math import isfinite

from .finger_assignments import StandardFingering
from .intake import MAX_FRET


S2A_PROTOCOL_VERSION = "S2-A.v1"

S2A_FEATURE_NAMES = tuple(
    name
    for string_no in range(1, 7)
    for name in (
        f"string_{string_no}_used",
        f"string_{string_no}_fret_norm",
        f"string_{string_no}_finger_norm",
    )
) + (
    "open_note_ratio",
    "mean_positive_fret_norm",
    "positive_fret_span_norm",
    "used_string_span_norm",
    "internal_string_gap_ratio",
    "standard_finger_count_norm",
    "barre_count_norm",
    "max_barre_span_norm",
    "total_barre_span_norm",
    "barre_override_note_ratio",
    "max_finger_fret_step_norm",
    "same_fret_multi_finger_pair_ratio",
)

S2A_FEATURE_LIST_SHA256 = sha256(
    json.dumps(S2A_FEATURE_NAMES, separators=(",", ":")).encode("ascii")
).hexdigest()


def _validated_assignment_maps(
    assignment: StandardFingering,
) -> tuple[dict[int, tuple[int, int, int]], dict[int, int]]:
    by_string: dict[int, tuple[int, int, int]] = {}
    fret_by_finger: dict[int, int] = {}

    if not assignment.assignment_id.startswith("fingering-sha256:"):
        raise ValueError("S2-A requires a stable S1-H-C assignment_id")

    for pitch, string, fret, finger in assignment.placements:
        if not 1 <= string <= 6:
            raise ValueError("S2-A supports six-string assignments only")
        if string in by_string:
            raise ValueError("S2-A assignment reuses a string")
        if not 0 <= fret <= MAX_FRET:
            raise ValueError("S2-A assignment fret outside repository range")
        if fret == 0 and finger != 0:
            raise ValueError("S2-A open string must use finger 0")
        if fret > 0 and finger not in (1, 2, 3, 4):
            raise ValueError("S2-A fretted note must use finger 1..4")
        by_string[string] = (pitch, fret, finger)
        if finger > 0:
            existing = fret_by_finger.get(finger)
            if existing is not None and existing != fret:
                raise ValueError("S2-A one finger may not occupy multiple frets in one assignment")
            fret_by_finger[finger] = fret

    if not by_string:
        raise ValueError("S2-A assignment must contain at least one note")

    for finger, fret, span_start, span_end in assignment.barres:
        if finger not in (1, 2, 3, 4):
            raise ValueError("S2-A barre finger outside 1..4")
        if not 0 < fret <= MAX_FRET:
            raise ValueError("S2-A barre fret outside repository range")
        if not (1 <= span_start < span_end <= 6):
            raise ValueError("S2-A barre span must cover at least two string positions")
        if fret_by_finger.get(finger) != fret:
            raise ValueError("S2-A barre metadata does not match assignment finger/fret")

    return by_string, fret_by_finger


def assignment_feature_vector(assignment: StandardFingering) -> tuple[float, ...]:
    """Return the frozen 30D S2-A deterministic target-blind feature vector."""

    by_string, fret_by_finger = _validated_assignment_maps(assignment)
    values: list[float] = []

    for string_no in range(1, 7):
        placement = by_string.get(string_no)
        if placement is None:
            values.extend((0.0, 0.0, 0.0))
        else:
            _, fret, finger = placement
            values.extend((1.0, fret / MAX_FRET, finger / 4.0))

    used_strings = sorted(by_string)
    frets = [fret for _, fret, _ in by_string.values()]
    positive_frets = [fret for fret in frets if fret > 0]
    fretted_note_count = len(positive_frets)

    open_note_ratio = sum(fret == 0 for fret in frets) / len(frets)
    mean_positive_fret_norm = (
        (sum(positive_frets) / len(positive_frets)) / MAX_FRET if positive_frets else 0.0
    )
    positive_fret_span_norm = (
        (max(positive_frets) - min(positive_frets)) / MAX_FRET
        if len(positive_frets) >= 2
        else 0.0
    )
    used_string_span_norm = (
        (max(used_strings) - min(used_strings)) / 5.0 if len(used_strings) >= 2 else 0.0
    )
    internal_positions = max(used_strings) - min(used_strings) - 1
    internal_gaps = (
        sum(string not in by_string for string in range(min(used_strings) + 1, max(used_strings)))
        if internal_positions > 0
        else 0
    )
    internal_string_gap_ratio = internal_gaps / internal_positions if internal_positions > 0 else 0.0
    standard_finger_count_norm = len(fret_by_finger) / 4.0

    barre_spans = [span_end - span_start for _, _, span_start, span_end in assignment.barres]
    barre_count_norm = len(assignment.barres) / 4.0
    max_barre_span_norm = max(barre_spans) / 5.0 if barre_spans else 0.0
    total_barre_span_norm = sum(barre_spans) / 20.0

    override_count = 0
    if fretted_note_count:
        for _, string, fret, _ in assignment.placements:
            if fret <= 0:
                continue
            if any(
                span_start <= string <= span_end and fret > barre_fret
                for _, barre_fret, span_start, span_end in assignment.barres
            ):
                override_count += 1
    barre_override_note_ratio = override_count / fretted_note_count if fretted_note_count else 0.0

    active_fingers = sorted(fret_by_finger)
    finger_steps: list[float] = []
    for left, right in zip(active_fingers, active_fingers[1:]):
        fret_delta = fret_by_finger[right] - fret_by_finger[left]
        finger_delta = right - left
        if finger_delta <= 0 or fret_delta < 0:
            raise ValueError("S2-A assignment violates monotonic finger/fret envelope")
        finger_steps.append((fret_delta / finger_delta) / MAX_FRET)
    max_finger_fret_step_norm = max(finger_steps) if finger_steps else 0.0

    same_fret_pairs = sum(
        fret_by_finger[left] == fret_by_finger[right]
        for left, right in combinations(active_fingers, 2)
    )
    same_fret_multi_finger_pair_ratio = same_fret_pairs / 6.0

    values.extend((
        open_note_ratio,
        mean_positive_fret_norm,
        positive_fret_span_norm,
        used_string_span_norm,
        internal_string_gap_ratio,
        standard_finger_count_norm,
        barre_count_norm,
        max_barre_span_norm,
        total_barre_span_norm,
        barre_override_note_ratio,
        max_finger_fret_step_norm,
        same_fret_multi_finger_pair_ratio,
    ))

    if len(values) != len(S2A_FEATURE_NAMES) or len(values) != 30:
        raise AssertionError("S2-A feature dimension mismatch")
    if not all(isfinite(value) for value in values):
        raise ValueError("S2-A features must be finite")
    return tuple(float(value) for value in values)
