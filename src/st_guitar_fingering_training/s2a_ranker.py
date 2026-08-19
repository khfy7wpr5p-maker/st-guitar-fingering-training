from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .finger_assignments import generate_standard_fingerings
from .s2a_features import S2A_FEATURE_NAMES, assignment_feature_vector
from .s2a_teacher import (
    S2A_FINAL_PROVENANCE,
    S2A_FIRST_PASS_PROVENANCE,
    S2A_INTERNAL_AUDIT_SCHEMA,
    validate_s2a_choice_export,
)
from .synthetic_behavior import deterministic_style_folds


@dataclass(frozen=True)
class S2APairRow:
    family_id: str
    event_id: str
    task_id: str
    pitches_midi: tuple[int, ...]
    tuning: tuple[int, ...]
    a_assignment_id: str
    b_assignment_id: str
    a_features: tuple[float, ...]
    b_features: tuple[float, ...]
    teacher_prefers_a: int
    pair_type: str
    distance_stratum: str
    provenance: str


@dataclass(frozen=True)
class S2ACorpus:
    provenance: str
    annotated_task_count: int
    equal_or_unsure_count: int
    rows: tuple[S2APairRow, ...]


def _event_assignment_features(
    pitches_midi: tuple[int, ...],
    tuning: tuple[int, ...],
) -> dict[str, tuple[float, ...]]:
    generated = generate_standard_fingerings(pitches_midi, tuning)
    out: dict[str, tuple[float, ...]] = {}
    for candidate in generated.candidates:
        for assignment in candidate.assignments:
            if assignment.assignment_id in out:
                raise AssertionError("S2-A event contains duplicate assignment IDs")
            out[assignment.assignment_id] = assignment_feature_vector(assignment)
    return out


def build_s2a_corpus(
    packages: Iterable[tuple[dict, dict, dict]],
    *,
    expected_provenance: str,
) -> S2ACorpus:
    """Decode sealed S2-A packages into decisive pair rows with fresh H-C lineage checks."""

    if expected_provenance not in (S2A_FIRST_PASS_PROVENANCE, S2A_FINAL_PROVENANCE):
        raise ValueError("S2-A corpus provenance must be FIRST_PASS or UNTOUCHED_FINAL")

    rows: list[S2APairRow] = []
    seen_task_ids: set[str] = set()
    annotated_task_count = 0
    equal_or_unsure_count = 0

    for teacher_manifest, internal_audit, choice_payload in packages:
        if teacher_manifest.get("provenance") != expected_provenance:
            raise ValueError("S2-A teacher manifest provenance mismatch")
        if internal_audit.get("schema") != S2A_INTERNAL_AUDIT_SCHEMA:
            raise ValueError("unexpected S2-A internal audit schema")
        if internal_audit.get("provenance") != expected_provenance:
            raise ValueError("S2-A internal audit provenance mismatch")
        choices = validate_s2a_choice_export(choice_payload, teacher_manifest)
        audit_by_task = {row["task_id"]: row for row in internal_audit.get("rows", [])}
        if set(audit_by_task) != set(choices):
            raise ValueError("S2-A audit/choice task mismatch")

        annotated_task_count += len(choices)
        for task_id in sorted(choices):
            if task_id in seen_task_ids:
                raise ValueError("duplicate S2-A task_id across corpus packages")
            seen_task_ids.add(task_id)
            response = choices[task_id]
            if response == "EQUAL_OR_UNSURE":
                equal_or_unsure_count += 1
                continue

            audit = audit_by_task[task_id]
            pitches = tuple(int(value) for value in audit["pitches_midi"])
            tuning = tuple(int(value) for value in audit["tuning"])
            recomputed = _event_assignment_features(pitches, tuning)
            a_id = str(audit["A_assignment_id"])
            b_id = str(audit["B_assignment_id"])
            if a_id == b_id or a_id not in recomputed or b_id not in recomputed:
                raise ValueError("S2-A pair assignment missing from fresh H-C output")
            a_features = recomputed[a_id]
            b_features = recomputed[b_id]
            if tuple(float(value) for value in audit["A_features"]) != a_features:
                raise ValueError("S2-A stored A features do not match fresh H-C recomputation")
            if tuple(float(value) for value in audit["B_features"]) != b_features:
                raise ValueError("S2-A stored B features do not match fresh H-C recomputation")

            row = S2APairRow(
                family_id=str(audit["family_id"]),
                event_id=str(audit["event_id"]),
                task_id=task_id,
                pitches_midi=pitches,
                tuning=tuning,
                a_assignment_id=a_id,
                b_assignment_id=b_id,
                a_features=a_features,
                b_features=b_features,
                teacher_prefers_a=1 if response == "A" else 0,
                pair_type=str(audit["pair_type"]),
                distance_stratum=str(audit["distance_stratum"]),
                provenance=expected_provenance,
            )
            _validate_pair_row(row)
            rows.append(row)

    rows.sort(key=lambda row: row.task_id)
    return S2ACorpus(
        provenance=expected_provenance,
        annotated_task_count=annotated_task_count,
        equal_or_unsure_count=equal_or_unsure_count,
        rows=tuple(rows),
    )


