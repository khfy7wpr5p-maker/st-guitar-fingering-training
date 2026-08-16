from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from typing import Iterable

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from .curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS,
)
from .stage7g_e3_r2_learning import (
    STAGE7G_E3_R2_CONFIG,
    STAGE7G_E3_R2_EXPECTED_DECISIVE,
    STAGE7G_E3_R2_EXPECTED_FAMILIES,
    Stage7GE3R2TrainingRow,
)

STAGE7G_E3_S0_SCHEMA = "st-guitar-stage7g-e3-s0-failure-diagnostic-v1"

STAGE7G_E3_S0_CONFIG = {
    "purpose": "diagnose_why_r2_failed_without_model_selection_or_promotion",
    "outer_cv": {
        "method": "StratifiedGroupKFold",
        "n_splits": 5,
        "shuffle": True,
        "random_state": 20260815,
        "group_key": "family_id",
        "all_folds_evaluated": True,
    },
    "model": {
        "type": "MLPClassifier",
        "hidden_layer_sizes": [32, 16],
        "activation": "relu",
        "solver": "adam",
        "alpha": 0.0001,
        "batch_size": 32,
        "learning_rate_init": 0.001,
        "random_state": 20260815,
        "epochs": 60,
        "positive_class": "COMPACT",
        "decision_threshold": 0.5,
    },
    "learning_curve": {
        "fractions": [0.25, 0.50, 0.75, 1.00],
        "inner_family_partitions": 4,
        "partition_method": "StratifiedGroupKFold",
        "shuffle": True,
        "random_state_base": 20260816,
        "selection": "cumulative_inner_validation_partitions_in_declared_order",
        "epoch_count_fixed": 60,
    },
    "cluster_bootstrap": {
        "unit": "family_id",
        "draws": 2000,
        "random_state": 20260816,
        "confidence": 0.95,
    },
    "diagnostic_flags": {
        "compact_support_thin_if_min_outer_compact_support_lt": 20,
        "recurrent_overfit_if_at_least_folds": 3,
        "recurrent_overfit_min_final_minus_min_val_loss": 0.02,
        "high_fold_variance_if_macro_f1_range_gte": 0.10,
        "learning_curve_still_rising_if_macro_f1_gain_75_to_100_gte": 0.03,
    },
    "forbidden": {
        "scheduler": True,
        "threshold_search": True,
        "hyperparameter_search": True,
        "new_features": True,
        "specialist_training": True,
        "early_stopping": True,
        "best_epoch_checkpoint_selection": True,
        "e3e_teacher_gold": True,
        "stage7e": True,
        "checkpoint_retention": True,
        "production_or_shadow_integration": True,
    },
}


def _assert_contract() -> None:
    r2 = STAGE7G_E3_R2_CONFIG
    if r2["split"]["method"] != STAGE7G_E3_S0_CONFIG["outer_cv"]["method"]:
        raise AssertionError("S0 outer split method drift from R2")
    for key in ("n_splits", "shuffle", "random_state", "group_key"):
        if r2["split"][key] != STAGE7G_E3_S0_CONFIG["outer_cv"][key]:
            raise AssertionError(f"S0 outer split {key} drift from R2")
    if r2["model"] != STAGE7G_E3_S0_CONFIG["model"]:
        raise AssertionError("S0 model drift from frozen R2 model")


