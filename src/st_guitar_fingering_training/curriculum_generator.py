from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

from .curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    STAGE7G_E3_LEVELS,
    STAGE7G_E3_RULE_PROPERTY_TARGETS,
    stage7g_e3_curriculum_level,
    stage7g_e3_feature_record,
    stage7g_e3_proposal_geometry,
    stage7g_e3_rule_property_value,
)
from .dataset import Voicing
from .teacher_gold import TeacherAnnotationTask
from .teacher_task_sampling import AnnotationSamplingEnvelope


STAGE7G_E3_TEACHER_MANIFEST_SCHEMA = "st-guitar-stage7g-e3-teacher-pairwise-manifest-v1"
STAGE7G_E3_INTERNAL_AUDIT_SCHEMA = "st-guitar-stage7g-e3-curriculum-audit-v1"
STAGE7G_E3_RULE_PROPERTY_SCHEMA = "st-guitar-stage7g-e3-rule-property-records-v1"
STAGE7G_E3_TEACHER_RESPONSES = ("A", "B", "EQUAL_OR_UNSURE")


@dataclass(frozen=True)
class Stage7GE3CurriculumItem:
    task: TeacherAnnotationTask
    curriculum_level: str
    feature_values: tuple[float, ...]
    open_low_top1: Voicing
    compact_top1: Voicing

    @property
    def feature_record(self) -> dict[str, float]:
        if len(self.feature_values) != len(STAGE7G_E3_FEATURE_NAMES):
            raise ValueError("Stage 7G-E3 curriculum feature dimension mismatch")
        return dict(zip(STAGE7G_E3_FEATURE_NAMES, self.feature_values))


def _stable_family_order(family_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(family_ids), key=lambda value: sha256(value.encode()).hexdigest()))


def _blind_style_order(task_id: str) -> tuple[str, str]:
    digest = sha256((task_id + "|stage7g-e3-pairwise-v1").encode()).digest()
    if digest[0] & 1:
        return "compact", "open_low"
    return "open_low", "compact"


def _placements(candidate: Voicing) -> list[dict[str, int]]:
    return [
        {"pitch_midi": int(pitch), "string": int(string), "fret": int(fret)}
        for pitch, string, fret in candidate
    ]


def _proposal_map(envelope: AnnotationSamplingEnvelope) -> dict[str, Voicing]:
    if envelope.task.event_id != envelope.diagnostic.event_id:
        raise ValueError("Stage 7G-E3 task/diagnostic event id mismatch")
    predictions = dict(envelope.diagnostic.specialist_top1)
    if set(predictions) != {"open_low", "compact", "mid_position", "high_position"}:
        raise ValueError("Stage 7G-E3 requires exactly the four frozen stateless specialist predictions")
    if len(envelope.diagnostic.specialist_top1) != 4:
        raise ValueError("Stage 7G-E3 specialist predictions contain duplicate keys")
    return predictions


def build_stage7g_e3_curriculum_pool(
    envelopes: Iterable[AnnotationSamplingEnvelope],
) -> tuple[Stage7GE3CurriculumItem, ...]:
    """Build the E3 curriculum pool without teacher labels or observed TAB targets.

    Only frozen open_low-vs-compact disagreements are eligible. Difficulty is assigned
    from the E3-A target-blind geometry contract. No teacher response is accepted by
    this API, so a sealed pool cannot adapt to annotation outcomes.
    """

    rows = tuple(envelopes)
    if not rows:
        raise ValueError("no Stage 7G-E3 sampling envelopes")

    seen_event_ids: set[str] = set()
    out: list[Stage7GE3CurriculumItem] = []
    for envelope in rows:
        task = envelope.task
        if task.event_id in seen_event_ids:
            raise ValueError("duplicate Stage 7G-E3 event_id")
        seen_event_ids.add(task.event_id)

        predictions = _proposal_map(envelope)
        open_low = predictions["open_low"]
        compact = predictions["compact"]
        if open_low == compact:
            continue
        if not envelope.diagnostic.open_low_compact_disagreement:
            raise ValueError("Stage 7G-E3 diagnostic disagreement flag is inconsistent")

        record = stage7g_e3_feature_record(
            task.pitches_midi,
            task.tuning,
            open_low,
            compact,
        )
        geometry_delta = {
            name: record[f"compact_minus_open__{name}"]
            for name in STAGE7G_E3_GEOMETRY_NAMES
        }
        level = stage7g_e3_curriculum_level(
            chord_size=len(task.pitches_midi),
            candidate_count=len(task.candidates),
            geometry_delta=geometry_delta,
        )
        out.append(Stage7GE3CurriculumItem(
            task=task,
            curriculum_level=level,
            feature_values=tuple(record[name] for name in STAGE7G_E3_FEATURE_NAMES),
            open_low_top1=open_low,
            compact_top1=compact,
        ))

    if not out:
        raise ValueError("no open_low-vs-compact disagreements eligible for Stage 7G-E3")
    return tuple(out)


