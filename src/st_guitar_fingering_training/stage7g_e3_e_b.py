from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping

import numpy as np

from .curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    STAGE7G_E3_LEVELS,
    stage7g_e3_curriculum_level,
    stage7g_e3_feature_record,
)
from .dataset import Voicing, valid_chord_voicings
from .stage7g_e3_e_a3 import A3_STYLES, _event_id, _winner
from .target_free_musicxml import TargetFreeSource
from .teacher_gold import TeacherAnnotationTask, build_teacher_annotation_task


E3E_B_TASK_QUOTA = 240
E3E_B_EXPECTED_DISAGREEMENT_EVENTS = 1937
E3E_B_EXPECTED_DISAGREEMENT_FAMILIES = 24
E3E_B_EXPECTED_A3_EVENT_SET_SHA256 = (
    "2d2d712b5c95b19f249aa950947062d78ab7f774a9b027b9b2386ef29d833ee1"
)
E3E_B_RESPONSES = ("A", "B", "EQUAL_OR_UNSURE")
E3E_B_TEACHER_MANIFEST_SCHEMA = "st-guitar-stage7g-e3-e-b-teacher-manifest-v1"
E3E_B_INTERNAL_AUDIT_SCHEMA = "st-guitar-stage7g-e3-e-b-internal-audit-v1"
E3E_B_RESPONSE_SCHEMA = "st-guitar-stage7g-e3-e-b-teacher-responses-v1"

# Frozen before E3-E Teacher-GOLD answers exist.
E3E_B_EVALUATION_GATE = {
    "required_completed_tasks": 240,
    "minimum_decisive_events": 200,
    "minimum_evaluable_families": 20,
    "final_development_fit_rows": 399,
    "feature_count": 40,
    "feature_name_sha256": "6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3",
    "model": {
        "pipeline": ["StandardScaler", "LogisticRegression"],
        "max_iter": 2000,
        "class_weight": None,
        "C": 1.0,
        "solver": "lbfgs",
        "random_state": 0,
        "positive_class": "COMPACT",
        "default_decision": "OPEN_LOW",
    },
    "compact_probability_threshold": 0.5,
    "threshold_origin": "mode_of_frozen_E3D_outer_selected_thresholds_[0.5,0.5,0.6,0.5,0.5]",
    "threshold_search_on_e3e": False,
    "pass_requirements": {
        "event_accuracy_delta_gt": 0.0,
        "macro_family_accuracy_delta_gt": 0.0,
        "compact_precision_gte": 2.0 / 3.0,
        "compact_true_positives_gt_false_positives": True,
        "family_wins_gt_losses": True,
    },
}


@dataclass(frozen=True)
class E3EBValidationItem:
    task: TeacherAnnotationTask
    curriculum_level: str
    feature_values: tuple[float, ...]
    open_low_top1: Voicing
    compact_top1: Voicing

    @property
    def feature_record(self) -> dict[str, float]:
        if len(self.feature_values) != len(STAGE7G_E3_FEATURE_NAMES):
            raise ValueError("E3-E-B feature dimension mismatch")
        return dict(zip(STAGE7G_E3_FEATURE_NAMES, self.feature_values))


def _stable_family_order(family_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(family_ids), key=lambda value: sha256(value.encode()).hexdigest()))


def _blind_style_order(task_id: str) -> tuple[str, str]:
    digest = sha256((task_id + "|stage7g-e3-e-b-pairwise-v1").encode()).digest()
    if digest[0] & 1:
        return "compact", "open_low"
    return "open_low", "compact"


def _placements(candidate: Voicing) -> list[dict[str, int]]:
    return [
        {"pitch_midi": int(pitch), "string": int(string), "fret": int(fret)}
        for pitch, string, fret in candidate
    ]


