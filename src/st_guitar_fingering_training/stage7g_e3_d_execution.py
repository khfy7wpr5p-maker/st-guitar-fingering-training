from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Iterable
from zipfile import BadZipFile, ZipFile

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .curriculum_contract import STAGE7G_E3_FEATURE_NAMES
from .curriculum_generator import (
    STAGE7G_E3_INTERNAL_AUDIT_SCHEMA,
    STAGE7G_E3_TEACHER_MANIFEST_SCHEMA,
)


STAGE7G_E3_D_EXECUTION_SCHEMA = "st-guitar-stage7g-e3-d-r1-execution-v1"
STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256 = "e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef"
STAGE7G_E3_D_EXPECTED_AUDIT_SHA256 = "e8fa34998a409a275d372ae089b9a3f3ed1ea5b53de5c15e58a61de0210a2915"
STAGE7G_E3_D_EXPECTED_MANIFEST_SHA256 = "433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2"
STAGE7G_E3_D_EXPECTED_CHOICES_SHA256 = "db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e"
STAGE7G_E3_D_EXPECTED_FEATURE_LIST_SHA256 = "6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3"
STAGE7G_E3_D_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
STAGE7G_E3_D_OUTER_SPLITS = 5
STAGE7G_E3_D_INNER_SPLITS = 4
STAGE7G_E3_D_OUTER_RANDOM_STATE = 731
# Frozen execution clarification made before any E3-D result is observed:
# protocol `outer_fold_index` means zero-based Python index 0..4.
STAGE7G_E3_D_INNER_RANDOM_STATE_BASE = 7310
STAGE7G_E3_D_EXPECTED_LEVEL_COUNTS = {"L1": 140, "L2": 120, "L3": 80, "L4": 60}
STAGE7G_E3_D_EXPECTED_DECODED_COUNTS = {"OPEN_LOW": 311, "COMPACT": 88, "EQUAL_OR_UNSURE": 1}
STAGE7G_E3_D_EXPECTED_TASKS = 400
STAGE7G_E3_D_EXPECTED_FAMILIES = 40
STAGE7G_E3_D_EXPECTED_DECISIVE = 399
_MAX_ZIP_MEMBERS = 32
_MAX_JSON_MEMBER_BYTES = 32 * 1024 * 1024
_MAX_TOTAL_JSON_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class Stage7GE3DRow:
    family_id: str
    event_id: str
    curriculum_level: str
    teacher_prefers_compact: int
    features: tuple[float, ...]


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def feature_list_sha256() -> str:
    return _sha256_bytes("\n".join(STAGE7G_E3_FEATURE_NAMES).encode("utf-8"))


