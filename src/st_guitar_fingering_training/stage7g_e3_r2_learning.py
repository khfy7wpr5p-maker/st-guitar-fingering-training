from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Iterable, Mapping

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from .curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    stage7g_e3_curriculum_level,
    stage7g_e3_feature_record,
)
from .dataset import valid_chord_voicings
from .stage7g_e3_e_a3 import A3_STYLES, _event_id, _winner
from .target_free_musicxml import TargetFreeSource


STAGE7G_E3_R2_SCHEMA = "st-guitar-stage7g-e3-r2-learning-demo-v1"
STAGE7G_E3_R2_EXPECTED_TASKS = 400
STAGE7G_E3_R2_EXPECTED_DECISIVE = 399
STAGE7G_E3_R2_EXPECTED_FAMILIES = 40
STAGE7G_E3_R2_EXPECTED_DISAGREEMENTS = 5626
STAGE7G_E3_R2_EXPECTED_TASK_SET_SHA256 = "d7a45c08e5fd4bc2c4e8773f45ba1f54ab5d5794b7ca69877c8f8c7a2d4980f7"
STAGE7G_E3_R2_EXPECTED_MANIFEST_SHA256 = "433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2"
STAGE7G_E3_R2_EXPECTED_CHOICES_SHA256 = "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e"
STAGE7G_E3_R2_EXPECTED_DECODED = {"OPEN_LOW": 311, "COMPACT": 88, "EQUAL_OR_UNSURE": 1}
STAGE7G_E3_R2_EXPECTED_LEVEL_COUNTS = {"L1": 140, "L2": 120, "L3": 80, "L4": 60}
STAGE7G_E3_R2_FEATURE_LIST_SHA256 = "6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3"

# Frozen before the R2 Colab TRAIN cell is run. This is a development-only
# learning-curve demonstration, not a new untouched validation or promotion gate.
STAGE7G_E3_R2_CONFIG = {
    "split": {
        "method": "StratifiedGroupKFold",
        "n_splits": 5,
        "shuffle": True,
        "random_state": 20260815,
        "validation_fold": 0,
        "group_key": "family_id",
    },
    "scaler": "StandardScaler_fit_on_train_only",
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
    "checkpoint_retained": False,
    "e3e_teacher_gold_used": False,
    "stage7e_used": False,
    "production_integration": False,
}


@dataclass(frozen=True)
class Stage7GE3R2PoolRow:
    event_id: str
    family_id: str
    curriculum_level: str
    features: tuple[float, ...]


@dataclass(frozen=True)
class Stage7GE3R2TrainingRow:
    event_id: str
    family_id: str
    curriculum_level: str
    teacher_prefers_compact: int
    features: tuple[float, ...]


def feature_list_sha256() -> str:
    return sha256("\n".join(STAGE7G_E3_FEATURE_NAMES).encode("utf-8")).hexdigest()


def _development_blind_style_order(task_id: str) -> tuple[str, str]:
    digest = sha256((task_id + "|stage7g-e3-pairwise-v1").encode()).digest()
    return ("compact", "open_low") if digest[0] & 1 else ("open_low", "compact")