def build_e3e_disagreement_pool(
    sources: Iterable[TargetFreeSource],
    *,
    source_origins: Mapping[str, str],
    specialist_models: Mapping[str, object],
) -> tuple[E3EBValidationItem, ...]:
    """Reconstruct the exact A3 disagreement set with frozen 40-feature diagnostics.

    This is target-blind. It never accepts a Teacher response, observed TAB target,
    router score, E3-E model, or threshold. The exact A3 count/family/digest guard
    prevents a later batch from silently drifting away from the sealed inventory.
    """

    if set(specialist_models) != set(A3_STYLES):
        raise ValueError("E3-E-B requires exactly frozen open_low and compact specialists")
    source_rows = tuple(sources)
    if not source_rows:
        raise ValueError("E3-E-B requires eligible target-free sources")
    expected_hashes = {source.source_sha256.lower() for source in source_rows}
    supplied_hashes = {str(key).lower() for key in source_origins}
    if supplied_hashes != expected_hashes:
        raise ValueError("source_origins must map exactly the supplied E3-E source hashes")
    origins = {str(key).lower(): str(value) for key, value in source_origins.items()}
    if any(not value.strip() for value in origins.values()):
        raise ValueError("E3-E source origins must be non-empty")

    event_ids: list[str] = []
    items: list[E3EBValidationItem] = []
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
            task = build_teacher_annotation_task(
                source_sha256=source.source_sha256.lower(),
                source_origin=origins[source.source_sha256.lower()],
                family_id=source.family_id,
                event_id=event_id,
                pitches_midi=event.pitches_midi,
                tuning=event.tuning,
            )
            if task.candidates != candidates:
                raise AssertionError("E3-E-B deterministic candidate boundary drift")

            record = stage7g_e3_feature_record(
                task.pitches_midi,
                task.tuning,
                open_low,
                compact,
            )
            values = np.asarray(
                [record[name] for name in STAGE7G_E3_FEATURE_NAMES],
                dtype=np.float64,
            )
            if values.shape != (40,) or not np.isfinite(values).all():
                raise ValueError("non-finite or wrong-dimensional E3-E-B feature vector")
            geometry_delta = {
                name: record[f"compact_minus_open__{name}"]
                for name in STAGE7G_E3_GEOMETRY_NAMES
            }
            level = stage7g_e3_curriculum_level(
                chord_size=len(task.pitches_midi),
                candidate_count=len(task.candidates),
                geometry_delta=geometry_delta,
            )
            items.append(E3EBValidationItem(
                task=task,
                curriculum_level=level,
                feature_values=tuple(float(value) for value in values),
                open_low_top1=open_low,
                compact_top1=compact,
            ))
            event_ids.append(event_id)

    if len(event_ids) != len(set(event_ids)):
        raise ValueError("duplicate E3-E-B disagreement event id")
    family_ids = {item.task.family_id for item in items}
    digest = sha256("\n".join(sorted(event_ids)).encode()).hexdigest()
    if len(items) != E3E_B_EXPECTED_DISAGREEMENT_EVENTS:
        raise AssertionError("E3-E-B disagreement count drift from sealed A3")
    if len(family_ids) != E3E_B_EXPECTED_DISAGREEMENT_FAMILIES:
        raise AssertionError("E3-E-B disagreement family count drift from sealed A3")
    if digest != E3E_B_EXPECTED_A3_EVENT_SET_SHA256:
        raise AssertionError("E3-E-B disagreement event-set digest drift from sealed A3")
    return tuple(items)


def select_e3e_validation_batch(
    pool: Iterable[E3EBValidationItem],
) -> tuple[E3EBValidationItem, ...]:
    """Select exactly 240 tasks in deterministic family-balanced round-robin rounds.

    The nominal design is 10 tasks x the 24 disagreement families. Families with
    fewer than 10 events are exhausted naturally and their unused slots are filled
    by later round-robin rounds from the remaining families. No label or model
    outcome participates in selection. Curriculum level remains diagnostic only.
    """

    items = tuple(pool)
    if len(items) != E3E_B_EXPECTED_DISAGREEMENT_EVENTS:
        raise ValueError("E3-E-B selection requires the exact sealed A3 disagreement pool")
    event_ids = [item.task.event_id for item in items]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("E3-E-B pool contains duplicate event ids")

    by_family: dict[str, list[E3EBValidationItem]] = defaultdict(list)
    for item in items:
        by_family[item.task.family_id].append(item)
    if len(by_family) != E3E_B_EXPECTED_DISAGREEMENT_FAMILIES:
        raise ValueError("E3-E-B pool must contain exactly 24 disagreement families")
    for family in by_family:
        by_family[family].sort(
            key=lambda item: sha256(item.task.event_id.encode()).hexdigest()
        )

    families = _stable_family_order(by_family)
    selected: list[E3EBValidationItem] = []
    cursor = 0
    while len(selected) < E3E_B_TASK_QUOTA:
        progressed = False
        for family in families:
            rows = by_family[family]
            if cursor >= len(rows):
                continue
            selected.append(rows[cursor])
            progressed = True
            if len(selected) >= E3E_B_TASK_QUOTA:
                break
        if not progressed:
            break
        cursor += 1

    if len(selected) != E3E_B_TASK_QUOTA:
        raise ValueError("sealed E3-E disagreement pool cannot fill the frozen 240-task quota")
    if len({item.task.family_id for item in selected}) != E3E_B_EXPECTED_DISAGREEMENT_FAMILIES:
        raise AssertionError("E3-E-B selection failed to cover all 24 disagreement families")
    if len({item.task.event_id for item in selected}) != E3E_B_TASK_QUOTA:
        raise AssertionError("E3-E-B selected duplicate task ids")
    return tuple(selected)