def _validate_pair_row(row: S2APairRow) -> None:
    if not row.family_id or not row.event_id or not row.task_id:
        raise ValueError("S2-A pair row requires family/event/task identity")
    if row.provenance not in (S2A_FIRST_PASS_PROVENANCE, S2A_FINAL_PROVENANCE):
        raise ValueError("S2-A pair row has forbidden provenance")
    if row.teacher_prefers_a not in (0, 1):
        raise ValueError("S2-A decisive target must be binary")
    if row.pair_type not in ("FINGER_ONLY", "MIXED"):
        raise ValueError("S2-A pair_type outside frozen contract")
    if row.distance_stratum not in ("NEAR", "MID", "FAR"):
        raise ValueError("S2-A distance_stratum outside frozen contract")
    if row.a_assignment_id == row.b_assignment_id:
        raise ValueError("S2-A pair requires two distinct assignments")
    if len(row.a_features) != 30 or len(row.b_features) != 30:
        raise ValueError("S2-A feature dimension must be exactly 30")
    if not all(isfinite(value) for value in row.a_features + row.b_features):
        raise ValueError("S2-A pair features must be finite")


def build_s2a_pairwise_training_matrix(
    rows: Iterable[S2APairRow],
) -> tuple[np.ndarray, np.ndarray]:
    rows = tuple(rows)
    if not rows:
        raise ValueError("no decisive S2-A pair rows")
    differences: list[np.ndarray] = []
    labels: list[int] = []
    for row in rows:
        _validate_pair_row(row)
        if row.provenance != S2A_FIRST_PASS_PROVENANCE:
            raise ValueError("S2-A fit matrix accepts FIRST_PASS rows only")
        delta = np.asarray(row.a_features, dtype=np.float64) - np.asarray(row.b_features, dtype=np.float64)
        differences.extend((delta, -delta))
        labels.extend((row.teacher_prefers_a, 1 - row.teacher_prefers_a))
    X = np.asarray(differences, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)
    if X.shape != (2 * len(rows), len(S2A_FEATURE_NAMES)):
        raise AssertionError("S2-A mirrored training matrix shape mismatch")
    if not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("invalid S2-A mirrored training matrix")
    for index in range(0, len(X), 2):
        if not np.array_equal(X[index], -X[index + 1]) or y[index] == y[index + 1]:
            raise AssertionError("S2-A mirrored pair symmetry violated")
    return X, y


def build_s2a_ranker_model() -> LogisticRegression:
    return LogisticRegression(
        penalty="l2",
        C=1.0,
        fit_intercept=False,
        class_weight=None,
        solver="lbfgs",
        max_iter=2000,
        random_state=0,
    )


def _reliability_fields_pass(report: dict, *, minimum_repeat_tasks: int) -> bool:
    return (
        int(report.get("repeat_tasks", 0)) >= minimum_repeat_tasks
        and float(report.get("three_class_exact_agreement", -1.0)) >= 0.85
        and float(report.get("decisive_cohen_kappa", -1.0)) >= 0.75
        and report.get("repeat_interval_24_to_72h") is True
        and report.get("presentation_reversal_exactly_50_percent") is True
        and report.get("old_answers_included") is False
        and report.get("status") == "PASS"
    )