def _metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=np.int64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if y_true.ndim != 1 or probabilities.shape != y_true.shape:
        raise ValueError("metric arrays must be one-dimensional and aligned")
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise ValueError("probabilities must be finite and within [0, 1]")
    predictions = (probabilities >= 0.5).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    open_support = int(np.sum(y_true == 0))
    compact_support = int(np.sum(y_true == 1))
    both_classes = open_support > 0 and compact_support > 0
    predicted_compact = int(np.sum(predictions == 1))
    return {
        "support": int(len(y_true)),
        "open_low_support": open_support,
        "compact_support": compact_support,
        "accuracy": float(accuracy_score(y_true, predictions)),
        "macro_f1": float(f1_score(y_true, predictions, labels=[0, 1], average="macro", zero_division=0)),
        "balanced_accuracy": (
            float(balanced_accuracy_score(y_true, predictions)) if both_classes else None
        ),
        "compact_precision": (
            float(precision_score(y_true, predictions, pos_label=1, zero_division=0))
            if predicted_compact > 0
            else 0.0
        ),
        "compact_recall": (
            float(recall_score(y_true, predictions, pos_label=1, zero_division=0))
            if compact_support > 0
            else None
        ),
        "log_loss": float(
            log_loss(
                y_true,
                np.column_stack([1.0 - probabilities, probabilities]),
                labels=[0, 1],
            )
        ),
        "average_precision": (
            float(average_precision_score(y_true, probabilities))
            if compact_support > 0
            else None
        ),
        "roc_auc": float(roc_auc_score(y_true, probabilities)) if both_classes else None,
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "mcc": float(matthews_corrcoef(y_true, predictions)) if both_classes else None,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


def _new_model() -> MLPClassifier:
    cfg = STAGE7G_E3_S0_CONFIG["model"]
    return MLPClassifier(
        hidden_layer_sizes=tuple(cfg["hidden_layer_sizes"]),
        activation=cfg["activation"],
        solver=cfg["solver"],
        alpha=cfg["alpha"],
        batch_size=cfg["batch_size"],
        learning_rate_init=cfg["learning_rate_init"],
        random_state=cfg["random_state"],
        max_iter=1,
        shuffle=True,
    )


def _fit_fixed_epochs(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[list[dict], np.ndarray]:
    if set(np.unique(y_train)) != {0, 1}:
        raise ValueError("S0 train split must contain both classes")
    if set(np.unique(y_val)) != {0, 1}:
        raise ValueError("S0 validation split must contain both classes")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    model = _new_model()
    history: list[dict] = []
    epochs = STAGE7G_E3_S0_CONFIG["model"]["epochs"]
    final_probabilities: np.ndarray | None = None
    for epoch in range(1, epochs + 1):
        model.partial_fit(
            X_train_scaled,
            y_train,
            classes=np.asarray([0, 1], dtype=np.int64),
        )
        train_p = np.asarray(model.predict_proba(X_train_scaled)[:, 1], dtype=np.float64)
        val_p = np.asarray(model.predict_proba(X_val_scaled)[:, 1], dtype=np.float64)
        train_m = _metrics(y_train, train_p)
        val_m = _metrics(y_val, val_p)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_m["log_loss"],
                "val_loss": val_m["log_loss"],
                "train_macro_f1": train_m["macro_f1"],
                "val_macro_f1": val_m["macro_f1"],
                "val_balanced_accuracy": val_m["balanced_accuracy"],
                "val_compact_precision": val_m["compact_precision"],
                "val_compact_recall": val_m["compact_recall"],
            }
        )
        final_probabilities = val_p
    if final_probabilities is None:
        raise AssertionError("S0 fixed-epoch fit produced no probabilities")
    return history, final_probabilities