def e3e_teacher_manifest(batch: Iterable[E3EBValidationItem]) -> dict:
    items = tuple(batch)
    if len(items) != E3E_B_TASK_QUOTA:
        raise ValueError("E3-E-B teacher manifest requires exactly 240 sealed tasks")
    tasks = []
    for item in items:
        order = _blind_style_order(item.task.event_id)
        proposals = {"open_low": item.open_low_top1, "compact": item.compact_top1}
        tasks.append({
            "task_id": item.task.event_id,
            "pitches_midi": list(item.task.pitches_midi),
            "tuning": list(item.task.tuning),
            "options": [
                {"option_id": "A", "placements": _placements(proposals[order[0]])},
                {"option_id": "B", "placements": _placements(proposals[order[1]])},
            ],
            "responses": list(E3E_B_RESPONSES),
        })
    return {
        "schema": E3E_B_TEACHER_MANIFEST_SCHEMA,
        "stage": "7G-E3-E-B",
        "annotation_blinded": True,
        "choice_semantics": "pairwise_guitaristic_preference_untouched_validation",
        "source_identity": "withheld",
        "family_identity": "withheld",
        "specialist_identity": "withheld",
        "curriculum_level": "withheld",
        "feature_values": "withheld",
        "model_prediction": "withheld",
        "threshold": "withheld",
        "task_count": len(tasks),
        "tasks": tasks,
    }


def e3e_response_template(batch: Iterable[E3EBValidationItem]) -> dict:
    items = tuple(batch)
    if len(items) != E3E_B_TASK_QUOTA:
        raise ValueError("E3-E-B response template requires exactly 240 sealed tasks")
    return {
        "schema": E3E_B_RESPONSE_SCHEMA,
        "stage": "7G-E3-E-C",
        "allowed_choices": list(E3E_B_RESPONSES),
        "task_count": len(items),
        "choices": [
            {"task_id": item.task.event_id, "choice": ""}
            for item in items
        ],
    }


def e3e_internal_audit(batch: Iterable[E3EBValidationItem]) -> dict:
    items = tuple(batch)
    if len(items) != E3E_B_TASK_QUOTA:
        raise ValueError("E3-E-B internal audit requires exactly 240 sealed tasks")
    rows = []
    for item in items:
        order = _blind_style_order(item.task.event_id)
        rows.append({
            "event_id": item.task.event_id,
            "family_id": item.task.family_id,
            "source_sha256": item.task.source_sha256,
            "source_origin": item.task.source_origin,
            "curriculum_level": item.curriculum_level,
            "candidate_count": len(item.task.candidates),
            "blind_A_specialist": order[0],
            "blind_B_specialist": order[1],
            "open_low": _placements(item.open_low_top1),
            "compact": _placements(item.compact_top1),
            "feature_record": item.feature_record,
        })
    family_counts = {
        family: sum(item.task.family_id == family for item in items)
        for family in sorted({item.task.family_id for item in items})
    }
    level_counts = {
        level: sum(item.curriculum_level == level for item in items)
        for level in STAGE7G_E3_LEVELS
    }
    return {
        "schema": E3E_B_INTERNAL_AUDIT_SCHEMA,
        "stage": "7G-E3-E-B",
        "teacher_facing": False,
        "target_voicing_used_for_generation": False,
        "teacher_response_used_for_generation": False,
        "router_score_used_for_generation": False,
        "e3e_model_used_for_generation": False,
        "threshold_used_for_generation": False,
        "selection_policy": "240_tasks_family_balanced_round_robin_all_24_disagreement_families",
        "feature_names": list(STAGE7G_E3_FEATURE_NAMES),
        "feature_count": len(STAGE7G_E3_FEATURE_NAMES),
        "selected_events": len(rows),
        "selected_families": len(family_counts),
        "family_counts": family_counts,
        "level_counts": level_counts,
        "evaluation_gate": E3E_B_EVALUATION_GATE,
        "rows": rows,
    }


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