def select_stage7g_e3_curriculum_batch(
    pool: Iterable[Stage7GE3CurriculumItem],
    *,
    max_per_level: Mapping[str, int],
) -> tuple[Stage7GE3CurriculumItem, ...]:
    """Select a deterministic family-balanced batch independently inside each level.

    The caller must provide an explicit quota for every L1..L4 level. There are no
    data-dependent default quotas. Selection uses only level, family, and event id.
    """

    items = tuple(pool)
    if not items:
        raise ValueError("cannot select an empty Stage 7G-E3 curriculum pool")
    if set(max_per_level) != set(STAGE7G_E3_LEVELS):
        raise ValueError("Stage 7G-E3 max_per_level must specify exactly L1..L4")
    quotas: dict[str, int] = {}
    for level in STAGE7G_E3_LEVELS:
        value = max_per_level[level]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Stage 7G-E3 level quotas must be non-negative integers")
        quotas[level] = value
    if not any(quotas.values()):
        raise ValueError("Stage 7G-E3 requires at least one positive level quota")

    event_ids = [item.task.event_id for item in items]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Stage 7G-E3 curriculum pool contains duplicate event ids")
    if any(item.curriculum_level not in STAGE7G_E3_LEVELS for item in items):
        raise ValueError("Stage 7G-E3 curriculum pool contains an unknown level")

    selected: list[Stage7GE3CurriculumItem] = []
    for level in STAGE7G_E3_LEVELS:
        quota = quotas[level]
        if quota == 0:
            continue
        level_items = tuple(item for item in items if item.curriculum_level == level)
        if not level_items:
            continue
        family_ids = _stable_family_order(item.task.family_id for item in level_items)
        by_family: dict[str, list[Stage7GE3CurriculumItem]] = defaultdict(list)
        for item in level_items:
            by_family[item.task.family_id].append(item)
        for family in by_family:
            by_family[family].sort(
                key=lambda item: sha256(item.task.event_id.encode()).hexdigest()
            )

        cursor = 0
        level_selected = 0
        while level_selected < quota:
            progressed = False
            for family in family_ids:
                family_items = by_family[family]
                if cursor >= len(family_items):
                    continue
                selected.append(family_items[cursor])
                level_selected += 1
                progressed = True
                if level_selected >= quota:
                    break
            if not progressed:
                break
            cursor += 1

    if not selected:
        raise ValueError("Stage 7G-E3 quotas selected no tasks")
    selected_ids = [item.task.event_id for item in selected]
    if len(selected_ids) != len(set(selected_ids)):
        raise AssertionError("Stage 7G-E3 selected one task more than once")
    return tuple(selected)


def stage7g_e3_teacher_manifest(
    batch: Iterable[Stage7GE3CurriculumItem],
) -> dict:
    """Create a blinded A/B teacher manifest with curriculum metadata withheld."""

    items = tuple(batch)
    if not items:
        raise ValueError("no Stage 7G-E3 curriculum items for teacher manifest")
    tasks: list[dict] = []
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
            "responses": list(STAGE7G_E3_TEACHER_RESPONSES),
        })
    return {
        "schema": STAGE7G_E3_TEACHER_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "choice_semantics": "pairwise_guitaristic_preference",
        "source_identity": "withheld",
        "family_identity": "withheld",
        "specialist_identity": "withheld",
        "curriculum_level": "withheld",
        "feature_values": "withheld",
        "observed_source_voicing": "withheld",
        "task_count": len(tasks),
        "tasks": tasks,
    }


def stage7g_e3_internal_audit(
    batch: Iterable[Stage7GE3CurriculumItem],
) -> dict:
    """Create the non-teacher-facing audit needed to reproduce a sealed E3 batch."""

    items = tuple(batch)
    if not items:
        raise ValueError("no Stage 7G-E3 curriculum items for audit")
    rows: list[dict] = []
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
    return {
        "schema": STAGE7G_E3_INTERNAL_AUDIT_SCHEMA,
        "teacher_facing": False,
        "target_voicing_used_for_generation": False,
        "observed_string_fret_used_for_generation": False,
        "teacher_response_used_for_generation": False,
        "family_balanced_within_level": True,
        "feature_names": list(STAGE7G_E3_FEATURE_NAMES),
        "feature_count": len(STAGE7G_E3_FEATURE_NAMES),
        "selected_events": len(rows),
        "level_counts": {
            level: sum(item.curriculum_level == level for item in items)
            for level in STAGE7G_E3_LEVELS
        },
        "rows": rows,
    }


def stage7g_e3_rule_property_records(
    batch: Iterable[Stage7GE3CurriculumItem],
) -> dict:
    """Generate descriptive L1/L2 geometry targets; never Teacher-GOLD preference."""

    items = tuple(batch)
    records: list[dict] = []
    for item in items:
        if item.curriculum_level not in ("L1", "L2"):
            continue
        open_values = dict(zip(
            STAGE7G_E3_GEOMETRY_NAMES,
            stage7g_e3_proposal_geometry(item.open_low_top1),
        ))
        compact_values = dict(zip(
            STAGE7G_E3_GEOMETRY_NAMES,
            stage7g_e3_proposal_geometry(item.compact_top1),
        ))
        for property_name in STAGE7G_E3_RULE_PROPERTY_TARGETS:
            records.append({
                "event_id": item.task.event_id,
                "family_id": item.task.family_id,
                "curriculum_level": item.curriculum_level,
                "provenance": "RULE_DERIVED_PROPERTY",
                "target_name": property_name,
                "target_value": stage7g_e3_rule_property_value(
                    property_name,
                    open_values,
                    compact_values,
                ),
                "teacher_gold": False,
            })
    return {
        "schema": STAGE7G_E3_RULE_PROPERTY_SCHEMA,
        "semantic_boundary": "descriptive_geometry_only_not_guitaristic_preference",
        "teacher_gold": False,
        "record_count": len(records),
        "records": records,
    }