def _json_object(data: bytes, *, label: str) -> dict:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def read_stage7g_e3_package_json(zip_path: str | Path) -> tuple[dict, dict]:
    """Read the sealed package in memory; never extract archive members to disk."""
    zip_path = Path(zip_path)
    if sha256_file(zip_path) != STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256:
        raise ValueError("Stage 7G-E3-D outer package SHA-256 mismatch")
    schemas: dict[str, tuple[dict, str]] = {}
    total_json_bytes = 0
    try:
        with ZipFile(zip_path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_ZIP_MEMBERS:
                raise ValueError("Stage 7G-E3-D package has too many members")
            for info in infos:
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                if info.file_size < 1 or info.file_size > _MAX_JSON_MEMBER_BYTES:
                    raise ValueError("Stage 7G-E3-D JSON member size is outside the allowed bound")
                total_json_bytes += info.file_size
                if total_json_bytes > _MAX_TOTAL_JSON_BYTES:
                    raise ValueError("Stage 7G-E3-D package JSON payload exceeds the allowed bound")
                data = archive.read(info)
                if len(data) != info.file_size:
                    raise ValueError("Stage 7G-E3-D package member size mismatch")
                obj = _json_object(data, label=info.filename)
                schema = obj.get("schema")
                if schema in (STAGE7G_E3_INTERNAL_AUDIT_SCHEMA, STAGE7G_E3_TEACHER_MANIFEST_SCHEMA):
                    if schema in schemas:
                        raise ValueError(f"duplicate Stage 7G-E3 package schema: {schema}")
                    schemas[schema] = (obj, _sha256_bytes(data))
    except (BadZipFile, RuntimeError) as exc:
        raise ValueError("Stage 7G-E3-D curriculum package is not readable as a plain ZIP") from exc
    if set(schemas) != {STAGE7G_E3_INTERNAL_AUDIT_SCHEMA, STAGE7G_E3_TEACHER_MANIFEST_SCHEMA}:
        raise ValueError("Stage 7G-E3-D package is missing the frozen audit or teacher manifest")
    audit, audit_sha = schemas[STAGE7G_E3_INTERNAL_AUDIT_SCHEMA]
    manifest, manifest_sha = schemas[STAGE7G_E3_TEACHER_MANIFEST_SCHEMA]
    if audit_sha != STAGE7G_E3_D_EXPECTED_AUDIT_SHA256:
        raise ValueError("Stage 7G-E3-D internal audit SHA-256 mismatch")
    if manifest_sha != STAGE7G_E3_D_EXPECTED_MANIFEST_SHA256:
        raise ValueError("Stage 7G-E3-D teacher manifest SHA-256 mismatch")
    return audit, manifest


def _placement_tuple(rows: object) -> tuple[tuple[int, int, int], ...]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("proposal placements must be a non-empty list")
    out = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("proposal placement must be an object")
        out.append((int(row["pitch_midi"]), int(row["string"]), int(row["fret"])))
    return tuple(sorted(out))


def load_stage7g_e3_d_rows(package_zip_path: str | Path, choices_path: str | Path) -> tuple[tuple[Stage7GE3DRow, ...], dict]:
    """Verify the frozen external inputs and construct only the 399 decisive rows."""
    if feature_list_sha256() != STAGE7G_E3_D_EXPECTED_FEATURE_LIST_SHA256:
        raise AssertionError("Stage 7G-E3-D feature-list contract drift")
    if sha256_file(choices_path) != STAGE7G_E3_D_EXPECTED_CHOICES_SHA256:
        raise ValueError("Stage 7G-E3-D Teacher-GOLD choices SHA-256 mismatch")
    audit, manifest = read_stage7g_e3_package_json(package_zip_path)
    choices = _json_object(Path(choices_path).read_bytes(), label="Teacher-GOLD choices")
    if choices.get("schema") != "st-guitar-stage7g-e3-pairwise-choice-export-v1":
        raise ValueError("unexpected Stage 7G-E3-D Teacher-GOLD choice schema")
    if choices.get("annotation_blinded") is not True:
        raise ValueError("Stage 7G-E3-D Teacher-GOLD choices must be blinded")
    if choices.get("manifest_sha256") != STAGE7G_E3_D_EXPECTED_MANIFEST_SHA256:
        raise ValueError("Stage 7G-E3-D choices reference the wrong teacher manifest")
    if choices.get("selected_count") != STAGE7G_E3_D_EXPECTED_TASKS or choices.get("task_count") != STAGE7G_E3_D_EXPECTED_TASKS:
        raise ValueError("Stage 7G-E3-D choices count mismatch")
    manifest_tasks = manifest.get("tasks")
    if manifest.get("task_count") != STAGE7G_E3_D_EXPECTED_TASKS or not isinstance(manifest_tasks, list) or len(manifest_tasks) != STAGE7G_E3_D_EXPECTED_TASKS:
        raise ValueError("Stage 7G-E3-D manifest task count mismatch")
    if audit.get("selected_events") != STAGE7G_E3_D_EXPECTED_TASKS:
        raise ValueError("Stage 7G-E3-D audit selected_events mismatch")
    if audit.get("teacher_response_used_for_generation") is not False or audit.get("observed_string_fret_used_for_generation") is not False:
        raise ValueError("Stage 7G-E3-D audit must remain target-free")
    if audit.get("feature_names") != list(STAGE7G_E3_FEATURE_NAMES) or audit.get("feature_count") != len(STAGE7G_E3_FEATURE_NAMES):
        raise ValueError("Stage 7G-E3-D audit feature contract mismatch")
    if audit.get("level_counts") != STAGE7G_E3_D_EXPECTED_LEVEL_COUNTS:
        raise ValueError("Stage 7G-E3-D audit curriculum level counts mismatch")
    audit_rows = audit.get("rows")
    if not isinstance(audit_rows, list) or len(audit_rows) != STAGE7G_E3_D_EXPECTED_TASKS:
        raise ValueError("Stage 7G-E3-D audit rows mismatch")
    audit_by_id = {row.get("event_id"): row for row in audit_rows if isinstance(row, dict)}
    manifest_by_id = {row.get("task_id"): row for row in manifest_tasks if isinstance(row, dict)}
    if len(audit_by_id) != STAGE7G_E3_D_EXPECTED_TASKS or len(manifest_by_id) != STAGE7G_E3_D_EXPECTED_TASKS or None in audit_by_id or None in manifest_by_id:
        raise ValueError("Stage 7G-E3-D sealed task ids must be unique and present")
    choice_rows = choices.get("choices")
    if not isinstance(choice_rows, list) or len(choice_rows) != STAGE7G_E3_D_EXPECTED_TASKS:
        raise ValueError("Stage 7G-E3-D choice rows mismatch")
    choice_by_id: dict[str, str] = {}
    for row in choice_rows:
        if not isinstance(row, dict):
            raise ValueError("Stage 7G-E3-D choice row must be an object")
        task_id, response = row.get("task_id"), row.get("response")
        if not isinstance(task_id, str) or response not in ("A", "B", "EQUAL_OR_UNSURE") or task_id in choice_by_id:
            raise ValueError("Stage 7G-E3-D choice row is invalid or duplicated")
        choice_by_id[task_id] = response
    task_ids = set(manifest_by_id)
    if set(audit_by_id) != task_ids or set(choice_by_id) != task_ids:
        raise ValueError("Stage 7G-E3-D external task sets do not match exactly")

    rows: list[Stage7GE3DRow] = []
    decoded = Counter()
    level_counts = Counter()
    for task_id in sorted(task_ids):
        audit_row, task, response = audit_by_id[task_id], manifest_by_id[task_id], choice_by_id[task_id]
        level = audit_row.get("curriculum_level")
        if level not in STAGE7G_E3_D_EXPECTED_LEVEL_COUNTS:
            raise ValueError("Stage 7G-E3-D unknown curriculum level")
        level_counts[level] += 1
        style_a, style_b = audit_row.get("blind_A_specialist"), audit_row.get("blind_B_specialist")
        if {style_a, style_b} != {"open_low", "compact"} or style_a == style_b:
            raise ValueError("Stage 7G-E3-D blind specialist mapping is invalid")
        options = task.get("options")
        if not isinstance(options, list) or len(options) != 2:
            raise ValueError("Stage 7G-E3-D teacher task must have exactly two options")
        option_map = {option.get("option_id"): option for option in options if isinstance(option, dict)}
        if set(option_map) != {"A", "B"}:
            raise ValueError("Stage 7G-E3-D teacher task must contain A and B")
        audit_open, audit_compact = _placement_tuple(audit_row.get("open_low")), _placement_tuple(audit_row.get("compact"))
        expected_a = audit_open if style_a == "open_low" else audit_compact
        expected_b = audit_open if style_b == "open_low" else audit_compact
        if _placement_tuple(option_map["A"].get("placements")) != expected_a or _placement_tuple(option_map["B"].get("placements")) != expected_b:
            raise ValueError("Stage 7G-E3-D teacher options do not match the sealed audit")
        if response == "EQUAL_OR_UNSURE":
            decoded["EQUAL_OR_UNSURE"] += 1
            continue
        preferred_style = style_a if response == "A" else style_b
        target = int(preferred_style == "compact")
        decoded["COMPACT" if target else "OPEN_LOW"] += 1
        feature_record = audit_row.get("feature_record")
        if not isinstance(feature_record, dict) or set(feature_record) != set(STAGE7G_E3_FEATURE_NAMES):
            raise ValueError("Stage 7G-E3-D feature record does not match the frozen contract")
        features = tuple(float(feature_record[name]) for name in STAGE7G_E3_FEATURE_NAMES)
        if not all(isfinite(value) for value in features):
            raise ValueError("Stage 7G-E3-D features must be finite")
        family_id = audit_row.get("family_id")
        if not isinstance(family_id, str) or not family_id:
            raise ValueError("Stage 7G-E3-D family id is required")
        rows.append(Stage7GE3DRow(family_id, task_id, level, target, features))
    if dict(level_counts) != STAGE7G_E3_D_EXPECTED_LEVEL_COUNTS or dict(decoded) != STAGE7G_E3_D_EXPECTED_DECODED_COUNTS:
        raise ValueError("Stage 7G-E3-D reconstructed aggregate counts mismatch")
    if len(rows) != STAGE7G_E3_D_EXPECTED_DECISIVE or len({row.family_id for row in rows}) != STAGE7G_E3_D_EXPECTED_FAMILIES:
        raise ValueError("Stage 7G-E3-D decisive row/family count mismatch")
    preflight = stage7g_e3_d_split_preflight(rows)
    preflight.update({
        "schema": STAGE7G_E3_D_EXECUTION_SCHEMA,
        "task_count": STAGE7G_E3_D_EXPECTED_TASKS,
        "decisive_rows": len(rows),
        "equal_or_unsure_excluded": decoded["EQUAL_OR_UNSURE"],
        "families": len({row.family_id for row in rows}),
        "curriculum_level_counts": dict(level_counts),
        "decoded_teacher_preference": dict(decoded),
        "feature_count": len(STAGE7G_E3_FEATURE_NAMES),
        "feature_list_sha256": feature_list_sha256(),
        "package_sha256": STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256,
        "audit_sha256": STAGE7G_E3_D_EXPECTED_AUDIT_SHA256,
        "manifest_sha256": STAGE7G_E3_D_EXPECTED_MANIFEST_SHA256,
        "choices_sha256": STAGE7G_E3_D_EXPECTED_CHOICES_SHA256,
        "stage7e_used": False,
        "checkpoint_retained": False,
        "production_integration": False,
    })
    return tuple(rows), preflight


def _arrays(rows: tuple[Stage7GE3DRow, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not rows:
        raise ValueError("no Stage 7G-E3-D rows")
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.teacher_prefers_compact for row in rows], dtype=np.int64)
    groups = np.asarray([row.family_id for row in rows], dtype=object)
    if X.shape != (len(rows), len(STAGE7G_E3_FEATURE_NAMES)) or not np.isfinite(X).all():
        raise ValueError("Stage 7G-E3-D feature matrix is invalid")
    if set(y.tolist()) != {0, 1}:
        raise ValueError("Stage 7G-E3-D rows must contain both binary classes")
    return X, y, groups


def _fold_class_check(y: np.ndarray, indices: np.ndarray, *, label: str) -> None:
    if set(y[indices].tolist()) != {0, 1}:
        raise ValueError(f"{label} training fold lacks one Teacher-GOLD class")


def stage7g_e3_d_split_preflight(rows: Iterable[Stage7GE3DRow]) -> dict:
    rows = tuple(rows)
    X, y, groups = _arrays(rows)
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=STAGE7G_E3_D_OUTER_RANDOM_STATE)
    outer_reports, seen_outer = [], np.zeros(len(rows), dtype=np.int64)
    for outer_index, (train_idx, test_idx) in enumerate(outer.split(X, y, groups)):
        _fold_class_check(y, train_idx, label=f"outer {outer_index + 1}")
        train_families, test_families = set(groups[train_idx].tolist()), set(groups[test_idx].tolist())
        if train_families & test_families:
            raise AssertionError("Stage 7G-E3-D outer family leakage")
        seen_outer[test_idx] += 1
        X_train, y_train, groups_train = X[train_idx], y[train_idx], groups[train_idx]
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=STAGE7G_E3_D_INNER_RANDOM_STATE_BASE + outer_index)
        inner_seen, inner_reports = np.zeros(len(train_idx), dtype=np.int64), []
        for inner_index, (fit_rel, val_rel) in enumerate(inner.split(X_train, y_train, groups_train)):
            _fold_class_check(y_train, fit_rel, label=f"outer {outer_index + 1} inner {inner_index + 1}")
            fit_families, val_families = set(groups_train[fit_rel].tolist()), set(groups_train[val_rel].tolist())
            if fit_families & val_families:
                raise AssertionError("Stage 7G-E3-D inner family leakage")
            inner_seen[val_rel] += 1
            inner_reports.append({"inner_fold": inner_index + 1, "fit_family_count": len(fit_families), "validation_family_count": len(val_families), "fit_rows": len(fit_rel), "validation_rows": len(val_rel)})
        if not np.all(inner_seen == 1):
            raise AssertionError("Stage 7G-E3-D inner OOF coverage failure")
        outer_reports.append({"outer_fold": outer_index + 1, "inner_random_state": STAGE7G_E3_D_INNER_RANDOM_STATE_BASE + outer_index, "train_family_count": len(train_families), "test_family_count": len(test_families), "train_rows": len(train_idx), "test_rows": len(test_idx), "inner_folds": inner_reports})
    if not np.all(seen_outer == 1):
        raise AssertionError("Stage 7G-E3-D outer OOF coverage failure")
    return {"status": "PREFLIGHT_PASS_STOP_BEFORE_TRAIN", "family_isolated": True, "outer_splits": 5, "inner_splits": 4, "outer_random_state": STAGE7G_E3_D_OUTER_RANDOM_STATE, "inner_random_states": [STAGE7G_E3_D_INNER_RANDOM_STATE_BASE + i for i in range(5)], "outer_folds": outer_reports}