def _breakdown(
    keys: Iterable[str],
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> list[dict]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(keys):
        buckets[str(key)].append(index)
    out = []
    for key in sorted(buckets):
        idx = np.asarray(buckets[key], dtype=np.int64)
        out.append({"key": key, **_metrics(y_true[idx], probabilities[idx])})
    return out


def _feature_regime_breakdown(
    X: np.ndarray,
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> list[dict]:
    feature_index = {name: i for i, name in enumerate(STAGE7G_E3_FEATURE_NAMES)}
    rows = []
    for geometry_name, threshold in STAGE7G_E3_STRONG_CONTRAST_THRESHOLDS.items():
        feature_name = f"compact_minus_open__{geometry_name}"
        if feature_name not in feature_index:
            raise AssertionError(f"missing frozen S0 diagnostic feature: {feature_name}")
        values = X[:, feature_index[feature_name]]
        masks = {
            "compact_higher_by_threshold": values >= float(threshold),
            "open_low_higher_by_threshold": values <= -float(threshold),
            "weak_contrast": np.abs(values) < float(threshold),
        }
        strata = []
        for stratum, mask in masks.items():
            idx = np.flatnonzero(mask)
            if len(idx) == 0:
                strata.append({"stratum": stratum, "support": 0})
            else:
                strata.append({"stratum": stratum, **_metrics(y_true[idx], probabilities[idx])})
        rows.append(
            {
                "feature": feature_name,
                "threshold": float(threshold),
                "semantics": "descriptive_geometry_stratum_not_preference_rule",
                "strata": strata,
            }
        )
    return rows


def _family_bootstrap_ci(
    family_ids: np.ndarray,
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> dict:
    cfg = STAGE7G_E3_S0_CONFIG["cluster_bootstrap"]
    unique_families = np.asarray(sorted(set(str(value) for value in family_ids)), dtype=object)
    family_to_indices = {
        family: np.flatnonzero(family_ids == family)
        for family in unique_families
    }
    rng = np.random.default_rng(cfg["random_state"])
    tracked = (
        "accuracy",
        "macro_f1",
        "balanced_accuracy",
        "compact_precision",
        "compact_recall",
        "average_precision",
        "roc_auc",
    )
    samples = {name: [] for name in tracked}
    accepted = 0
    for _ in range(cfg["draws"]):
        selected = rng.choice(unique_families, size=len(unique_families), replace=True)
        idx = np.concatenate([family_to_indices[str(family)] for family in selected])
        metrics = _metrics(y_true[idx], probabilities[idx])
        accepted += 1
        for name in tracked:
            value = metrics[name]
            if value is not None:
                samples[name].append(float(value))
    alpha = 1.0 - cfg["confidence"]
    point = _metrics(y_true, probabilities)
    out = {}
    for name in tracked:
        values = np.asarray(samples[name], dtype=np.float64)
        out[name] = {
            "point_estimate": point[name],
            "lower": float(np.quantile(values, alpha / 2.0)) if len(values) else None,
            "upper": float(np.quantile(values, 1.0 - alpha / 2.0)) if len(values) else None,
            "accepted_draws": int(len(values)),
        }
    return {
        "unit": cfg["unit"],
        "requested_draws": cfg["draws"],
        "accepted_resamples": accepted,
        "confidence": cfg["confidence"],
        "random_state": cfg["random_state"],
        "intervals": out,
    }


def _inner_partitions(
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups_train: np.ndarray,
    outer_fold_index: int,
) -> list[np.ndarray]:
    cfg = STAGE7G_E3_S0_CONFIG["learning_curve"]
    splitter = StratifiedGroupKFold(
        n_splits=cfg["inner_family_partitions"],
        shuffle=cfg["shuffle"],
        random_state=cfg["random_state_base"] + outer_fold_index,
    )
    partitions = []
    covered = np.zeros(len(y_train), dtype=np.int64)
    for _, test_idx in splitter.split(X_train, y_train, groups_train):
        test_idx = np.asarray(test_idx, dtype=np.int64)
        partitions.append(test_idx)
        covered[test_idx] += 1
    if len(partitions) != cfg["inner_family_partitions"] or not np.all(covered == 1):
        raise AssertionError("S0 learning-curve family partitions must cover train rows exactly once")
    return partitions


def stage7g_e3_s0_diagnostic_report(
    rows: Iterable[Stage7GE3R2TrainingRow],
) -> dict:
    """Diagnose R2 with all five family-isolated folds and no model selection.

    This is development-only. Final-epoch OOF predictions are used for diagnostic
    summaries. Minimum validation loss is reported descriptively only; it never
    selects or retains a checkpoint.
    """
    _assert_contract()
    samples = tuple(rows)
    if len(samples) != STAGE7G_E3_R2_EXPECTED_DECISIVE:
        raise ValueError("S0 requires exactly 399 decisive R2 development rows")
    if len({row.family_id for row in samples}) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise ValueError("S0 requires exactly 40 R2 development families")

    X = np.asarray([row.features for row in samples], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in samples], dtype=np.int64)
    groups = np.asarray([row.family_id for row in samples], dtype=object)
    levels = np.asarray([row.curriculum_level for row in samples], dtype=object)
    if X.shape != (STAGE7G_E3_R2_EXPECTED_DECISIVE, len(STAGE7G_E3_FEATURE_NAMES)):
        raise ValueError("S0 feature matrix shape mismatch")
    if not np.isfinite(X).all():
        raise ValueError("S0 feature matrix contains non-finite values")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("S0 requires both Teacher-GOLD classes")

    cv = STAGE7G_E3_S0_CONFIG["outer_cv"]
    splitter = StratifiedGroupKFold(
        n_splits=cv["n_splits"],
        shuffle=cv["shuffle"],
        random_state=cv["random_state"],
    )
    splits = list(splitter.split(X, y, groups))
    if len(splits) != cv["n_splits"]:
        raise AssertionError("S0 outer fold count mismatch")

    oof_probabilities = np.full(len(samples), np.nan, dtype=np.float64)
    oof_fold = np.full(len(samples), -1, dtype=np.int64)
    fold_reports = []
    learning_curve_oof = {
        float(fraction): np.full(len(samples), np.nan, dtype=np.float64)
        for fraction in STAGE7G_E3_S0_CONFIG["learning_curve"]["fractions"]
    }
    learning_curve_fold_rows: dict[float, list[dict]] = {
        float(fraction): []
        for fraction in STAGE7G_E3_S0_CONFIG["learning_curve"]["fractions"]
    }

    for fold_index, (train_idx, val_idx) in enumerate(splits):
        train_idx = np.asarray(train_idx, dtype=np.int64)
        val_idx = np.asarray(val_idx, dtype=np.int64)
        train_families = set(str(value) for value in groups[train_idx])
        val_families = set(str(value) for value in groups[val_idx])
        if train_families & val_families:
            raise AssertionError("S0 outer family leakage")
        if np.any(oof_fold[val_idx] != -1):
            raise AssertionError("S0 OOF validation overlap")

        history, final_p = _fit_fixed_epochs(
            X[train_idx],
            y[train_idx],
            X[val_idx],
            y[val_idx],
        )
        oof_probabilities[val_idx] = final_p
        oof_fold[val_idx] = fold_index

        min_record = min(history, key=lambda item: (item["val_loss"], item["epoch"]))
        final_metrics = _metrics(y[val_idx], final_p)
        fold_reports.append(
            {
                "fold": fold_index,
                "train_rows": int(len(train_idx)),
                "validation_rows": int(len(val_idx)),
                "train_families": len(train_families),
                "validation_families": len(val_families),
                "family_overlap": 0,
                "train_open_low_support": int(np.sum(y[train_idx] == 0)),
                "train_compact_support": int(np.sum(y[train_idx] == 1)),
                "validation_open_low_support": int(np.sum(y[val_idx] == 0)),
                "validation_compact_support": int(np.sum(y[val_idx] == 1)),
                "history": history,
                "minimum_val_loss": {
                    "epoch": int(min_record["epoch"]),
                    "value": float(min_record["val_loss"]),
                    "descriptive_only_no_checkpoint_selection": True,
                },
                "final_epoch": {
                    **final_metrics,
                    "final_minus_min_val_loss": float(
                        final_metrics["log_loss"] - min_record["val_loss"]
                    ),
                },
            }
        )

        partitions = _inner_partitions(
            X[train_idx],
            y[train_idx],
            groups[train_idx],
            fold_index,
        )
        fractions = STAGE7G_E3_S0_CONFIG["learning_curve"]["fractions"]
        for fraction in fractions:
            fraction = float(fraction)
            partition_count = int(round(fraction * len(partitions)))
            if partition_count < 1 or partition_count > len(partitions):
                raise AssertionError("S0 learning-curve partition count out of range")
            if fraction == 1.0:
                curve_p = final_p.copy()
                selected_local = np.arange(len(train_idx), dtype=np.int64)
            else:
                selected_local = np.unique(
                    np.concatenate(partitions[:partition_count])
                ).astype(np.int64)
                if set(np.unique(y[train_idx][selected_local])) != {0, 1}:
                    raise ValueError("S0 learning-curve subset lacks one class")
                _, curve_p = _fit_fixed_epochs(
                    X[train_idx][selected_local],
                    y[train_idx][selected_local],
                    X[val_idx],
                    y[val_idx],
                )
            learning_curve_oof[fraction][val_idx] = curve_p
            selected_families = set(str(value) for value in groups[train_idx][selected_local])
            learning_curve_fold_rows[fraction].append(
                {
                    "fold": fold_index,
                    "target_fraction": fraction,
                    "train_rows": int(len(selected_local)),
                    "train_families": len(selected_families),
                    "validation_rows": int(len(val_idx)),
                    **_metrics(y[val_idx], curve_p),
                }
            )

    if not np.isfinite(oof_probabilities).all() or np.any(oof_fold < 0):
        raise AssertionError("S0 OOF predictions must cover all 399 rows exactly once")

    oof_metrics = _metrics(y, oof_probabilities)
    family_breakdown = _breakdown(groups, y, oof_probabilities)
    level_breakdown = _breakdown(levels, y, oof_probabilities)
    regime_breakdown = _feature_regime_breakdown(X, y, oof_probabilities)
    bootstrap = _family_bootstrap_ci(groups, y, oof_probabilities)

    learning_curve = []
    for fraction in STAGE7G_E3_S0_CONFIG["learning_curve"]["fractions"]:
        fraction = float(fraction)
        probabilities = learning_curve_oof[fraction]
        if not np.isfinite(probabilities).all():
            raise AssertionError("S0 learning-curve OOF coverage incomplete")
        learning_curve.append(
            {
                "target_fraction": fraction,
                "oof_metrics": _metrics(y, probabilities),
                "folds": learning_curve_fold_rows[fraction],
            }
        )

    flags_cfg = STAGE7G_E3_S0_CONFIG["diagnostic_flags"]
    overfit_fold_count = sum(
        fold["final_epoch"]["final_minus_min_val_loss"]
        >= flags_cfg["recurrent_overfit_min_final_minus_min_val_loss"]
        for fold in fold_reports
    )
    fold_macro = [fold["final_epoch"]["macro_f1"] for fold in fold_reports]
    lc75 = next(row for row in learning_curve if row["target_fraction"] == 0.75)
    lc100 = next(row for row in learning_curve if row["target_fraction"] == 1.0)
    compact_supports = [fold["validation_compact_support"] for fold in fold_reports]
    diagnostic_flags = {
        "compact_support_thin": (
            min(compact_supports)
            < flags_cfg["compact_support_thin_if_min_outer_compact_support_lt"]
        ),
        "recurrent_overfit": (
            overfit_fold_count
            >= flags_cfg["recurrent_overfit_if_at_least_folds"]
        ),
        "recurrent_overfit_fold_count": int(overfit_fold_count),
        "high_fold_variance": (
            max(fold_macro) - min(fold_macro)
            >= flags_cfg["high_fold_variance_if_macro_f1_range_gte"]
        ),
        "fold_macro_f1_range": float(max(fold_macro) - min(fold_macro)),
        "learning_curve_still_rising_75_to_100": (
            lc100["oof_metrics"]["macro_f1"] - lc75["oof_metrics"]["macro_f1"]
            >= flags_cfg["learning_curve_still_rising_if_macro_f1_gain_75_to_100_gte"]
        ),
        "learning_curve_macro_f1_gain_75_to_100": float(
            lc100["oof_metrics"]["macro_f1"] - lc75["oof_metrics"]["macro_f1"]
        ),
        "teacher_repeat_reliability_measured": False,
        "specialist_architecture_activation_authorized": False,
        "causal_failure_reason_claimed": False,
    }

    return {
        "schema": STAGE7G_E3_S0_SCHEMA,
        "status": "S0_DIAGNOSTIC_COMPLETE_NO_ARCHITECTURE_DECISION",
        "config": STAGE7G_E3_S0_CONFIG,
        "dataset": {
            "rows": len(samples),
            "families": len(set(groups)),
            "open_low": int(np.sum(y == 0)),
            "compact": int(np.sum(y == 1)),
            "feature_count": X.shape[1],
            "feature_list_sha256": sha256(
                "\n".join(STAGE7G_E3_FEATURE_NAMES).encode("utf-8")
            ).hexdigest(),
        },
        "outer_folds": fold_reports,
        "oof_final_epoch": oof_metrics,
        "family_cluster_bootstrap_95ci": bootstrap,
        "family_breakdown": family_breakdown,
        "curriculum_level_breakdown": level_breakdown,
        "feature_regime_breakdown": regime_breakdown,
        "learning_curve": learning_curve,
        "diagnostic_flags": diagnostic_flags,
        "interpretation_boundary": {
            "specialist_architecture_status": "TARGET_ARCHITECTURE_CANDIDATE_ONLY",
            "this_report_may_support_but_cannot_by_itself_prove_causality": True,
            "teacher_repeat_reliability_requires_new_blind_repeat_batch": True,
            "minimum_val_loss_is_descriptive_only": True,
            "no_threshold_or_epoch_selected_from_s0": True,
            "no_model_or_checkpoint_retained": True,
            "e3e_teacher_gold_used": False,
            "stage7e_used": False,
            "production_or_shadow_integration": False,
        },
    }
