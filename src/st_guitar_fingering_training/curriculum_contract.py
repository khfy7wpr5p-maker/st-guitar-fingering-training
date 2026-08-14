from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from statistics import fmean
from typing import Mapping

from .dataset import Voicing, valid_chord_voicings


STAGE7G_E3_LEVELS = ("L1", "L2", "L3", "L4")

STAGE7G_E3_GEOMETRY_NAMES = (
    "open_note_count",
    "fretted_note_count",
    "min_positive_fret",
    "mean_positive_fret",
    "max_fret",
    "positive_fret_span",
    "unique_positive_frets",
    "max_same_positive_fret_count",
    "string_span",
    "adjacent_string_ratio",
    "internal_string_gaps",
)

STAGE7G_E3_CONTEXT_NAMES = (
    "chord_size",
    "pitch_span",
    "mean_pitch",
    "candidate_count",
    "candidate_open_fraction",
    "candidate_mean_positive_fret_mean",
    "candidate_positive_fret_span_mean",
)

STAGE7G_E3_FEATURE_NAMES = (
    STAGE7G_E3_CONTEXT_NAMES
    + tuple(f"open_low__{name}" for name in STAGE7G_E3_GEOMETRY_NAMES)
    + tuple(f"compact__{name}" for name in STAGE7G_E3_GEOMETRY_NAMES)
    + tuple(f"compact_minus_open__{name}" for name in STAGE7G_E3_GEOMETRY_NAMES)
)

# These thresholds define curriculum difficulty only. They are not teacher-preference
# rules and must never be interpreted as proof that one proposal is more natural.
STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS = {
    "open_note_count": 1.0,
    "fretted_note_count": 1.0,
    "mean_positive_fret": 3.0,
    "positive_fret_span": 2.0,
    "string_span": 2.0,
    "internal_string_gaps": 1.0,
}

STAGE7G_E3_RULE_PROPERTY_TARGETS = (
    "more_open_notes",
    "fewer_fretted_notes",
    "lower_mean_positive_fret",
    "narrower_positive_fret_span",
    "smaller_string_span",
    "fewer_internal_string_gaps",
)

STAGE7G_E3_RULE_PROPERTY_VALUES = ("OPEN_LOW", "COMPACT", "EQUAL")
STAGE7G_E3_TEACHER_TARGET = "pairwise_guitaristic_preference"
STAGE7G_E3_TEACHER_VALUES = ("OPEN_LOW", "COMPACT", "EQUAL_OR_UNSURE")
STAGE7G_E3_PROVENANCE = ("RULE_DERIVED_PROPERTY", "TEACHER_GOLD")


@dataclass(frozen=True)
class Stage7GE3Supervision:
    curriculum_level: str
    provenance: str
    target_name: str
    target_value: str
    annotation_blinded: bool


def stage7g_e3_proposal_geometry(voicing: Voicing) -> tuple[float, ...]:
    """Return the frozen E3 target-blind proposal-geometry descriptor vector."""

    if not voicing:
        raise ValueError("voicing must not be empty")
    strings = sorted(int(string) for _, string, _ in voicing)
    frets = [int(fret) for _, _, fret in voicing]
    if len(strings) != len(set(strings)):
        raise ValueError("voicing must use distinct strings")
    if any(string < 1 or string > 6 for string in strings):
        raise ValueError("Stage 7G-E3 supports six-string guitar only")
    if any(fret < 0 for fret in frets):
        raise ValueError("negative fret is invalid")

    positive = [fret for fret in frets if fret > 0]
    fret_counts = Counter(positive)
    string_span = max(strings) - min(strings)
    adjacent_pairs = sum(abs(a - b) == 1 for a, b in zip(strings, strings[1:]))
    internal_gaps = string_span + 1 - len(strings)

    if positive:
        min_positive = min(positive)
        mean_positive = fmean(positive)
        positive_span = max(positive) - min(positive)
        max_same_positive = max(fret_counts.values())
    else:
        min_positive = 0
        mean_positive = 0.0
        positive_span = 0
        max_same_positive = 0

    values = (
        float(sum(fret == 0 for fret in frets)),
        float(len(positive)),
        float(min_positive),
        float(mean_positive),
        float(max(frets)),
        float(positive_span),
        float(len(set(positive))),
        float(max_same_positive),
        float(string_span),
        adjacent_pairs / max(1, len(strings) - 1),
        float(internal_gaps),
    )
    if len(values) != len(STAGE7G_E3_GEOMETRY_NAMES) or not all(isfinite(value) for value in values):
        raise AssertionError("invalid Stage 7G-E3 geometry vector")
    return tuple(float(value) for value in values)