def _new_model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight=None, C=1.0, solver="lbfgs", random_state=0))


def _compact_probability(model, X: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(model.predict_proba(X), dtype=np.float64)
    classifier = model.named_steps.get("logisticregression")
    if classifier is None or list(classifier.classes_) != [0, 1] or probabilities.shape != (len(X), 2) or not np.isfinite(probabilities).all():
        raise ValueError("Stage 7G-E3-D model probabilities/classes are invalid")
    return probabilities[:, 1]


def _prediction_metrics(y: np.ndarray, predicted: np.ndarray) -> dict:
    if len(y) != len(predicted) or not len(y):
        raise ValueError("Stage 7G-E3-D prediction metric shape mismatch")
    tp = int(np.sum((predicted == 1) & (y == 1)))
    fp = int(np.sum((predicted == 1) & (y == 0)))
    fn = int(np.sum((predicted == 0) & (y == 1)))
    switches, compact_total = tp + fp, tp + fn
    accuracy, baseline = float(np.mean(predicted == y)), float(np.mean(y == 0))
    return {"events": len(y), "accuracy": accuracy, "always_open_low_accuracy": baseline, "accuracy_delta_vs_always_open_low": accuracy - baseline, "compact_precision": tp / switches if switches else 0.0, "compact_recall": tp / compact_total if compact_total else 0.0, "compact_true_positive": tp, "compact_false_positive": fp, "compact_false_negative": fn, "compact_switch_count": switches, "compact_switch_rate": switches / len(y)}


def _threshold_metrics(y: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    metrics = _prediction_metrics(y, (probabilities >= threshold).astype(np.int64))
    return {"threshold": float(threshold), **metrics}


def select_stage7g_e3_d_threshold(y: np.ndarray, probabilities: np.ndarray) -> tuple[float | None, list[dict]]:
    candidates, eligible = [], []
    for threshold in STAGE7G_E3_D_THRESHOLDS:
        metrics = _threshold_metrics(y, probabilities, threshold)
        metrics["eligible"] = metrics["compact_switch_count"] >= 10 and metrics["compact_precision"] >= (2.0 / 3.0) and metrics["accuracy"] >= metrics["always_open_low_accuracy"]
        candidates.append(metrics)
        if metrics["eligible"]:
            eligible.append(metrics)
    if not eligible:
        return None, candidates
    best = max(eligible, key=lambda item: (item["compact_recall"], item["accuracy_delta_vs_always_open_low"], item["compact_precision"], item["threshold"]))
    return float(best["threshold"]), candidates


def stage7g_e3_d_nested_cv_report(rows: Iterable[Stage7GE3DRow]) -> dict:
    """Execute only the frozen nested development CV; no fitted model is returned or saved."""
    rows = tuple(rows)
    preflight = stage7g_e3_d_split_preflight(rows)
    X, y, groups = _arrays(rows)
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=STAGE7G_E3_D_OUTER_RANDOM_STATE)
    pooled, seen_outer, outer_reports = np.zeros(len(rows), dtype=np.int64), np.zeros(len(rows), dtype=np.int64), []
    for outer_index, (train_idx, test_idx) in enumerate(outer.split(X, y, groups)):
        X_train, y_train, groups_train = X[train_idx], y[train_idx], groups[train_idx]
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=STAGE7G_E3_D_INNER_RANDOM_STATE_BASE + outer_index)
        inner_probability = np.full(len(train_idx), np.nan, dtype=np.float64)
        for fit_rel, val_rel in inner.split(X_train, y_train, groups_train):
            model = _new_model()
            model.fit(X_train[fit_rel], y_train[fit_rel])
            inner_probability[val_rel] = _compact_probability(model, X_train[val_rel])
        if not np.isfinite(inner_probability).all():
            raise AssertionError("Stage 7G-E3-D inner OOF probability coverage failure")
        selected_threshold, candidates = select_stage7g_e3_d_threshold(y_train, inner_probability)
        if selected_threshold is None:
            test_prediction, selected_label = np.zeros(len(test_idx), dtype=np.int64), "NO_SWITCH"
        else:
            outer_model = _new_model()
            outer_model.fit(X_train, y_train)
            test_prediction = (_compact_probability(outer_model, X[test_idx]) >= selected_threshold).astype(np.int64)
            selected_label = selected_threshold
        pooled[test_idx], seen_outer[test_idx] = test_prediction, seen_outer[test_idx] + 1
        outer_reports.append({"outer_fold": outer_index + 1, "selected_threshold": selected_label, "inner_threshold_candidates": candidates, "test_rows": len(test_idx), **_prediction_metrics(y[test_idx], test_prediction)})
    if not np.all(seen_outer == 1):
        raise AssertionError("Stage 7G-E3-D outer prediction coverage failure")
    aggregate = _prediction_metrics(y, pooled)
    family_accuracy, family_baseline = {}, {}
    family_wins = family_ties = family_losses = 0
    for family_id in sorted(set(groups.tolist())):
        idx = np.flatnonzero(groups == family_id)
        acc, baseline = float(np.mean(pooled[idx] == y[idx])), float(np.mean(y[idx] == 0))
        family_accuracy[family_id], family_baseline[family_id] = acc, baseline
        if acc > baseline:
            family_wins += 1
        elif acc < baseline:
            family_losses += 1
        else:
            family_ties += 1
    levels = np.asarray([row.curriculum_level for row in rows], dtype=object)
    level_metrics = {}
    for level in ("L1", "L2", "L3", "L4"):
        idx = np.flatnonzero(levels == level)
        level_metrics[level] = {"events": len(idx), "accuracy": float(np.mean(pooled[idx] == y[idx])), "compact_switch_count": int(np.sum(pooled[idx] == 1)), "compact_switch_rate": float(np.mean(pooled[idx] == 1))}
    macro_accuracy, macro_baseline = float(np.mean(list(family_accuracy.values()))), float(np.mean(list(family_baseline.values())))
    positive = aggregate["accuracy_delta_vs_always_open_low"] > 0 and macro_accuracy - macro_baseline > 0 and aggregate["compact_precision"] > 0.50 and aggregate["compact_true_positive"] > aggregate["compact_false_positive"] and family_wins > family_losses
    status = "POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN" if positive else "NEGATIVE_DEVELOPMENT_CV_NO_PROMOTION"
    return {"schema": STAGE7G_E3_D_EXECUTION_SCHEMA, "stage": "7G-E3-D", "status": status, "scientific_scope": "nested_development_cv_not_untouched_validation", "preflight_status": preflight["status"], "model": {"features": list(STAGE7G_E3_FEATURE_NAMES), "feature_count": len(STAGE7G_E3_FEATURE_NAMES), "scaler": "StandardScaler", "classifier": "LogisticRegression", "max_iter": 2000, "class_weight": None, "C": 1.0, "solver": "lbfgs", "random_state": 0, "threshold_candidates": list(STAGE7G_E3_D_THRESHOLDS)}, "validation": {"family_isolated": True, "outer_splits": 5, "inner_splits": 4, "outer_random_state": STAGE7G_E3_D_OUTER_RANDOM_STATE, "inner_random_states": preflight["inner_random_states"], "outer_folds": outer_reports}, "aggregate": {**aggregate, "macro_family_accuracy": macro_accuracy, "macro_family_always_open_low_accuracy": macro_baseline, "macro_family_accuracy_delta_vs_always_open_low": macro_accuracy - macro_baseline, "family_wins": family_wins, "family_ties": family_ties, "family_losses": family_losses, "curriculum_level_metrics": level_metrics}, "checkpoint_retained": False, "production_integration": False, "stage7e_used": False}
