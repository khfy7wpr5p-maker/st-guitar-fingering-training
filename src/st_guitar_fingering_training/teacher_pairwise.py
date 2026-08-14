from __future__ import annotations

from hashlib import sha256
from typing import Iterable

from .teacher_task_sampling import TeacherAnnotationBatch


PAIRWISE_CHOICE_SCHEMA = "st-guitar-stage7g-pairwise-choice-export-v1"
PAIRWISE_MANIFEST_SCHEMA = "st-guitar-stage7g-teacher-pairwise-manifest-v1"
PAIRWISE_AUDIT_SCHEMA = "st-guitar-stage7g-pairwise-audit-v1"
PAIRWISE_RESPONSES = ("A", "B", "EQUAL_OR_UNSURE")


def _candidate_id(task, candidate) -> str:
    try:
        index = task.candidates.index(candidate)
    except ValueError as exc:
        raise ValueError("specialist prediction is not in the deterministic candidate set") from exc
    return f"candidate_{index + 1:04d}"


def _placements(candidate) -> list[dict[str, int]]:
    return [
        {"pitch_midi": int(pitch), "string": int(string), "fret": int(fret)}
        for pitch, string, fret in candidate
    ]


def _blind_style_order(task_id: str) -> tuple[str, str]:
    """Deterministically hide which side came from which specialist.

    The order depends only on the opaque task id and is fixed before any teacher
    response. It therefore cannot adapt to labels and does not expose model scores.
    """

    digest = sha256((task_id + "|stage7g-pairwise-v1").encode()).digest()
    if digest[0] & 1:
        return "compact", "open_low"
    return "open_low", "compact"


def build_pairwise_teacher_manifests(
    batch: TeacherAnnotationBatch,
    *,
    completed_task_ids: Iterable[str] = (),
) -> tuple[dict, dict]:
    """Build blind A/B teacher tasks from frozen specialist disagreements.

    The teacher-facing manifest contains only two physical TAB candidates labelled
    A and B. Specialist identities, model scores, source identity, family identity,
    and observed source voicing remain outside the teacher channel. A separate audit
    maps A/B back to the frozen specialist predictions after annotation.
    """

    completed = {str(value) for value in completed_task_ids}
    task_ids = {task.event_id for task in batch.tasks}
    unknown = completed - task_ids
    if unknown:
        raise ValueError("completed_task_ids contains tasks outside the sealed batch")
    if len(batch.tasks) != len(batch.diagnostics):
        raise ValueError("task/diagnostic count mismatch")

    teacher_rows: list[dict] = []
    audit_rows: list[dict] = []

    for task, diagnostic in zip(batch.tasks, batch.diagnostics):
        if task.event_id != diagnostic.event_id:
            raise ValueError("task/diagnostic event id mismatch")
        if task.event_id in completed:
            continue
        predictions = dict(diagnostic.specialist_top1)
        if set(predictions) != {"open_low", "compact", "mid_position", "high_position"}:
            raise ValueError("pairwise audit requires exactly the four stateless specialists")
        open_low = predictions["open_low"]
        compact = predictions["compact"]
        if open_low == compact or not diagnostic.open_low_compact_disagreement:
            raise ValueError("pairwise teacher task must be a frozen two-specialist disagreement")

        option_a_style, option_b_style = _blind_style_order(task.event_id)
        option_a = predictions[option_a_style]
        option_b = predictions[option_b_style]
        option_a_candidate_id = _candidate_id(task, option_a)
        option_b_candidate_id = _candidate_id(task, option_b)

        teacher_rows.append({
            "task_id": task.event_id,
            "pitches_midi": list(task.pitches_midi),
            "tuning": list(task.tuning),
            "options": [
                {"option_id": "A", "placements": _placements(option_a)},
                {"option_id": "B", "placements": _placements(option_b)},
            ],
            "responses": list(PAIRWISE_RESPONSES),
        })
        audit_rows.append({
            "task_id": task.event_id,
            "family_id": diagnostic.family_id,
            "source_sha256": diagnostic.source_sha256,
            "source_origin": diagnostic.source_origin,
            "A": {
                "specialist": option_a_style,
                "candidate_id": option_a_candidate_id,
                "placements": _placements(option_a),
            },
            "B": {
                "specialist": option_b_style,
                "candidate_id": option_b_candidate_id,
                "placements": _placements(option_b),
            },
        })

    if not teacher_rows:
        raise ValueError("no pairwise tasks remain after completed-task exclusion")

    teacher_manifest = {
        "schema": PAIRWISE_MANIFEST_SCHEMA,
        "annotation_blinded": True,
        "model_identity": "withheld",
        "model_scores": "withheld",
        "observed_source_voicing": "withheld",
        "source_identity": "withheld",
        "choice_semantics": "pairwise_guitaristic_preference",
        "allowed_responses": list(PAIRWISE_RESPONSES),
        "task_count": len(teacher_rows),
        "tasks": teacher_rows,
    }
    internal_audit = {
        "schema": PAIRWISE_AUDIT_SCHEMA,
        "teacher_facing": False,
        "target_voicing_used_for_pair_construction": False,
        "observed_string_fret_used_for_pair_construction": False,
        "pair_source": "frozen_open_low_and_compact_top1",
        "completed_full_candidate_tasks_excluded": len(completed),
        "task_count": len(audit_rows),
        "rows": audit_rows,
    }
    return teacher_manifest, internal_audit


def validate_pairwise_choice_export(payload: dict, teacher_manifest: dict) -> dict[str, str]:
    """Validate a teacher-facing pairwise export without interpreting model identity."""

    if payload.get("schema") != PAIRWISE_CHOICE_SCHEMA:
        raise ValueError("unexpected pairwise choice export schema")
    if payload.get("annotation_blinded") is not True:
        raise ValueError("pairwise annotation must remain blind")
    annotator_id = str(payload.get("annotator_id", "")).strip()
    if not annotator_id:
        raise ValueError("annotator_id is required")
    if teacher_manifest.get("schema") != PAIRWISE_MANIFEST_SCHEMA:
        raise ValueError("unexpected pairwise teacher manifest schema")

    known_ids = {row["task_id"] for row in teacher_manifest.get("tasks", [])}
    choices = payload.get("choices")
    if not isinstance(choices, list):
        raise ValueError("choices must be a list")

    out: dict[str, str] = {}
    for row in choices:
        task_id = str(row.get("task_id", ""))
        response = str(row.get("response", ""))
        if task_id not in known_ids:
            raise ValueError("pairwise export contains an unknown task_id")
        if task_id in out:
            raise ValueError("pairwise export contains duplicate task_id")
        if response not in PAIRWISE_RESPONSES:
            raise ValueError("pairwise response must be A, B, or EQUAL_OR_UNSURE")
        out[task_id] = response
    return out