def build_stage7g_e3_r2_disagreement_pool(
    sources: Iterable[TargetFreeSource],
    *,
    specialist_models: Mapping[str, object],
) -> tuple[Stage7GE3R2PoolRow, ...]:
    """Rebuild the 40-family AnimeTAB open_low/compact disagreement feature pool.

    This function is label-free. It reads pitches/tuning only, keeps physical
    validity under valid_chord_voicings(), and computes the already-frozen 40
    target-blind ergonomics features.
    """
    if set(specialist_models) != set(A3_STYLES):
        raise ValueError("R2 requires exactly frozen open_low and compact specialists")
    source_rows = tuple(sources)
    if len(source_rows) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise ValueError("R2 requires exactly the sealed 40 AnimeTAB families")
    if len({source.family_id for source in source_rows}) != len(source_rows):
        raise ValueError("R2 source family ids must be unique")
    if len({source.source_sha256.lower() for source in source_rows}) != len(source_rows):
        raise ValueError("R2 source hashes must be unique")

    out: list[Stage7GE3R2PoolRow] = []
    seen: set[str] = set()
    for source in sorted(source_rows, key=lambda value: value.family_id):
        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            candidates = valid_chord_voicings(event.pitches_midi, event.tuning)
            if len(candidates) < 2:
                continue
            open_low = _winner(candidates, specialist_models["open_low"], "open_low")
            compact = _winner(candidates, specialist_models["compact"], "compact")
            if open_low == compact:
                continue
            event_id = _event_id(source, event, index)
            if event_id in seen:
                raise ValueError("duplicate R2 disagreement event id")
            seen.add(event_id)
            record = stage7g_e3_feature_record(
                event.pitches_midi,
                event.tuning,
                open_low,
                compact,
            )
            features = tuple(float(record[name]) for name in STAGE7G_E3_FEATURE_NAMES)
            if len(features) != 40 or not all(isfinite(value) for value in features):
                raise ValueError("R2 feature vector is non-finite or wrong-dimensional")
            geometry_delta = {
                name: record[f"compact_minus_open__{name}"]
                for name in STAGE7G_E3_GEOMETRY_NAMES
            }
            level = stage7g_e3_curriculum_level(
                chord_size=len(event.pitches_midi),
                candidate_count=len(candidates),
                geometry_delta=geometry_delta,
            )
            out.append(Stage7GE3R2PoolRow(
                event_id=event_id,
                family_id=source.family_id,
                curriculum_level=level,
                features=features,
            ))

    if len(out) != STAGE7G_E3_R2_EXPECTED_DISAGREEMENTS:
        raise AssertionError("R2 disagreement count drift from sealed AnimeTAB evidence")
    if len({row.family_id for row in out}) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise AssertionError("R2 disagreement family coverage drift")
    return tuple(out)


def rows_from_choices(
    pool: Iterable[Stage7GE3R2PoolRow],
    choices: Mapping[str, object],
) -> tuple[tuple[Stage7GE3R2TrainingRow, ...], dict]:
    """Join the exact 400 blinded development choices to label-free feature rows."""
    if feature_list_sha256() != STAGE7G_E3_R2_FEATURE_LIST_SHA256:
        raise AssertionError("R2 40-feature contract drift")
    pool_rows = tuple(pool)
    by_id = {row.event_id: row for row in pool_rows}
    if len(by_id) != len(pool_rows):
        raise ValueError("R2 pool contains duplicate event ids")

    if choices.get("schema") != "st-guitar-stage7g-e3-pairwise-choice-export-v1":
        raise ValueError("unexpected R2 Teacher-GOLD choices schema")
    if choices.get("annotation_blinded") is not True:
        raise ValueError("R2 choices must be blinded")
    if choices.get("manifest_sha256") != STAGE7G_E3_R2_EXPECTED_MANIFEST_SHA256:
        raise ValueError("R2 choices reference the wrong manifest")
    if choices.get("selected_count") != STAGE7G_E3_R2_EXPECTED_TASKS:
        raise ValueError("R2 selected_count mismatch")
    if choices.get("task_count") != STAGE7G_E3_R2_EXPECTED_TASKS:
        raise ValueError("R2 task_count mismatch")

    raw_choices = choices.get("choices")
    if not isinstance(raw_choices, list) or len(raw_choices) != STAGE7G_E3_R2_EXPECTED_TASKS:
        raise ValueError("R2 choices must contain exactly 400 rows")

    choice_by_id: dict[str, str] = {}
    for row in raw_choices:
        if not isinstance(row, dict):
            raise ValueError("R2 choice row must be an object")
        task_id = row.get("task_id")
        response = row.get("response")
        if not isinstance(task_id, str) or not task_id or task_id in choice_by_id:
            raise ValueError("R2 choice task id is invalid or duplicated")
        if response not in ("A", "B", "EQUAL_OR_UNSURE"):
            raise ValueError("R2 choice response is invalid")
        choice_by_id[task_id] = response

    task_ids = set(choice_by_id)
    digest = sha256("\n".join(sorted(task_ids)).encode("utf-8")).hexdigest()
    if digest != STAGE7G_E3_R2_EXPECTED_TASK_SET_SHA256:
        raise ValueError("R2 400-task set digest mismatch")
    if not task_ids.issubset(by_id):
        raise ValueError("R2 choices contain task ids outside the reconstructed disagreement pool")

    decoded = Counter()
    level_counts = Counter()
    rows: list[Stage7GE3R2TrainingRow] = []
    for task_id in sorted(task_ids):
        pool_row = by_id[task_id]
        response = choice_by_id[task_id]
        level_counts[pool_row.curriculum_level] += 1
        if response == "EQUAL_OR_UNSURE":
            decoded["EQUAL_OR_UNSURE"] += 1
            continue
        style_a, style_b = _development_blind_style_order(task_id)
        preferred_style = style_a if response == "A" else style_b
        target = int(preferred_style == "compact")
        decoded["COMPACT" if target else "OPEN_LOW"] += 1
        rows.append(Stage7GE3R2TrainingRow(
            event_id=task_id,
            family_id=pool_row.family_id,
            curriculum_level=pool_row.curriculum_level,
            teacher_prefers_compact=target,
            features=pool_row.features,
        ))

    if dict(decoded) != STAGE7G_E3_R2_EXPECTED_DECODED:
        raise ValueError("R2 decoded Teacher-GOLD counts mismatch")
    if dict(level_counts) != STAGE7G_E3_R2_EXPECTED_LEVEL_COUNTS:
        raise ValueError("R2 curriculum level counts mismatch")
    if len(rows) != STAGE7G_E3_R2_EXPECTED_DECISIVE:
        raise ValueError("R2 decisive row count mismatch")
    if len({row.family_id for row in rows}) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise ValueError("R2 decisive family count mismatch")

    preflight = {
        "status": "R2_PREFLIGHT_PASS_STOP_BEFORE_MANUAL_TRAIN",
        "schema": STAGE7G_E3_R2_SCHEMA,
        "tasks": STAGE7G_E3_R2_EXPECTED_TASKS,
        "decisive_rows": len(rows),
        "equal_or_unsure_excluded": decoded["EQUAL_OR_UNSURE"],
        "families": len({row.family_id for row in rows}),
        "decoded_teacher_preferences": dict(decoded),
        "curriculum_level_counts": dict(level_counts),
        "feature_count": len(STAGE7G_E3_FEATURE_NAMES),
        "feature_list_sha256": feature_list_sha256(),
        "task_id_set_sha256": digest,
        "e3e_teacher_gold_used": False,
        "stage7e_used": False,
        "checkpoint_retained": False,
        "production_integration": False,
    }
    return tuple(rows), preflight


