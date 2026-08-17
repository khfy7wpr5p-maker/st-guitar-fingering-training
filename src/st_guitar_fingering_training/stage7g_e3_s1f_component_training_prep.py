from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from statistics import fmean
from typing import Iterable, Mapping

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .curriculum_contract import (
    STAGE7G_E3_GEOMETRY_NAMES,
    stage7g_e3_proposal_geometry,
)
from .dataset import Voicing, valid_chord_voicings


S1F_COMPONENTS = (
    "STRING_SKIP_PENALTY",
    "OPEN_STRING_HAND_RELIEF",
    "OPEN_STRING_CONTROL_PENALTY",
)
S1F_BINARY_LABELS = ("NO", "YES")
S1F_EXCLUDED_LABEL = "UNSURE"
S1F_FEATURE_NAMES = (
    "chord_size",
    "pitch_span",
    "mean_pitch",
    "candidate_count",
    *STAGE7G_E3_GEOMETRY_NAMES,
)
S1F_FAMILY_FOLDS = 5
S1F_VALIDATION_THRESHOLD = 0.5
S1F_SPLIT_SALT = "stage7g-e3-s1f-family-fold-v1"
S1F_TRAINING_GATE_SCHEMA = "st-guitar-stage7g-e3-s1f-training-authorization-v1"


@dataclass(frozen=True)
class Stage7GE3S1FTrainingRow:
    example_id: str
    family_id: str
    task_id: str
    option_id: str
    specialist: str
    label: int
    features: tuple[float, ...]
    provenance: str


@dataclass(frozen=True)
class Stage7GE3S1FEvaluation:
    specialist: str
    rows: int
    families: int
    accuracy: float
    balanced_accuracy: float
    precision_yes: float
    recall_yes: float
    f1_yes: float
    true_no: int
    false_yes: int
    false_no: int
    true_yes: int


def _canonical_feature_record(
    pitches_midi: Iterable[int],
    tuning: Iterable[int],
    voicing: Voicing,
) -> dict[str, float]:
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning_tuple = tuple(int(value) for value in tuning)
    if len(tuning_tuple) != 6:
        raise ValueError("S1-F supports six-string tuning only")
    if len(pitches) < 2 or len(pitches) > 6:
        raise ValueError("S1-F requires 2..6 simultaneous pitches")

    candidates = valid_chord_voicings(pitches, tuning_tuple)
    if voicing not in candidates:
        raise ValueError("S1-F voicing must belong to the deterministic valid candidate set")
    if not candidates:
        raise ValueError("S1-F requires at least one deterministic candidate")

    geometry = stage7g_e3_proposal_geometry(voicing)
    record = {
        "chord_size": float(len(pitches)),
        "pitch_span": float(max(pitches) - min(pitches)),
        "mean_pitch": float(fmean(pitches)),
        "candidate_count": float(len(candidates)),
    }
    record.update(
        {name: float(value) for name, value in zip(STAGE7G_E3_GEOMETRY_NAMES, geometry)}
    )
    if tuple(record) != S1F_FEATURE_NAMES:
        raise AssertionError("S1-F feature ordering drift")
    if not all(isfinite(value) for value in record.values()):
        raise ValueError("S1-F features must be finite")
    return record


def component_feature_record(
    *,
    specialist: str,
    pitches_midi: Iterable[int],
    tuning: Iterable[int],
    voicing: Voicing,
) -> dict[str, float]:
    """Return frozen target-blind features for one physically valid voicing.

    This helper never reads a Teacher label and never derives a target from
    geometry. Geometry is descriptive input only.
    """

    if specialist not in S1F_COMPONENTS:
        raise ValueError("unknown S1-F specialist")
    record = _canonical_feature_record(pitches_midi, tuning, voicing)
    if specialist in ("OPEN_STRING_HAND_RELIEF", "OPEN_STRING_CONTROL_PENALTY"):
        if record["open_note_count"] < 1.0:
            raise ValueError("open-string specialists require a voicing with at least one open string")
    return record


