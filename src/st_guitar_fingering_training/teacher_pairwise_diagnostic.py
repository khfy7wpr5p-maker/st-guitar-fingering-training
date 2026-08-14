from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np

from .dataset import Voicing


STAGE7G_E2_GEOMETRY_NAMES = (
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

STAGE7G_E2_DELTA_NAMES = tuple(f"compact_minus_open__{name}" for name in STAGE7G_E2_GEOMETRY_NAMES)


@dataclass(frozen=True)
class TeacherPairwiseDiagnosticRow:
    family_id: str
    event_id: str
    chord_size: int
    candidate_count: int
    teacher_prefers_compact: int
    oof_predicted_compact: int
    geometry_delta: tuple[float, ...]


def _geometry(voicing: Voicing) -> tuple[float, ...]:
    if not voicing:
        raise ValueError("voicing must not be empty")
    strings = sorted(string for _, string, _ in voicing)
    frets = [fret for _, _, fret in voicing]
    if len(strings) != len(set(strings)):
        raise ValueError("voicing must use distinct strings")
    if any(string < 1 or string > 6 for string in strings):
        raise ValueError("Stage 7G-E2 supports six-string guitar only")
    if any(fret < 0 for fret in frets):
        raise ValueError("negative fret is invalid")

    positive = [fret for fret in frets if fret > 0]
    fret_counts = Counter(positive)
    adjacent_pairs = sum(abs(a - b) == 1 for a, b in zip(strings, strings[1:]))
    string_span = max(strings) - min(strings)
    internal_gaps = string_span + 1 - len(strings)

    if positive:
        min_positive = min(positive)
        mean_positive = float(np.mean(positive))
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
        mean_positive,
        float(max(frets)),
        float(positive_span),
        float(len(set(positive))),
        float(max_same_positive),
        float(string_span),
        adjacent_pairs / max(1, len(strings) - 1),
        float(internal_gaps),
    )
    if len(values) != len(STAGE7G_E2_GEOMETRY_NAMES) or not np.isfinite(np.asarray(values)).all():
        raise AssertionError("invalid Stage 7G-E2 geometry vector")
    return tuple(float(value) for value in values)


def teacher_pairwise_geometry_delta(open_low_top1: Voicing, compact_top1: Voicing) -> tuple[float, ...]:
    """Return fixed target-blind compact-minus-open ergonomic descriptors."""
    if open_low_top1 == compact_top1:
        raise ValueError("Stage 7G-E2 diagnostic requires specialist disagreement")
    open_values = _geometry(open_low_top1)
    compact_values = _geometry(compact_top1)
    return tuple(compact - open_value for compact, open_value in zip(compact_values, open_values))


def _three_way(value: float, tolerance: float = 0.0) -> str:
    if value < -tolerance:
        return "negative"
    if value > tolerance:
        return "positive"
    return "zero"


def stage7g_e2_fixed_strata(row: TeacherPairwiseDiagnosticRow) -> dict[str, str]:
    if row.teacher_prefers_compact not in (0, 1) or row.oof_predicted_compact not in (0, 1):
        raise ValueError("Stage 7G-E2 labels/predictions must be binary")
    if len(row.geometry_delta) != len(STAGE7G_E2_DELTA_NAMES):
        raise ValueError("Stage 7G-E2 geometry dimension mismatch")
    if row.chord_size < 2 or row.chord_size > 6:
        raise ValueError("invalid chord size")
    if row.candidate_count < 2:
        raise ValueError("invalid candidate count")

    delta = dict(zip(STAGE7G_E2_GEOMETRY_NAMES, row.geometry_delta))
    if row.chord_size == 2:
        chord_bucket = "2"
    elif row.chord_size == 3:
        chord_bucket = "3"
    elif row.chord_size == 4:
        chord_bucket = "4"
    else:
        chord_bucket = "5_plus"

    if row.candidate_count <= 12:
        candidate_bucket = "2_12"
    elif row.candidate_count <= 16:
        candidate_bucket = "13_16"
    else:
        candidate_bucket = "17_plus"

    return {
        "chord_size": chord_bucket,
        "candidate_count": candidate_bucket,
        "open_note_delta": _three_way(delta["open_note_count"]),
        "mean_positive_fret_delta": _three_way(delta["mean_positive_fret"], tolerance=1.0),
        "positive_fret_span_delta": _three_way(delta["positive_fret_span"]),
        "same_fret_barre_proxy_delta": _three_way(delta["max_same_positive_fret_count"]),
        "internal_string_gaps_delta": _three_way(delta["internal_string_gaps"]),
    }


def _aggregate(rows: Iterable[TeacherPairwiseDiagnosticRow]) -> dict:
    rows = tuple(rows)
    if not rows:
        return {"events": 0, "teacher_compact": 0, "teacher_compact_rate": None, "oof_accuracy": None}
    teacher = np.asarray([row.teacher_prefers_compact for row in rows], dtype=np.int64)
    predicted = np.asarray([row.oof_predicted_compact for row in rows], dtype=np.int64)
    return {
        "events": len(rows),
        "teacher_compact": int(np.sum(teacher == 1)),
        "teacher_compact_rate": float(np.mean(teacher == 1)),
        "oof_accuracy": float(np.mean(predicted == teacher)),
        "oof_false_positive_compact": int(np.sum((predicted == 1) & (teacher == 0))),
        "oof_false_negative_compact": int(np.sum((predicted == 0) & (teacher == 1))),
    }


def stage7g_e2_diagnostic_report(rows: Iterable[TeacherPairwiseDiagnosticRow]) -> dict:
    """Aggregate E1 out-of-fold errors without fitting or tuning another model."""
    rows = tuple(rows)
    if not rows:
        raise ValueError("no Stage 7G-E2 diagnostic rows")
    event_ids = [row.event_id for row in rows]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("duplicate Stage 7G-E2 event_id")
    if len({row.family_id for row in rows}) < 2:
        raise ValueError("Stage 7G-E2 requires multiple families")

    confusion = Counter()
    for row in rows:
        if row.teacher_prefers_compact == 1 and row.oof_predicted_compact == 1:
            confusion["compact_true_positive"] += 1
        elif row.teacher_prefers_compact == 1:
            confusion["compact_false_negative"] += 1
        elif row.oof_predicted_compact == 1:
            confusion["compact_false_positive"] += 1
        else:
            confusion["open_low_true_negative"] += 1

    by_family: dict[str, list[TeacherPairwiseDiagnosticRow]] = defaultdict(list)
    strata: dict[str, dict[str, list[TeacherPairwiseDiagnosticRow]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_family[row.family_id].append(row)
        for dimension, bucket in stage7g_e2_fixed_strata(row).items():
            strata[dimension][bucket].append(row)

    return {
        "stage": "7G-E2",
        "status": "DIAGNOSTIC_ONLY",
        "event_count": len(rows),
        "family_count": len(by_family),
        "confusion": dict(confusion),
        "overall": _aggregate(rows),
        "family_heterogeneity": {
            family_id: _aggregate(family_rows)
            for family_id, family_rows in sorted(by_family.items())
        },
        "fixed_strata": {
            dimension: {
                bucket: _aggregate(bucket_rows)
                for bucket, bucket_rows in sorted(buckets.items())
            }
            for dimension, buckets in sorted(strata.items())
        },
        "geometry_names": list(STAGE7G_E2_GEOMETRY_NAMES),
        "geometry_delta_semantics": "compact_minus_open_low",
        "model_fit_performed": False,
        "hyperparameter_search": False,
        "checkpoint_retained": False,
        "production_integration": False,
    }