def _metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict:
    predictions = (probabilities >= 0.5).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "loss": float(log_loss(y_true, np.column_stack([1.0 - probabilities, probabilities]), labels=[0, 1])),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "macro_f1": float(f1_score(y_true, predictions, average="macro", zero_division=0)),
        "compact_precision": float(precision_score(y_true, predictions, pos_label=1, zero_division=0)),
        "compact_recall": float(recall_score(y_true, predictions, pos_label=1, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def stage7g_e3_r2_learning_report(
    rows: Iterable[Stage7GE3R2TrainingRow],
) -> dict:
    """Run the frozen 60-epoch family-isolated R2 learning demonstration.

    No E3-E labels are accepted by this API. No early stopping, best-epoch model
    selection, checkpoint serialization, or production promotion occurs.
    """
    samples = tuple(rows)
    if len(samples) != STAGE7G_E3_R2_EXPECTED_DECISIVE:
        raise ValueError("R2 requires exactly 399 decisive development rows")
    if len({row.family_id for row in samples}) != STAGE7G_E3_R2_EXPECTED_FAMILIES:
        raise ValueError("R2 requires exactly 40 development families")

    X = np.asarray([row.features for row in samples], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in samples], dtype=np.int64)
    groups = np.asarray([row.family_id for row in samples], dtype=object)
    if X.shape != (STAGE7G_E3_R2_EXPECTED_DECISIVE, 40) or not np.isfinite(X).all():
        raise ValueError("R2 training matrix is non-finite or wrong-dimensional")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("R2 requires both OPEN_LOW and COMPACT classes")

    split_cfg = STAGE7G_E3_R2_CONFIG["split"]
    splitter = StratifiedGroupKFold(
        n_splits=split_cfg["n_splits"],
        shuffle=split_cfg["shuffle"],
        random_state=split_cfg["random_state"],
    )
    splits = list(splitter.split(X, y, groups))
    train_idx, val_idx = splits[split_cfg["validation_fold"]]
    train_families = set(groups[train_idx])
    val_families = set(groups[val_idx])
    if train_families & val_families:
        raise AssertionError("R2 train/validation family leakage")
    if set(np.unique(y[train_idx])) != {0, 1} or set(np.unique(y[val_idx])) != {0, 1}:
        raise ValueError("R2 train/validation split must contain both classes")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[train_idx])
    X_val = scaler.transform(X[val_idx])
    y_train = y[train_idx]
    y_val = y[val_idx]

    model_cfg = STAGE7G_E3_R2_CONFIG["model"]
    model = MLPClassifier(
        hidden_layer_sizes=tuple(model_cfg["hidden_layer_sizes"]),
        activation=model_cfg["activation"],
        solver=model_cfg["solver"],
        alpha=model_cfg["alpha"],
        batch_size=model_cfg["batch_size"],
        learning_rate_init=model_cfg["learning_rate_init"],
        random_state=model_cfg["random_state"],
        max_iter=1,
        shuffle=True,
    )

    history: list[dict] = []
    for epoch in range(1, model_cfg["epochs"] + 1):
        model.partial_fit(X_train, y_train, classes=np.asarray([0, 1], dtype=np.int64))
        train_p = np.asarray(model.predict_proba(X_train)[:, 1], dtype=np.float64)
        val_p = np.asarray(model.predict_proba(X_val)[:, 1], dtype=np.float64)
        train_metrics = _metrics(y_train, train_p)
        val_metrics = _metrics(y_val, val_p)
        history.append({
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "val_loss": val_metrics["loss"],
            "train_macro_f1": train_metrics["macro_f1"],
            "val_macro_f1": val_metrics["macro_f1"],
            "val_accuracy": val_metrics["accuracy"],
            "val_balanced_accuracy": val_metrics["balanced_accuracy"],
            "val_compact_precision": val_metrics["compact_precision"],
            "val_compact_recall": val_metrics["compact_recall"],
        })

    baseline_predictions = np.zeros_like(y_val)
    baseline = {
        "always_open_low_accuracy": float(accuracy_score(y_val, baseline_predictions)),
        "always_open_low_macro_f1": float(f1_score(y_val, baseline_predictions, average="macro", zero_division=0)),
        "always_open_low_balanced_accuracy": float(balanced_accuracy_score(y_val, baseline_predictions)),
    }
    final_p = np.asarray(model.predict_proba(X_val)[:, 1], dtype=np.float64)
    final = _metrics(y_val, final_p)
    final.update({
        "macro_f1_gain_vs_always_open_low": final["macro_f1"] - baseline["always_open_low_macro_f1"],
        "accuracy_gain_vs_always_open_low": final["accuracy"] - baseline["always_open_low_accuracy"],
        "val_loss_change_epoch1_to_final": history[-1]["val_loss"] - history[0]["val_loss"],
    })

    return {
        "schema": STAGE7G_E3_R2_SCHEMA,
        "status": "R2_DEVELOPMENT_LEARNING_DEMO_COMPLETE_NO_PROMOTION_CLAIM",
        "config": STAGE7G_E3_R2_CONFIG,
        "split": {
            "train_rows": int(len(train_idx)),
            "validation_rows": int(len(val_idx)),
            "train_families": len(train_families),
            "validation_families": len(val_families),
            "family_overlap": 0,
            "train_class_counts": {"OPEN_LOW": int(np.sum(y_train == 0)), "COMPACT": int(np.sum(y_train == 1))},
            "validation_class_counts": {"OPEN_LOW": int(np.sum(y_val == 0)), "COMPACT": int(np.sum(y_val == 1))},
        },
        "baseline": baseline,
        "history": history,
        "final_validation": final,
        "pixel_localization_metric": {
            "LocF1@2px": None,
            "reason": "not_applicable_this_model_predicts_guitaristic_class_preference_not_pixel_locations",
        },
        "scientific_boundary": {
            "development_only": True,
            "e3e_teacher_gold_used": False,
            "stage7e_used": False,
            "early_stopping": False,
            "best_epoch_checkpoint_selected": False,
            "checkpoint_retained": False,
            "production_integration": False,
        },
    }
