from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Iterable

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from .curriculum_contract import (
    STAGE7G_E3_CONTEXT_NAMES,
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS,
)
from .stage7g_e3_r2_learning import (
    STAGE7G_E3_R2_EXPECTED_DECISIVE,
    STAGE7G_E3_R2_EXPECTED_FAMILIES,
    Stage7GE3R2TrainingRow,
)
from .stage7g_e3_s0_diagnostic import (
    STAGE7G_E3_S0_CONFIG,
    _assert_contract,
    _fit_fixed_epochs,
    _metrics,
)

STAGE7G_E3_S0B_SCHEMA = "st-guitar-stage7g-e3-s0b-error-attribution-v1"

# S0-B does not invent new numeric cut-points. It groups the already-frozen
# Stage 7G-E3 strong-contrast properties into interpretable axes.
STAGE7G_E3_S0B_AXIS_PROPERTIES = {
    "OPEN_STRING_ECONOMY": ("open_note_count", "fretted_note_count"),
    "POSITION": ("mean_positive_fret",),
    "STRETCH": ("positive_fret_span",),
    "STRING_TOPOLOGY": ("string_span", "internal_string_gaps"),
}

STAGE7G_E3_S0B_CONFIG = {
    "purpose": "event_level_descriptive_error_attribution_without_model_or_architecture_selection",
    "source_model": "exact_frozen_stage7g_e3_s0_final_epoch_oof",
    "decision_threshold": 0.5,
    "axis_properties": STAGE7G_E3_S0B_AXIS_PROPERTIES,
    "contrast_threshold_source": "STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS",
    "primary_bucket_rule": (
        "NO_STRONG_AXIS if zero active axes; SINGLE_AXIS_<AXIS> if exactly one; "
        "MULTI_AXIS if two or more"
    ),
    "forbidden": {
        "scheduler": True,
        "threshold_search": True,
        "hyperparameter_search": True,
        "new_features": True,
        "new_contrast_thresholds": True,
        "specialist_training": True,
        "specialist_architecture_activation": True,
        "early_stopping": True,
        "best_epoch_checkpoint_selection": True,
        "e3e_teacher_gold": True,
        "stage7e": True,
        "checkpoint_retention": True,
        "production_or_shadow_integration": True,
        "causal_attribution_claim": True,
    },
}


def _direction(value: float, threshold: float) -> str:
    if value >= threshold:
        return "COMPACT_HIGHER_BY_THRESHOLD"
    if value <= -threshold:
        return "OPEN_LOW_HIGHER_BY_THRESHOLD"
    return "WEAK_CONTRAST"