def s2a_fit_gate_report(
    corpus: S2ACorpus,
    reliability_report: dict,
    *,
    untouched_family_ids: Iterable[str] = (),
) -> dict:
    if corpus.provenance != S2A_FIRST_PASS_PROVENANCE:
        raise ValueError("S2-A real fit gate accepts FIRST_PASS corpus only")
    for row in corpus.rows:
        _validate_pair_row(row)
        if row.provenance != S2A_FIRST_PASS_PROVENANCE:
            raise ValueError("S2-A fit corpus contains non-FIRST_PASS row")

    families = {row.family_id for row in corpus.rows}
    events = {(row.family_id, row.event_id) for row in corpus.rows}
    finger_only = sum(row.pair_type == "FINGER_ONLY" for row in corpus.rows)
    mixed = sum(row.pair_type == "MIXED" for row in corpus.rows)
    strata = {
        stratum: sum(row.distance_stratum == stratum for row in corpus.rows)
        for stratum in ("NEAR", "MID", "FAR")
    }
    final_families = {str(value) for value in untouched_family_ids}
    family_overlap = families & final_families
    minimum_repeat_tasks = max(120, ceil(0.20 * corpus.annotated_task_count))

    checks = {
        "development_families_gte_40": len(families) >= 40,
        "development_events_gte_200": len(events) >= 200,
        "decisive_first_pass_pairs_gte_600": len(corpus.rows) >= 600,
        "finger_only_decisive_pairs_gte_150": finger_only >= 150,
        "mixed_decisive_pairs_gte_150": mixed >= 150,
        "near_decisive_pairs_gte_100": strata["NEAR"] >= 100,
        "mid_decisive_pairs_gte_100": strata["MID"] >= 100,
        "far_decisive_pairs_gte_100": strata["FAR"] >= 100,
        "development_final_family_disjoint": not family_overlap,
        "reliability_gate_pass": _reliability_fields_pass(
            reliability_report,
            minimum_repeat_tasks=minimum_repeat_tasks,
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "development_families": len(families),
        "development_events": len(events),
        "annotated_tasks": corpus.annotated_task_count,
        "decisive_pairs": len(corpus.rows),
        "equal_or_unsure": corpus.equal_or_unsure_count,
        "finger_only_decisive_pairs": finger_only,
        "mixed_decisive_pairs": mixed,
        "distance_strata_decisive_pairs": strata,
        "minimum_repeat_tasks": minimum_repeat_tasks,
        "family_overlap_with_untouched_final": sorted(family_overlap),
        "checkpoint_retention_authorized": False,
        "shadow_or_production_authorized": False,
    }


def fit_s2a_ranker(
    corpus: S2ACorpus,
    reliability_report: dict,
    *,
    untouched_family_ids: Iterable[str] = (),
):
    gate = s2a_fit_gate_report(
        corpus,
        reliability_report,
        untouched_family_ids=untouched_family_ids,
    )
    if gate["status"] != "PASS":
        raise RuntimeError("S2-A real fit gate is CLOSED")
    X, y = build_s2a_pairwise_training_matrix(corpus.rows)
    model = build_s2a_ranker_model()
    model.fit(X, y)
    return model


def _pair_probabilities(model, rows: tuple[S2APairRow, ...]) -> np.ndarray:
    X = np.asarray([
        np.asarray(row.a_features, dtype=np.float64) - np.asarray(row.b_features, dtype=np.float64)
        for row in rows
    ])
    decision = np.asarray(model.decision_function(X), dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-decision))


def _baseline_prediction(row: S2APairRow, baseline: str) -> int:
    if baseline == "LOW_FRET_BASELINE":
        left = row.a_features[19]
        right = row.b_features[19]
    elif baseline == "COMPACT_BASELINE":
        left = row.a_features[20]
        right = row.b_features[20]
    elif baseline == "HASH_BASELINE":
        left = right = 0.0
    else:
        raise ValueError("unknown S2-A baseline")
    if left < right:
        return 1
    if right < left:
        return 0
    return int(row.a_assignment_id < row.b_assignment_id)