def stage7g_e3_feature_record(
    pitches: tuple[int, ...],
    tuning: tuple[int, ...],
    open_low_top1: Voicing,
    compact_top1: Voicing,
) -> dict[str, float]:
    """Build the frozen E3-A target-blind raw feature record.

    This is a contract helper only. It does not train a model or assign a
    Teacher-GOLD preference.
    """

    pitches = tuple(sorted(int(value) for value in pitches))
    tuning = tuple(int(value) for value in tuning)
    if len(tuning) != 6:
        raise ValueError("Stage 7G-E3 supports six-string guitar tuning only")
    if len(pitches) < 2 or len(pitches) > 6:
        raise ValueError("Stage 7G-E3 requires 2..6 chord pitches")
    if open_low_top1 == compact_top1:
        raise ValueError("Stage 7G-E3 requires an open_low-vs-compact disagreement")

    candidates = valid_chord_voicings(pitches, tuning)
    if len(candidates) < 2:
        raise ValueError("Stage 7G-E3 requires an ambiguous deterministic candidate set")
    if open_low_top1 not in candidates or compact_top1 not in candidates:
        raise ValueError("specialist proposals must belong to the deterministic candidate set")

    candidate_geometry = [stage7g_e3_proposal_geometry(candidate) for candidate in candidates]
    open_geometry = stage7g_e3_proposal_geometry(open_low_top1)
    compact_geometry = stage7g_e3_proposal_geometry(compact_top1)

    geometry_index = {name: index for index, name in enumerate(STAGE7G_E3_GEOMETRY_NAMES)}
    context = {
        "chord_size": float(len(pitches)),
        "pitch_span": float(max(pitches) - min(pitches)),
        "mean_pitch": float(fmean(pitches)),
        "candidate_count": float(len(candidates)),
        "candidate_open_fraction": float(
            sum(values[geometry_index["open_note_count"]] > 0 for values in candidate_geometry)
            / len(candidate_geometry)
        ),
        "candidate_mean_positive_fret_mean": float(
            fmean(values[geometry_index["mean_positive_fret"]] for values in candidate_geometry)
        ),
        "candidate_positive_fret_span_mean": float(
            fmean(values[geometry_index["positive_fret_span"]] for values in candidate_geometry)
        ),
    }

    record: dict[str, float] = dict(context)
    for name, value in zip(STAGE7G_E3_GEOMETRY_NAMES, open_geometry):
        record[f"open_low__{name}"] = float(value)
    for name, value in zip(STAGE7G_E3_GEOMETRY_NAMES, compact_geometry):
        record[f"compact__{name}"] = float(value)
    for name, open_value, compact_value in zip(
        STAGE7G_E3_GEOMETRY_NAMES, open_geometry, compact_geometry
    ):
        record[f"compact_minus_open__{name}"] = float(compact_value - open_value)

    if tuple(record) != STAGE7G_E3_FEATURE_NAMES:
        raise AssertionError("Stage 7G-E3 feature ordering drift")
    if not all(isfinite(value) for value in record.values()):
        raise AssertionError("Stage 7G-E3 features must be finite")
    return record


