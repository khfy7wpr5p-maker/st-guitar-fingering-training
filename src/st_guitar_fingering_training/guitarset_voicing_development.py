from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
import platform
from pathlib import Path
from typing import Iterable
import zipfile

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .guitarset_observed_gold import (
    _validated_comp_members,
    archive_sha256,
    derive_strum_voicings,
    extract_comp_jams,
)
from .guitarset_split import parse_comp_member_identity
from .guitarset_voicing_prereg import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_NEGATIVE_SAMPLE_CAP,
    GUITARSET_SOURCE_ARCHIVE_SHA256,
    GUITARSET_VOICING_MAX_FRET,
    assert_frozen_protocol,
)

DEVELOPMENT_PERFORMERS = ("00", "01", "04", "05")
EXPECTED_DEVELOPMENT_RECORDINGS = 120
EXPECTED_DEVELOPMENT_ACCEPTED_NOTES = 31699
EXPECTED_DEVELOPMENT_QUARANTINED_NOTES = 35
EXPECTED_DEVELOPMENT_VOICINGS = 8330
MAX_ENUMERATED_CANDIDATES_PER_EVENT = 10000

TUNING_BY_STRING = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
Candidate = tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class DevelopmentEvent:
    performer: str
    recording_id: str
    voicing_id: str
    observed: Candidate
    candidates: tuple[Candidate, ...]


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_sha256(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def canonical_candidate(candidate: Candidate) -> str:
    return json.dumps(
        [[int(pitch), int(string), int(fret)] for pitch, string, fret in candidate],
        separators=(",", ":"),
        ensure_ascii=True,
    )


@lru_cache(maxsize=None)
def enumerate_voicing_candidates(pitches_midi: tuple[int, ...]) -> tuple[Candidate, ...]:
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    if not 2 <= len(pitches) <= 6:
        return ()

    per_pitch: list[tuple[tuple[int, int, int], ...]] = []
    for pitch in pitches:
        placements = []
        for string in range(1, 7):
            fret = pitch - TUNING_BY_STRING[string]
            if 0 <= fret <= GUITARSET_VOICING_MAX_FRET:
                placements.append((pitch, string, fret))
        if not placements:
            return ()
        per_pitch.append(tuple(placements))

    out: set[Candidate] = set()

    def visit(index: int, used_strings: frozenset[int], chosen: Candidate) -> None:
        if len(out) > MAX_ENUMERATED_CANDIDATES_PER_EVENT:
            raise ValueError("GuitarSet voicing candidate enumeration exceeded safety ceiling")
        if index == len(pitches):
            out.add(tuple(sorted(chosen)))
            return
        for placement in per_pitch[index]:
            string = placement[1]
            if string in used_strings:
                continue
            visit(index + 1, used_strings | {string}, chosen + (placement,))

    visit(0, frozenset(), ())
    if len(out) > MAX_ENUMERATED_CANDIDATES_PER_EVENT:
        raise ValueError("GuitarSet voicing candidate enumeration exceeded safety ceiling")
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def feature_vector(candidate: Candidate) -> tuple[float, ...]:
    if not candidate:
        raise ValueError("empty GuitarSet voicing candidate")
    if len({string for _, string, _ in candidate}) != len(candidate):
        raise ValueError("candidate reuses a string")

    note_count = len(candidate)
    frets = [fret for _, _, fret in candidate]
    strings = [string for _, string, _ in candidate]
    positive = [fret for fret in frets if fret > 0]
    occupied = set(strings)
    open_count = sum(fret == 0 for fret in frets)
    adjacent_pairs = sum(1 for string in range(1, 6) if string in occupied and string + 1 in occupied)
    internal_gaps = max(strings) - min(strings) + 1 - len(occupied)
    by_string = {string: (pitch, fret) for pitch, string, fret in candidate}

    values = [
        open_count / note_count,
        sum(frets) / (note_count * GUITARSET_VOICING_MAX_FRET),
        max(frets) / GUITARSET_VOICING_MAX_FRET,
        min(positive) / GUITARSET_VOICING_MAX_FRET if positive else 0.0,
        max(positive) / GUITARSET_VOICING_MAX_FRET if positive else 0.0,
        (max(positive) - min(positive)) / GUITARSET_VOICING_MAX_FRET if positive else 0.0,
        (max(strings) - min(strings)) / 5.0,
        adjacent_pairs / max(1, note_count - 1),
        internal_gaps / 5.0,
        sum(string - 1 for string in strings) / (note_count * 5.0),
    ]
    values.extend(1.0 if string in by_string else 0.0 for string in range(1, 7))
    values.extend(
        by_string[string][1] / GUITARSET_VOICING_MAX_FRET if string in by_string else 0.0
        for string in range(1, 7)
    )
    values.extend(
        by_string[string][0] / 127.0 if string in by_string else 0.0
        for string in range(1, 7)
    )
    if len(values) != 28 or not np.isfinite(np.asarray(values, dtype=np.float64)).all():
        raise ValueError("invalid frozen 28D GuitarSet voicing feature vector")
    return tuple(float(value) for value in values)


def low_total_fret_key(candidate: Candidate) -> tuple:
    frets = [fret for _, _, fret in candidate]
    positive = [fret for fret in frets if fret > 0]
    positive_span = max(positive) - min(positive) if positive else 0
    strings = [string for _, string, _ in candidate]
    return (
        sum(frets),
        max(frets),
        positive_span,
        -sum(fret == 0 for fret in frets),
        max(strings) - min(strings),
        candidate,
    )


def select_negative_candidates(event: DevelopmentEvent) -> tuple[Candidate, ...]:
    alternatives = [candidate for candidate in event.candidates if candidate != event.observed]
    alternatives.sort(
        key=lambda candidate: (
            sha256(
                (
                    "GUITARSET-NEGSEL.v1|"
                    + event.voicing_id
                    + "|"
                    + canonical_candidate(candidate)
                ).encode("ascii")
            ).hexdigest(),
            candidate,
        )
    )
    return tuple(alternatives[:GUITARSET_NEGATIVE_SAMPLE_CAP])


def _development_member(source_member: str) -> bool:
    performer, _, _ = parse_comp_member_identity(source_member)
    return performer in DEVELOPMENT_PERFORMERS


def load_development_events(path: str | Path) -> tuple[tuple[DevelopmentEvent, ...], dict]:
    assert_frozen_protocol()
    path = Path(path)
    observed_archive_sha = archive_sha256(path)
    if observed_archive_sha != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise ValueError("GuitarSet source archive SHA-256 does not match preregistration")

    notes = []
    quarantined = []
    with zipfile.ZipFile(path) as archive:
        members = _validated_comp_members(path, archive)
        development_members = tuple(member for member in members if _development_member(member))
        if len(development_members) != EXPECTED_DEVELOPMENT_RECORDINGS:
            raise ValueError("unexpected GuitarSet DEVELOPMENT recording count")
        # Deliberately do not read VALIDATION or UNTOUCHED_FINAL JAMS bytes here.
        for member in development_members:
            accepted, rejected = extract_comp_jams(member, archive.read(member))
            notes.extend(accepted)
            quarantined.extend(rejected)

    voicings = derive_strum_voicings(notes)
    if len(notes) != EXPECTED_DEVELOPMENT_ACCEPTED_NOTES:
        raise ValueError("GuitarSet DEVELOPMENT accepted-note count drift")
    if len(quarantined) != EXPECTED_DEVELOPMENT_QUARANTINED_NOTES:
        raise ValueError("GuitarSet DEVELOPMENT quarantine count drift")
    if len(voicings) != EXPECTED_DEVELOPMENT_VOICINGS:
        raise ValueError("GuitarSet DEVELOPMENT voicing count drift")

    events: list[DevelopmentEvent] = []
    single_candidate = 0
    candidate_count = 0
    ambiguous_by_performer: dict[str, int] = {performer: 0 for performer in DEVELOPMENT_PERFORMERS}
    single_by_performer: dict[str, int] = {performer: 0 for performer in DEVELOPMENT_PERFORMERS}

    for voicing in voicings:
        performer, _, _ = parse_comp_member_identity(voicing.source_member)
        if performer not in DEVELOPMENT_PERFORMERS:
            raise AssertionError("non-development voicing entered development loader")
        pitches = tuple(pitch for pitch, _, _ in voicing.placements)
        candidates = enumerate_voicing_candidates(pitches)
        if voicing.placements not in candidates:
            raise ValueError("observed GuitarSet DEVELOPMENT voicing missing from candidate set")
        candidate_count += len(candidates)
        if len(candidates) == 1:
            single_candidate += 1
            single_by_performer[performer] += 1
            continue
        if not candidates:
            raise ValueError("GuitarSet DEVELOPMENT voicing has no physical candidates")
        ambiguous_by_performer[performer] += 1
        events.append(
            DevelopmentEvent(
                performer=performer,
                recording_id=voicing.recording_id,
                voicing_id=voicing.voicing_id,
                observed=voicing.placements,
                candidates=candidates,
            )
        )

    events.sort(key=lambda event: (event.performer, event.recording_id, event.voicing_id))
    if len({event.voicing_id for event in events}) != len(events):
        raise AssertionError("duplicate GuitarSet DEVELOPMENT voicing IDs")

    summary = {
        "recordings": len(development_members),
        "accepted_notes": len(notes),
        "quarantined_notes": len(quarantined),
        "derived_voicings": len(voicings),
        "ambiguous_voicings": len(events),
        "single_candidate_voicings": single_candidate,
        "full_candidate_count_across_all_voicings": candidate_count,
        "ambiguous_by_performer": ambiguous_by_performer,
        "single_candidate_by_performer": single_by_performer,
    }
    return tuple(events), summary


def event_identity_sha256(events: Iterable[DevelopmentEvent]) -> str:
    digest = sha256()
    for event in sorted(events, key=lambda item: (item.performer, item.recording_id, item.voicing_id)):
        payload = {
            "performer": event.performer,
            "recording_id": event.recording_id,
            "voicing_id": event.voicing_id,
            "observed": json.loads(canonical_candidate(event.observed)),
            "candidates": [json.loads(canonical_candidate(candidate)) for candidate in event.candidates],
        }
        digest.update(_canonical_json(payload).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def selected_pair_identity(events: Iterable[DevelopmentEvent]) -> tuple[str, int]:
    digest = sha256()
    pair_count = 0
    for event in sorted(events, key=lambda item: (item.performer, item.recording_id, item.voicing_id)):
        observed = canonical_candidate(event.observed)
        for alternative in select_negative_candidates(event):
            payload = {
                "voicing_id": event.voicing_id,
                "observed": observed,
                "alternative": canonical_candidate(alternative),
            }
            digest.update(_canonical_json(payload).encode("utf-8"))
            digest.update(b"\n")
            pair_count += 1
    return digest.hexdigest(), pair_count


def build_training_matrix(events: Iterable[DevelopmentEvent]) -> tuple[np.ndarray, np.ndarray]:
    differences: list[np.ndarray] = []
    for event in events:
        observed = np.asarray(feature_vector(event.observed), dtype=np.float64)
        for alternative in select_negative_candidates(event):
            difference = observed - np.asarray(feature_vector(alternative), dtype=np.float64)
            differences.append(difference)
            differences.append(-difference)
    if not differences:
        raise ValueError("no GuitarSet DEVELOPMENT pairwise training rows")
    X = np.vstack(differences)
    y = np.tile(np.asarray([1, 0], dtype=np.int8), len(differences) // 2)
    if X.ndim != 2 or X.shape[1] != 28 or not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("invalid GuitarSet DEVELOPMENT training matrix")
    return X, y


def fit_preregistered_model(X: np.ndarray, y: np.ndarray):
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            fit_intercept=False,
            class_weight=None,
            solver="lbfgs",
            max_iter=2000,
            random_state=0,
        ),
    )
    model.fit(X, y)
    return model


def evaluate_model(model, events: Iterable[DevelopmentEvent]) -> dict:
    events = tuple(events)
    if not events:
        raise ValueError("no held-out GuitarSet DEVELOPMENT events")

    learned_top1: list[float] = []
    learned_mrr: list[float] = []
    learned_recall3: list[float] = []
    baseline_top1: list[float] = []
    baseline_mrr: list[float] = []
    by_recording: dict[str, list[list[float]]] = {}

    for event in events:
        X = np.asarray([feature_vector(candidate) for candidate in event.candidates], dtype=np.float64)
        scores = np.asarray(model.decision_function(X), dtype=np.float64)
        learned_order = sorted(
            range(len(event.candidates)),
            key=lambda index: (-float(scores[index]), event.candidates[index]),
        )
        baseline_order = sorted(
            range(len(event.candidates)),
            key=lambda index: low_total_fret_key(event.candidates[index]),
        )
        observed_index = event.candidates.index(event.observed)
        learned_rank = learned_order.index(observed_index) + 1
        baseline_rank = baseline_order.index(observed_index) + 1
        lt = float(learned_rank == 1)
        lm = 1.0 / learned_rank
        bt = float(baseline_rank == 1)
        bm = 1.0 / baseline_rank
        learned_top1.append(lt)
        learned_mrr.append(lm)
        learned_recall3.append(float(learned_rank <= 3))
        baseline_top1.append(bt)
        baseline_mrr.append(bm)
        rows = by_recording.setdefault(event.recording_id, [[], [], [], []])
        rows[0].append(lt)
        rows[1].append(lm)
        rows[2].append(bt)
        rows[3].append(bm)

    def mean(values: Iterable[float]) -> float:
        values = tuple(values)
        return float(sum(values) / len(values))

    recording_macro = [mean(mean(row[index]) for row in by_recording.values()) for index in range(4)]
    learned_top1_value = mean(learned_top1)
    learned_mrr_value = mean(learned_mrr)
    baseline_top1_value = mean(baseline_top1)
    baseline_mrr_value = mean(baseline_mrr)
    return {
        "ambiguous_events": len(events),
        "recordings_with_ambiguous_events": len(by_recording),
        "learned_event_top1": learned_top1_value,
        "baseline_event_top1": baseline_top1_value,
        "event_top1_delta": learned_top1_value - baseline_top1_value,
        "learned_event_mrr": learned_mrr_value,
        "baseline_event_mrr": baseline_mrr_value,
        "event_mrr_delta": learned_mrr_value - baseline_mrr_value,
        "learned_event_recall_at_3": mean(learned_recall3),
        "learned_recording_macro_top1": recording_macro[0],
        "learned_recording_macro_mrr": recording_macro[1],
        "baseline_recording_macro_top1": recording_macro[2],
        "baseline_recording_macro_mrr": recording_macro[3],
        "recording_macro_top1_delta": recording_macro[0] - recording_macro[2],
        "recording_macro_mrr_delta": recording_macro[1] - recording_macro[3],
    }


def _model_signature(model, metrics: dict) -> str:
    scaler = model.named_steps["standardscaler"]
    logistic = model.named_steps["logisticregression"]
    payload = {
        "metrics": metrics,
        "scaler_mean_hex": [float(value).hex() for value in scaler.mean_],
        "scaler_scale_hex": [float(value).hex() for value in scaler.scale_],
        "coef_hex": [float(value).hex() for value in logistic.coef_[0]],
        "n_iter": [int(value) for value in logistic.n_iter_],
    }
    return _canonical_sha256(payload)


def _development_gate(source_summary: dict, folds: list[dict], reproduction_runs: int, identical_runs: int) -> tuple[bool, dict]:
    macro_top1_delta = float(sum(fold["event_top1_delta"] for fold in folds) / len(folds))
    macro_mrr_delta = float(sum(fold["event_mrr_delta"] for fold in folds) / len(folds))
    top1_wins = sum(fold["event_top1_delta"] > 0 for fold in folds)
    mrr_wins = sum(fold["event_mrr_delta"] > 0 for fold in folds)
    gate = {
        "minimum_ambiguous_events": {
            "required": 1000,
            "observed": source_summary["ambiguous_voicings"],
            "pass": source_summary["ambiguous_voicings"] >= 1000,
        },
        "macro_event_top1_delta": {
            "required_gte": 0.03,
            "observed": macro_top1_delta,
            "pass": macro_top1_delta >= 0.03,
        },
        "macro_event_mrr_delta": {
            "required_gte": 0.05,
            "observed": macro_mrr_delta,
            "pass": macro_mrr_delta >= 0.05,
        },
        "top1_fold_wins": {"required_gte": 3, "observed": top1_wins, "pass": top1_wins >= 3},
        "mrr_fold_wins": {"required_gte": 3, "observed": mrr_wins, "pass": mrr_wins >= 3},
        "deterministic_reproduction": {
            "required_runs": 10,
            "observed_identical_runs": identical_runs,
            "pass": reproduction_runs == 10 and identical_runs == 10,
        },
    }
    return all(item["pass"] for item in gate.values()), gate


def run_development_fit(path: str | Path, *, reproduction_runs: int = 10) -> tuple[dict, dict | None]:
    if reproduction_runs != 10:
        raise ValueError("preregistered DEVELOPMENT gate requires exactly 10 reproduction runs")
    events, source_summary = load_development_events(path)
    event_hash = event_identity_sha256(events)

    prepared = {}
    pair_identities = {}
    for held_out in DEVELOPMENT_PERFORMERS:
        train_events = tuple(event for event in events if event.performer != held_out)
        held_events = tuple(event for event in events if event.performer == held_out)
        X, y = build_training_matrix(train_events)
        pair_hash, pair_count = selected_pair_identity(train_events)
        prepared[held_out] = (X, y, held_events, len(train_events))
        pair_identities[held_out] = (pair_hash, pair_count)

    first_folds: list[dict] | None = None
    reproduction_signatures: list[str] = []
    for _ in range(reproduction_runs):
        folds: list[dict] = []
        fold_model_signatures = []
        for held_out in DEVELOPMENT_PERFORMERS:
            X, y, held_events, train_event_count = prepared[held_out]
            model = fit_preregistered_model(X, y)
            metrics = evaluate_model(model, held_events)
            pair_hash, pair_count = pair_identities[held_out]
            fold = {
                "held_out_performer": held_out,
                "train_ambiguous_events": train_event_count,
                "held_out_ambiguous_events": metrics["ambiguous_events"],
                "symmetric_training_rows": int(len(y)),
                "selected_pair_count": pair_count,
                "selected_pair_identity_sha256": pair_hash,
                **metrics,
            }
            folds.append(fold)
            fold_model_signatures.append(_model_signature(model, metrics))
        if first_folds is None:
            first_folds = folds
        reproduction_signatures.append(
            _canonical_sha256(
                {
                    "development_event_identity_sha256": event_hash,
                    "fold_pair_identity_sha256": {key: value[0] for key, value in pair_identities.items()},
                    "fold_model_signatures": fold_model_signatures,
                }
            )
        )

    if first_folds is None:
        raise AssertionError("DEVELOPMENT folds were not produced")
    identical_runs = sum(signature == reproduction_signatures[0] for signature in reproduction_signatures)
    development_pass, gate = _development_gate(source_summary, first_folds, reproduction_runs, identical_runs)

    macro = {
        "learned_event_top1": float(sum(fold["learned_event_top1"] for fold in first_folds) / 4),
        "baseline_event_top1": float(sum(fold["baseline_event_top1"] for fold in first_folds) / 4),
        "event_top1_delta": float(sum(fold["event_top1_delta"] for fold in first_folds) / 4),
        "learned_event_mrr": float(sum(fold["learned_event_mrr"] for fold in first_folds) / 4),
        "baseline_event_mrr": float(sum(fold["baseline_event_mrr"] for fold in first_folds) / 4),
        "event_mrr_delta": float(sum(fold["event_mrr_delta"] for fold in first_folds) / 4),
        "learned_event_recall_at_3": float(sum(fold["learned_event_recall_at_3"] for fold in first_folds) / 4),
        "recording_macro_top1_delta": float(sum(fold["recording_macro_top1_delta"] for fold in first_folds) / 4),
        "recording_macro_mrr_delta": float(sum(fold["recording_macro_mrr_delta"] for fold in first_folds) / 4),
        "top1_fold_wins": sum(fold["event_top1_delta"] > 0 for fold in first_folds),
        "mrr_fold_wins": sum(fold["event_mrr_delta"] > 0 for fold in first_folds),
    }

    artifact = None
    sealed_model_reproduction = None
    if development_pass:
        X_full, y_full = build_training_matrix(events)
        full_pair_hash, full_pair_count = selected_pair_identity(events)
        full_signatures = []
        full_models = []
        for _ in range(10):
            model = fit_preregistered_model(X_full, y_full)
            scaler = model.named_steps["standardscaler"]
            logistic = model.named_steps["logisticregression"]
            signature_payload = {
                "scaler_mean_hex": [float(value).hex() for value in scaler.mean_],
                "scaler_scale_hex": [float(value).hex() for value in scaler.scale_],
                "coef_hex": [float(value).hex() for value in logistic.coef_[0]],
                "n_iter": [int(value) for value in logistic.n_iter_],
            }
            full_signatures.append(_canonical_sha256(signature_payload))
            full_models.append(model)
        if len(set(full_signatures)) != 1:
            raise AssertionError("sealed DEVELOPMENT model is not deterministic 10/10")
        model = full_models[0]
        scaler = model.named_steps["standardscaler"]
        logistic = model.named_steps["logisticregression"]
        artifact_core = {
            "schema": "st-guitar-guitarset-observed-voicing-development-model-v1",
            "model_version": "GUITARSET-OBSERVED-VOICING-MODEL.v1",
            "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
            "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
            "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
            "split_version": "GUITARSET-SPLIT.v1",
            "training_role": "DEVELOPMENT",
            "training_performers": list(DEVELOPMENT_PERFORMERS),
            "ambiguous_event_count": len(events),
            "selected_pair_count": full_pair_count,
            "symmetric_training_row_count": int(len(y_full)),
            "selected_pair_identity_sha256": full_pair_hash,
            "pipeline": {
                "scaler": "StandardScaler",
                "estimator": "LogisticRegression",
                "params": {
                    "C": 1.0,
                    "fit_intercept": False,
                    "class_weight": None,
                    "solver": "lbfgs",
                    "max_iter": 2000,
                    "random_state": 0,
                },
            },
            "parameters": {
                "scaler_mean_hex": [float(value).hex() for value in scaler.mean_],
                "scaler_scale_hex": [float(value).hex() for value in scaler.scale_],
                "logistic_coef_hex": [float(value).hex() for value in logistic.coef_[0]],
                "n_iter": [int(value) for value in logistic.n_iter_],
            },
            "scoring": "dot((features-mean)/scale, coef)",
            "validation_only_artifact": True,
            "checkpoint_authorized": False,
            "runtime_connection_authorized": False,
        }
        artifact = {**artifact_core, "artifact_sha256": _canonical_sha256(artifact_core)}
        sealed_model_reproduction = {
            "runs": 10,
            "identical_runs": 10,
            "parameter_signature_sha256": full_signatures[0],
        }

    report_core = {
        "schema": "st-guitar-guitarset-observed-voicing-development-evidence-v1",
        "status": "DEVELOPMENT_PASS_MODEL_SEALED_VALIDATION_CLOSED" if development_pass else "DEVELOPMENT_FAIL_STOP",
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "prereg_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "feature_schema_sha256": EXPECTED_FEATURE_SCHEMA_SHA256,
        "split_version": "GUITARSET-SPLIT.v1",
        "development_performers": list(DEVELOPMENT_PERFORMERS),
        "validation_performer_opened": False,
        "untouched_final_performer_opened": False,
        "development_source_counts": source_summary,
        "development_event_identity_sha256": event_hash,
        "folds": first_folds,
        "macro": macro,
        "gate": gate,
        "deterministic_reproduction_signature_sha256": reproduction_signatures[0],
        "development_pass": development_pass,
        "sealed_development_model_artifact_sha256": artifact["artifact_sha256"] if artifact else None,
        "sealed_development_model_reproduction": sealed_model_reproduction,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "validation_access_authorized": False,
        "final_access_authorized": False,
        "next_gate": "OBSERVED_VOICING_MODEL_VALIDATION_ONE_SHOT" if development_pass else "STOP_DEVELOPMENT_GATE_FAILED",
    }
    report = {**report_core, "evidence_sha256": _canonical_sha256(report_core)}
    return report, artifact


def verify_sealed_json(payload: dict, hash_field: str) -> None:
    claimed = payload.get(hash_field)
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("missing or invalid sealed JSON SHA-256")
    core = {key: value for key, value in payload.items() if key != hash_field}
    if _canonical_sha256(core) != claimed:
        raise ValueError("sealed JSON SHA-256 mismatch")