def _family_accuracy(rows: tuple[S2APairRow, ...], predictions: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for family_id in sorted({row.family_id for row in rows}):
        indices = [index for index, row in enumerate(rows) if row.family_id == family_id]
        out[family_id] = float(np.mean([
            int(predictions[index]) == rows[index].teacher_prefers_a
            for index in indices
        ]))
    return out


def _metric_panel(rows: tuple[S2APairRow, ...], probabilities: np.ndarray, comparator: str) -> dict:
    y = np.asarray([row.teacher_prefers_a for row in rows], dtype=np.int64)
    predicted = (probabilities >= 0.5).astype(np.int64)
    family_model = _family_accuracy(rows, predicted)
    comparator_predictions = np.asarray([
        _baseline_prediction(row, comparator) for row in rows
    ], dtype=np.int64)
    family_comparator = _family_accuracy(rows, comparator_predictions)
    wins = sum(family_model[key] > family_comparator[key] for key in family_model)
    ties = sum(family_model[key] == family_comparator[key] for key in family_model)
    losses = sum(family_model[key] < family_comparator[key] for key in family_model)

    auc = float(roc_auc_score(y, probabilities)) if len(set(y.tolist())) == 2 else None
    return {
        "pairwise_accuracy": float(np.mean(predicted == y)),
        "macro_family_accuracy": float(np.mean(list(family_model.values()))),
        "roc_auc": auc,
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "comparator": comparator,
        "comparator_pairwise_accuracy": float(np.mean(comparator_predictions == y)),
        "comparator_macro_family_accuracy": float(np.mean(list(family_comparator.values()))),
        "macro_family_accuracy_delta_vs_comparator": float(
            np.mean(list(family_model.values())) - np.mean(list(family_comparator.values()))
        ),
        "family_wins": wins,
        "family_ties": ties,
        "family_losses": losses,
        "finger_only_accuracy": _slice_accuracy(rows, predicted, "pair_type", "FINGER_ONLY"),
        "mixed_accuracy": _slice_accuracy(rows, predicted, "pair_type", "MIXED"),
        "near_accuracy": _slice_accuracy(rows, predicted, "distance_stratum", "NEAR"),
        "mid_accuracy": _slice_accuracy(rows, predicted, "distance_stratum", "MID"),
        "far_accuracy": _slice_accuracy(rows, predicted, "distance_stratum", "FAR"),
    }


def _slice_accuracy(rows, predictions, attr: str, value: str):
    indices = [index for index, row in enumerate(rows) if getattr(row, attr) == value]
    if not indices:
        return None
    return float(np.mean([
        int(predictions[index]) == rows[index].teacher_prefers_a for index in indices
    ]))


def _baseline_macro_family_accuracy(rows: tuple[S2APairRow, ...], baseline: str) -> float:
    predictions = np.asarray([_baseline_prediction(row, baseline) for row in rows], dtype=np.int64)
    return float(np.mean(list(_family_accuracy(rows, predictions).values())))


def _development_cv_once(corpus: S2ACorpus, folds: int) -> dict:
    rows = tuple(corpus.rows)
    family_ids = tuple(sorted({row.family_id for row in rows}))
    fold_family_ids = deterministic_style_folds(family_ids, folds=folds)
    probabilities_by_task: dict[str, float] = {}

    for validation_tuple in fold_family_ids:
        validation_ids = set(validation_tuple)
        train_rows = tuple(row for row in rows if row.family_id not in validation_ids)
        validation_rows = tuple(row for row in rows if row.family_id in validation_ids)
        if {row.family_id for row in train_rows} & {row.family_id for row in validation_rows}:
            raise AssertionError("S2-A family leakage in development CV")
        X, y = build_s2a_pairwise_training_matrix(train_rows)
        model = build_s2a_ranker_model()
        model.fit(X, y)
        fold_probabilities = _pair_probabilities(model, validation_rows)
        for row, probability in zip(validation_rows, fold_probabilities):
            if row.task_id in probabilities_by_task:
                raise AssertionError("S2-A task evaluated more than once out-of-fold")
            probabilities_by_task[row.task_id] = float(probability)

    if set(probabilities_by_task) != {row.task_id for row in rows}:
        raise AssertionError("S2-A development CV did not evaluate every task exactly once")
    probabilities = np.asarray([probabilities_by_task[row.task_id] for row in rows], dtype=np.float64)

    low_macro = _baseline_macro_family_accuracy(rows, "LOW_FRET_BASELINE")
    compact_macro = _baseline_macro_family_accuracy(rows, "COMPACT_BASELINE")
    comparator = "LOW_FRET_BASELINE" if low_macro >= compact_macro else "COMPACT_BASELINE"
    metrics = _metric_panel(rows, probabilities, comparator)
    return {
        "fold_count": folds,
        "family_isolated": True,
        "comparator_selection": {
            "low_fret_macro_family_accuracy": low_macro,
            "compact_macro_family_accuracy": compact_macro,
            "selected": comparator,
            "tie_break": "LOW_FRET_BASELINE",
        },
        "metrics": metrics,
        "task_probabilities": [
            (row.task_id, float(probabilities[index])) for index, row in enumerate(rows)
        ],
    }


def development_cv_report(
    corpus: S2ACorpus,
    reliability_report: dict,
    *,
    untouched_family_ids: Iterable[str] = (),
    folds: int = 5,
) -> dict:
    gate = s2a_fit_gate_report(
        corpus,
        reliability_report,
        untouched_family_ids=untouched_family_ids,
    )
    if gate["status"] != "PASS":
        raise RuntimeError("S2-A development CV fit gate is CLOSED")

    expected = _development_cv_once(corpus, folds)
    repeatability_pass = True
    for _ in range(9):
        if _development_cv_once(corpus, folds) != expected:
            repeatability_pass = False
            break

    metrics = expected["metrics"]
    finger_count = sum(row.pair_type == "FINGER_ONLY" for row in corpus.rows)
    mixed_count = sum(row.pair_type == "MIXED" for row in corpus.rows)
    slice_checks = {
        "finger_only": True if finger_count < 100 else metrics["finger_only_accuracy"] >= 0.60,
        "mixed": True if mixed_count < 100 else metrics["mixed_accuracy"] >= 0.60,
    }
    pass_checks = {
        "pairwise_accuracy_gte_065": metrics["pairwise_accuracy"] >= 0.65,
        "macro_family_accuracy_gte_065": metrics["macro_family_accuracy"] >= 0.65,
        "roc_auc_gte_070": metrics["roc_auc"] is not None and metrics["roc_auc"] >= 0.70,
        "macro_family_delta_gte_005": metrics["macro_family_accuracy_delta_vs_comparator"] >= 0.05,
        "family_wins_gt_losses": metrics["family_wins"] > metrics["family_losses"],
        "finger_only_slice": slice_checks["finger_only"],
        "mixed_slice": slice_checks["mixed"],
        "ten_of_ten_repeatability": repeatability_pass,
    }
    return {
        "stage": "7G-E3-S2-A",
        "protocol_version": "S2-A.v1",
        "fit_gate": gate,
        **expected,
        "pass_checks": pass_checks,
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "checkpoint_retained": False,
        "shadow_or_production_integration": False,
    }


def rank_s2a_assignments(model, pitches_midi: tuple[int, ...], tuning: tuple[int, ...]) -> tuple[dict, ...]:
    generated = generate_standard_fingerings(pitches_midi, tuning)
    rows: list[tuple[str, str, tuple[float, ...]]] = []
    for candidate in generated.candidates:
        for assignment in candidate.assignments:
            rows.append((candidate.candidate_id, assignment.assignment_id, assignment_feature_vector(assignment)))
    if not rows:
        raise ValueError("S2-A cannot rank an event with no H-C assignments")
    X = np.asarray([features for _, _, features in rows], dtype=np.float64)
    scores = np.asarray(model.decision_function(X), dtype=np.float64)
    ranked = sorted(
        zip(rows, scores),
        key=lambda item: (-float(item[1]), item[0][1]),
    )
    result = tuple({
        "candidate_id": candidate_id,
        "assignment_id": assignment_id,
        "score": float(score),
    } for ((candidate_id, assignment_id, _), score) in ranked)
    if {row["assignment_id"] for row in result} != {assignment_id for _, assignment_id, _ in rows}:
        raise AssertionError("S2-A ranking changed the H-C assignment authority set")
    return result