def stage7g_e3_curriculum_level(
    *,
    chord_size: int,
    candidate_count: int,
    geometry_delta: Mapping[str, float],
) -> str:
    """Assign one deterministic curriculum difficulty level without teacher labels."""

    if chord_size < 2 or chord_size > 6:
        raise ValueError("Stage 7G-E3 chord_size must be in 2..6")
    if candidate_count < 2:
        raise ValueError("Stage 7G-E3 candidate_count must be >= 2")
    if set(geometry_delta) != set(STAGE7G_E3_GEOMETRY_NAMES):
        raise ValueError("Stage 7G-E3 geometry delta keys do not match the frozen contract")
    if not all(isfinite(float(value)) for value in geometry_delta.values()):
        raise ValueError("Stage 7G-E3 geometry deltas must be finite")

    strong_contrasts = sum(
        abs(float(geometry_delta[name])) >= threshold
        for name, threshold in STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS.items()
    )

    if chord_size == 2 and candidate_count <= 12 and strong_contrasts >= 2:
        return "L1"
    if chord_size <= 3 and candidate_count <= 20 and strong_contrasts >= 1:
        return "L2"
    if chord_size <= 4 and candidate_count <= 40:
        return "L3"
    return "L4"


def validate_stage7g_e3_supervision(supervision: Stage7GE3Supervision) -> None:
    """Fail closed on provenance/target semantics.

    Rule-derived property supervision is descriptive only. Teacher preference
    requires a blind Teacher-GOLD response.
    """

    if supervision.curriculum_level not in STAGE7G_E3_LEVELS:
        raise ValueError("unknown Stage 7G-E3 curriculum level")
    if supervision.provenance not in STAGE7G_E3_PROVENANCE:
        raise ValueError("unknown Stage 7G-E3 supervision provenance")

    if supervision.provenance == "RULE_DERIVED_PROPERTY":
        if supervision.curriculum_level not in ("L1", "L2"):
            raise ValueError("rule-derived property supervision is limited to L1/L2")
        if supervision.target_name not in STAGE7G_E3_RULE_PROPERTY_TARGETS:
            raise ValueError("unknown Stage 7G-E3 rule-derived property target")
        if supervision.target_value not in STAGE7G_E3_RULE_PROPERTY_VALUES:
            raise ValueError("invalid Stage 7G-E3 rule-derived property value")
        if supervision.annotation_blinded:
            raise ValueError("rule-derived property supervision is not a teacher annotation")
        return

    if supervision.target_name != STAGE7G_E3_TEACHER_TARGET:
        raise ValueError("Teacher-GOLD must use the frozen pairwise preference target")
    if supervision.target_value not in STAGE7G_E3_TEACHER_VALUES:
        raise ValueError("invalid Stage 7G-E3 Teacher-GOLD response")
    if not supervision.annotation_blinded:
        raise ValueError("Stage 7G-E3 Teacher-GOLD must be blinded")


def stage7g_e3_rule_property_value(
    property_name: str,
    open_low_geometry: Mapping[str, float],
    compact_geometry: Mapping[str, float],
) -> str:
    """Return the factual side for one frozen property, never a preference label."""

    if property_name not in STAGE7G_E3_RULE_PROPERTY_TARGETS:
        raise ValueError("unknown Stage 7G-E3 rule-derived property target")
    if set(open_low_geometry) != set(STAGE7G_E3_GEOMETRY_NAMES):
        raise ValueError("open_low geometry keys do not match the frozen contract")
    if set(compact_geometry) != set(STAGE7G_E3_GEOMETRY_NAMES):
        raise ValueError("compact geometry keys do not match the frozen contract")

    direction = {
        "more_open_notes": ("open_note_count", 1),
        "fewer_fretted_notes": ("fretted_note_count", -1),
        "lower_mean_positive_fret": ("mean_positive_fret", -1),
        "narrower_positive_fret_span": ("positive_fret_span", -1),
        "smaller_string_span": ("string_span", -1),
        "fewer_internal_string_gaps": ("internal_string_gaps", -1),
    }
    geometry_name, sign = direction[property_name]
    open_value = float(open_low_geometry[geometry_name])
    compact_value = float(compact_geometry[geometry_name])
    if not isfinite(open_value) or not isfinite(compact_value):
        raise ValueError("Stage 7G-E3 property values must be finite")
    signed_delta = sign * (compact_value - open_value)
    if signed_delta > 0:
        return "COMPACT"
    if signed_delta < 0:
        return "OPEN_LOW"
    return "EQUAL"