def build_training_row(
    *,
    example_id: str,
    family_id: str,
    task_id: str,
    option_id: str,
    specialist: str,
    label: str,
    pitches_midi: Iterable[int],
    tuning: Iterable[int],
    voicing: Voicing,
    provenance: str,
) -> Stage7GE3S1FTrainingRow | None:
    """Build one future full-reliability first-pass row.

    `UNSURE` is explicitly excluded rather than converted into a binary target.
    Pilot and repeat provenance are rejected. This function does not authorize
    model fitting.
    """

    normalized = str(label).upper()
    if normalized == S1F_EXCLUDED_LABEL:
        return None
    if normalized not in S1F_BINARY_LABELS:
        raise ValueError("S1-F labels must be YES, NO, or UNSURE")

    provenance_upper = str(provenance).upper()
    if "REPEAT" in provenance_upper:
        raise ValueError("S1 repeat labels are reliability-only and may not enter training")
    if "PILOT" in provenance_upper:
        raise ValueError("S1-E pilot labels are diagnostic-only and may not enter training")
    if "FIRST_PASS" not in provenance_upper or "FULL_RELIABILITY" not in provenance_upper:
        raise ValueError("S1-F training rows require future FULL_RELIABILITY_FIRST_PASS provenance")

    feature_record = component_feature_record(
        specialist=specialist,
        pitches_midi=pitches_midi,
        tuning=tuning,
        voicing=voicing,
    )
    values = tuple(float(feature_record[name]) for name in S1F_FEATURE_NAMES)
    return Stage7GE3S1FTrainingRow(
        example_id=str(example_id),
        family_id=str(family_id),
        task_id=str(task_id),
        option_id=str(option_id),
        specialist=specialist,
        label=int(normalized == "YES"),
        features=values,
        provenance=str(provenance),
    )


def _validate_rows(rows: tuple[Stage7GE3S1FTrainingRow, ...]) -> str:
    if not rows:
        raise ValueError("S1-F requires at least one training row")
    specialists = {row.specialist for row in rows}
    if len(specialists) != 1 or next(iter(specialists)) not in S1F_COMPONENTS:
        raise ValueError("S1-F rows must belong to exactly one known specialist")
    if len({row.example_id for row in rows}) != len(rows):
        raise ValueError("S1-F example IDs must be unique")
    if any(len(row.features) != len(S1F_FEATURE_NAMES) for row in rows):
        raise ValueError("S1-F feature dimension mismatch")
    if any(not all(isfinite(value) for value in row.features) for row in rows):
        raise ValueError("S1-F rows contain non-finite features")
    if any(row.label not in (0, 1) for row in rows):
        raise ValueError("S1-F binary labels must be 0/1")
    if any("REPEAT" in row.provenance.upper() or "PILOT" in row.provenance.upper() for row in rows):
        raise ValueError("S1-F rows contain forbidden repeat/pilot provenance")
    return next(iter(specialists))


def family_fold_map(
    rows: Iterable[Stage7GE3S1FTrainingRow],
    *,
    folds: int = S1F_FAMILY_FOLDS,
) -> dict[str, int]:
    rows_tuple = tuple(rows)
    if folds < 2:
        raise ValueError("S1-F requires at least two family folds")
    families = sorted(
        {row.family_id for row in rows_tuple},
        key=lambda family: sha256((family + "|" + S1F_SPLIT_SALT).encode()).hexdigest(),
    )
    if len(families) < folds:
        raise ValueError("S1-F requires at least one distinct family per fold")
    return {family: index % folds for index, family in enumerate(families)}


def split_family_safe(
    rows: Iterable[Stage7GE3S1FTrainingRow],
    *,
    validation_fold: int,
    folds: int = S1F_FAMILY_FOLDS,
) -> tuple[tuple[Stage7GE3S1FTrainingRow, ...], tuple[Stage7GE3S1FTrainingRow, ...]]:
    rows_tuple = tuple(rows)
    _validate_rows(rows_tuple)
    if validation_fold < 0 or validation_fold >= folds:
        raise ValueError("validation_fold outside configured fold range")
    fold_by_family = family_fold_map(rows_tuple, folds=folds)
    train = tuple(row for row in rows_tuple if fold_by_family[row.family_id] != validation_fold)
    validation = tuple(row for row in rows_tuple if fold_by_family[row.family_id] == validation_fold)
    if not train or not validation:
        raise ValueError("S1-F family split produced an empty partition")
    train_families = {row.family_id for row in train}
    validation_families = {row.family_id for row in validation}
    if train_families & validation_families:
        raise AssertionError("family leakage across S1-F train/validation")
    return train, validation