def _feature_views(features: tuple[float, ...]) -> dict:
    if len(features) != len(STAGE7G_E3_FEATURE_NAMES):
        raise ValueError("S0-B feature vector length mismatch")
    values = np.asarray(features, dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("S0-B feature vector contains non-finite values")
    record = dict(zip(STAGE7G_E3_FEATURE_NAMES, (float(v) for v in values)))
    context = {name: record[name] for name in STAGE7G_E3_CONTEXT_NAMES}
    open_geometry = {
        name: record[f"open_low__{name}"] for name in STAGE7G_E3_GEOMETRY_NAMES
    }
    compact_geometry = {
        name: record[f"compact__{name}"] for name in STAGE7G_E3_GEOMETRY_NAMES
    }
    deltas = {
        name: record[f"compact_minus_open__{name}"] for name in STAGE7G_E3_GEOMETRY_NAMES
    }
    return {
        "context": context,
        "open_low_geometry": open_geometry,
        "compact_geometry": compact_geometry,
        "compact_minus_open": deltas,
    }


def _axis_attribution(deltas: dict[str, float]) -> dict:
    property_directions = {
        name: _direction(float(deltas[name]), float(threshold))
        for name, threshold in STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS.items()
    }
    active_axes = []
    axis_details = {}
    for axis, properties in STAGE7G_E3_S0B_AXIS_PROPERTIES.items():
        active_properties = [
            name
            for name in properties
            if property_directions[name] != "WEAK_CONTRAST"
        ]
        active = bool(active_properties)
        if active:
            active_axes.append(axis)
        axis_details[axis] = {
            "active": active,
            "active_properties": active_properties,
            "property_directions": {
                name: property_directions[name] for name in properties
            },
        }
    if not active_axes:
        primary_bucket = "NO_STRONG_AXIS"
    elif len(active_axes) == 1:
        primary_bucket = f"SINGLE_AXIS_{active_axes[0]}"
    else:
        primary_bucket = "MULTI_AXIS"
    return {
        "primary_bucket": primary_bucket,
        "active_axes": active_axes,
        "active_axis_count": len(active_axes),
        "axis_details": axis_details,
        "property_directions": property_directions,
        "semantics": "DESCRIPTIVE_TARGET_BLIND_GEOMETRY_NOT_CAUSAL_PREFERENCE_LABEL",
    }


def _error_type(target: int, prediction: int) -> str:
    if target == 1 and prediction == 1:
        return "TP"
    if target == 0 and prediction == 1:
        return "FP"
    if target == 1 and prediction == 0:
        return "FN"
    return "TN"


def _summary(rows: list[dict]) -> dict:
    error_counts = Counter(row["error_type"] for row in rows)
    error_by_level: dict[str, Counter] = {}
    error_by_bucket: dict[str, Counter] = {}
    for row in rows:
        error_by_level.setdefault(row["curriculum_level"], Counter())[row["error_type"]] += 1
        error_by_bucket.setdefault(row["attribution"]["primary_bucket"], Counter())[row["error_type"]] += 1

    def ordered(counter: Counter) -> dict:
        return {name: int(counter.get(name, 0)) for name in ("TP", "FP", "FN", "TN")}

    return {
        "error_counts": ordered(error_counts),
        "errors_only": {
            "fp": int(error_counts.get("FP", 0)),
            "fn": int(error_counts.get("FN", 0)),
            "total": int(error_counts.get("FP", 0) + error_counts.get("FN", 0)),
        },
        "by_curriculum_level": {
            key: ordered(error_by_level[key]) for key in sorted(error_by_level)
        },
        "by_primary_bucket": {
            key: ordered(error_by_bucket[key]) for key in sorted(error_by_bucket)
        },
    }


def stage7g_e3_s0b_event_audit(
    rows: Iterable[Stage7GE3R2TrainingRow],
) -> dict:
    """Reconstruct final-epoch S0 OOF predictions and export event-level diagnostics.

    This development-only audit does not tune, select, retain, promote, or activate
    a model. Geometry attribution is descriptive and target-blind; it is not a
    causal Teacher-GOLD explanation or specialist supervision label.
    """
    _assert_contract()
    samples = tuple(rows)
    if len(samples) != STAGE7G_E3_R2_EXPECTED_DECISIVE:
        raise ValueError("S0-B requires exactly 399 decisive R2 development rows")
    if len({row.family_id for row in samples}) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise ValueError("S0-B requires exactly 40 R2 development families")

    X = np.asarray([row.features for row in samples], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in samples], dtype=np.int64)
    groups = np.asarray([row.family_id for row in samples], dtype=object)
    if X.shape != (STAGE7G_E3_R2_EXPECTED_DECISIVE, len(STAGE7G_E3_FEATURE_NAMES)):
        raise ValueError("S0-B feature matrix shape mismatch")
    if not np.isfinite(X).all():
        raise ValueError("S0-B feature matrix contains non-finite values")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("S0-B requires both Teacher-GOLD classes")

    cv = STAGE7G_E3_S0_CONFIG["outer_cv"]
    splitter = StratifiedGroupKFold(
        n_splits=cv["n_splits"],
        shuffle=cv["shuffle"],
        random_state=cv["random_state"],
    )
    splits = list(splitter.split(X, y, groups))
    if len(splits) != cv["n_splits"]:
        raise AssertionError("S0-B outer fold count mismatch")

    oof_probabilities = np.full(len(samples), np.nan, dtype=np.float64)
    oof_fold = np.full(len(samples), -1, dtype=np.int64)
    for fold_index, (train_idx, val_idx) in enumerate(splits):
        train_idx = np.asarray(train_idx, dtype=np.int64)
        val_idx = np.asarray(val_idx, dtype=np.int64)
        if set(str(v) for v in groups[train_idx]) & set(str(v) for v in groups[val_idx]):
            raise AssertionError("S0-B outer family leakage")
        if np.any(oof_fold[val_idx] != -1):
            raise AssertionError("S0-B OOF validation overlap")
        _, probabilities = _fit_fixed_epochs(
            X[train_idx],
            y[train_idx],
            X[val_idx],
            y[val_idx],
        )
        oof_probabilities[val_idx] = probabilities
        oof_fold[val_idx] = fold_index

    if not np.isfinite(oof_probabilities).all() or np.any(oof_fold < 0):
        raise AssertionError("S0-B OOF predictions must cover all 399 rows exactly once")

    event_rows = []
    for index, sample in enumerate(samples):
        probability = float(oof_probabilities[index])
        prediction = int(probability >= STAGE7G_E3_S0B_CONFIG["decision_threshold"])
        feature_views = _feature_views(sample.features)
        attribution = _axis_attribution(feature_views["compact_minus_open"])
        event_rows.append(
            {
                "event_id": sample.event_id,
                "family_id": sample.family_id,
                "curriculum_level": sample.curriculum_level,
                "outer_fold": int(oof_fold[index]),
                "teacher_target": "COMPACT" if sample.teacher_prefers_compact else "OPEN_LOW",
                "model_prediction": "COMPACT" if prediction else "OPEN_LOW",
                "compact_probability": probability,
                "error_type": _error_type(sample.teacher_prefers_compact, prediction),
                **feature_views,
                "attribution": attribution,
            }
        )

    metrics = _metrics(y, oof_probabilities)
    summary = _summary(event_rows)
    if summary["error_counts"] != {
        "TP": metrics["tp"],
        "FP": metrics["fp"],
        "FN": metrics["fn"],
        "TN": metrics["tn"],
    }:
        raise AssertionError("S0-B event rows do not reproduce aggregate confusion counts")

    event_rows_sorted = sorted(event_rows, key=lambda row: row["event_id"])
    event_id_digest = sha256(
        "\n".join(row["event_id"] for row in event_rows_sorted).encode("utf-8")
    ).hexdigest()

    return {
        "schema": STAGE7G_E3_S0B_SCHEMA,
        "status": "S0B_EVENT_AUDIT_COMPLETE_NO_ARCHITECTURE_DECISION",
        "config": STAGE7G_E3_S0B_CONFIG,
        "dataset": {
            "rows": len(samples),
            "families": len(set(groups)),
            "feature_count": X.shape[1],
            "event_id_set_sha256": event_id_digest,
        },
        "aggregate_oof": metrics,
        "summary": summary,
        "event_rows": event_rows_sorted,
        "interpretation_boundary": {
            "attribution_is_descriptive_not_causal": True,
            "no_new_teacher_specialist_labels_created": True,
            "specialist_architecture_status": "TARGET_ARCHITECTURE_CANDIDATE_ONLY",
            "specialist_architecture_activation_authorized": False,
            "no_threshold_or_hyperparameter_selected": True,
            "no_model_or_checkpoint_retained": True,
            "e3e_teacher_gold_used": False,
            "stage7e_used": False,
            "production_or_shadow_integration": False,
        },
    }