def _authorization_passes(authorization: Mapping[str, object]) -> bool:
    return (
        authorization.get("schema") == S1F_TRAINING_GATE_SCHEMA
        and authorization.get("full_reliability_status") == "PASS"
        and authorization.get("training_protocol_status") == "MERGED"
        and authorization.get("repeat_labels_used") is False
        and authorization.get("pilot_labels_used") is False
        and authorization.get("threshold_tuned_on_validation") is False
        and authorization.get("checkpoint_retention_authorized") is False
        and authorization.get("production_or_shadow_integration") is False
    )


def _matrix(rows: tuple[Stage7GE3S1FTrainingRow, ...]) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray([row.features for row in rows], dtype=np.float64)
    y = np.asarray([row.label for row in rows], dtype=np.int64)
    if X.shape != (len(rows), len(S1F_FEATURE_NAMES)) or not np.isfinite(X).all():
        raise ValueError("invalid S1-F feature matrix")
    return X, y


def fit_component_specialist(
    rows: Iterable[Stage7GE3S1FTrainingRow],
    *,
    authorization: Mapping[str, object],
) -> Pipeline:
    """Fit an in-memory fixed logistic baseline after the future gate opens.

    The current S1-F preparation stage must fail closed because no full
    reliability PASS + merged training protocol exists yet. No checkpoint is
    serialized by this API.
    """

    if not _authorization_passes(authorization):
        raise PermissionError("S1-F training gate is closed")
    rows_tuple = tuple(rows)
    _validate_rows(rows_tuple)
    X, y = _matrix(rows_tuple)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("S1-F fitting requires both YES and NO labels")
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                    random_state=0,
                ),
            ),
        ]
    )
    model.fit(X, y)
    return model


def evaluate_component_specialist(
    model: Pipeline,
    rows: Iterable[Stage7GE3S1FTrainingRow],
) -> Stage7GE3S1FEvaluation:
    rows_tuple = tuple(rows)
    specialist = _validate_rows(rows_tuple)
    X, y = _matrix(rows_tuple)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("S1-F evaluation requires both YES and NO labels")
    probabilities = np.asarray(model.predict_proba(X)[:, 1], dtype=np.float64)
    if probabilities.shape != (len(rows_tuple),) or not np.isfinite(probabilities).all():
        raise ValueError("invalid S1-F probability vector")
    pred = (probabilities >= S1F_VALIDATION_THRESHOLD).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return Stage7GE3S1FEvaluation(
        specialist=specialist,
        rows=len(rows_tuple),
        families=len({row.family_id for row in rows_tuple}),
        accuracy=float(accuracy_score(y, pred)),
        balanced_accuracy=float(balanced_accuracy_score(y, pred)),
        precision_yes=float(precision_score(y, pred, zero_division=0)),
        recall_yes=float(recall_score(y, pred, zero_division=0)),
        f1_yes=float(f1_score(y, pred, zero_division=0)),
        true_no=int(tn),
        false_yes=int(fp),
        false_no=int(fn),
        true_yes=int(tp),
    )


def majority_baseline_label(rows: Iterable[Stage7GE3S1FTrainingRow]) -> int:
    rows_tuple = tuple(rows)
    _validate_rows(rows_tuple)
    counts = Counter(row.label for row in rows_tuple)
    if not counts:
        raise ValueError("S1-F majority baseline requires rows")
    return 1 if counts[1] > counts[0] else 0


def evaluate_constant_baseline(
    rows: Iterable[Stage7GE3S1FTrainingRow],
    *,
    predicted_label: int,
) -> Stage7GE3S1FEvaluation:
    if predicted_label not in (0, 1):
        raise ValueError("baseline label must be 0 or 1")
    rows_tuple = tuple(rows)
    specialist = _validate_rows(rows_tuple)
    y = np.asarray([row.label for row in rows_tuple], dtype=np.int64)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("S1-F baseline evaluation requires both labels")
    pred = np.full(len(rows_tuple), predicted_label, dtype=np.int64)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return Stage7GE3S1FEvaluation(
        specialist=specialist,
        rows=len(rows_tuple),
        families=len({row.family_id for row in rows_tuple}),
        accuracy=float(accuracy_score(y, pred)),
        balanced_accuracy=float(balanced_accuracy_score(y, pred)),
        precision_yes=float(precision_score(y, pred, zero_division=0)),
        recall_yes=float(recall_score(y, pred, zero_division=0)),
        f1_yes=float(f1_score(y, pred, zero_division=0)),
        true_no=int(tn),
        false_yes=int(fp),
        false_no=int(fn),
        true_yes=int(tp),
    )
