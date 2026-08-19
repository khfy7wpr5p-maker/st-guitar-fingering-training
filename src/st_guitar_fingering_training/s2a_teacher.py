from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
from math import isfinite

from .finger_assignments import StandardFingering, generate_standard_fingerings
from .s2a_features import S2A_PROTOCOL_VERSION, assignment_feature_vector


S2A_FIRST_PASS_PROVENANCE = "S2A_STATIC_NATURALNESS_FIRST_PASS"
S2A_REPEAT_PROVENANCE = "S2A_STATIC_NATURALNESS_REPEAT"
S2A_FINAL_PROVENANCE = "S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL"
S2A_RESPONSES = ("A", "B", "EQUAL_OR_UNSURE")

S2A_TEACHER_MANIFEST_SCHEMA = "st-guitar-s2a-teacher-pair-manifest-v1"
S2A_INTERNAL_AUDIT_SCHEMA = "st-guitar-s2a-pair-audit-v1"
S2A_CHOICE_EXPORT_SCHEMA = "st-guitar-s2a-choice-export-v1"
S2A_REPEAT_AUDIT_SCHEMA = "st-guitar-s2a-repeat-audit-v1"

_PAIR_TYPES = ("FINGER_ONLY", "MIXED")
_DISTANCE_STRATA = ("NEAR", "MID", "FAR")


def _opaque_hash(prefix: str, payload: str) -> str:
    return f"{prefix}{sha256(payload.encode('utf-8')).hexdigest()}"


def _assignment_payload(assignment: StandardFingering, option_id: str) -> dict:
    return {
        "option_id": option_id,
        "assignment_id": assignment.assignment_id,
        "placements": [
            {
                "pitch_midi": int(pitch),
                "string": int(string),
                "fret": int(fret),
                "finger": int(finger),
            }
            for pitch, string, fret, finger in assignment.placements
        ],
        "barres": [
            {
                "finger": int(finger),
                "fret": int(fret),
                "span_start_string": int(span_start),
                "span_end_string": int(span_end),
            }
            for finger, fret, span_start, span_end in assignment.barres
        ],
    }


def _flatten_event_assignments(pitches_midi: tuple[int, ...], tuning: tuple[int, ...]):
    generated = generate_standard_fingerings(pitches_midi, tuning)
    flattened: list[tuple[str, tuple, StandardFingering]] = []
    seen_ids: set[str] = set()
    for candidate in generated.candidates:
        for assignment in candidate.assignments:
            if assignment.assignment_id in seen_ids:
                raise AssertionError("S2-A requires unique H-C assignment IDs within an event")
            seen_ids.add(assignment.assignment_id)
            flattened.append((candidate.candidate_id, candidate.candidate, assignment))
    flattened.sort(key=lambda item: item[2].assignment_id)
    return generated, tuple(flattened)


def _pair_id(event_id: str, left_id: str, right_id: str) -> str:
    low, high = sorted((left_id, right_id))
    return _opaque_hash("s2a-pair-sha256:", f"{S2A_PROTOCOL_VERSION}|{event_id}|{low}|{high}")


def _distance_strata_for_type(rows: list[dict]) -> None:
    rows.sort(key=lambda row: (row["distance_l1"], row["pair_id"]))
    count = len(rows)
    for index, row in enumerate(rows):
        bucket = min(2, (3 * index) // count)
        row["distance_stratum"] = _DISTANCE_STRATA[bucket]


def build_s2a_teacher_package(
    *,
    family_id: str,
    event_id: str,
    pitches_midi: tuple[int, ...],
    tuning: tuple[int, ...],
    provenance: str,
) -> tuple[dict, dict]:
    """Build a blind, label-free S2-A pair package from exact S1-H-C assignments."""

    if provenance not in (S2A_FIRST_PASS_PROVENANCE, S2A_FINAL_PROVENANCE):
        raise ValueError("S2-A first/final pair package requires exact allowed provenance")
    if not family_id or not event_id:
        raise ValueError("S2-A family_id and event_id are required for internal audit")

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    _, flattened = _flatten_event_assignments(pitches, tuning)
    if len(flattened) < 2:
        raise ValueError("S2-A event needs at least two distinct H-C assignments")

    by_assignment_id = {assignment.assignment_id: assignment for _, _, assignment in flattened}
    candidate_by_assignment_id = {
        assignment.assignment_id: (candidate_id, candidate)
        for candidate_id, candidate, assignment in flattened
    }
    features = {
        assignment.assignment_id: assignment_feature_vector(assignment)
        for _, _, assignment in flattened
    }

    all_pairs: list[dict] = []
    for left, right in combinations(flattened, 2):
        left_candidate_id, left_candidate, left_assignment = left
        right_candidate_id, right_candidate, right_assignment = right
        pair_type = "FINGER_ONLY" if left_candidate == right_candidate else "MIXED"
        left_features = features[left_assignment.assignment_id]
        right_features = features[right_assignment.assignment_id]
        distance = sum(abs(a - b) for a, b in zip(left_features, right_features))
        if not isfinite(distance):
            raise ValueError("S2-A pair feature distance must be finite")
        all_pairs.append({
            "pair_id": _pair_id(event_id, left_assignment.assignment_id, right_assignment.assignment_id),
            "pair_type": pair_type,
            "distance_l1": float(distance),
            "left_assignment_id": left_assignment.assignment_id,
            "right_assignment_id": right_assignment.assignment_id,
            "left_candidate_id": left_candidate_id,
            "right_candidate_id": right_candidate_id,
        })

    for pair_type in _PAIR_TYPES:
        typed = [row for row in all_pairs if row["pair_type"] == pair_type]
        if typed:
            _distance_strata_for_type(typed)

    selected: list[dict] = []
    for pair_type in _PAIR_TYPES:
        for stratum in _DISTANCE_STRATA:
            cell = [
                row for row in all_pairs
                if row["pair_type"] == pair_type and row.get("distance_stratum") == stratum
            ]
            if not cell:
                continue
            chosen = min(
                cell,
                key=lambda row: sha256(
                    f"{S2A_PROTOCOL_VERSION}|sample|{row['pair_id']}".encode("utf-8")
                ).hexdigest(),
            )
            selected.append(chosen)

    selected.sort(key=lambda row: (row["pair_type"], row["distance_stratum"], row["pair_id"]))
    if not 1 <= len(selected) <= 6:
        raise AssertionError("S2-A event must yield between one and six selected pairs")

    teacher_tasks: list[dict] = []
    audit_rows: list[dict] = []
    for row in selected:
        left_id = row["left_assignment_id"]
        right_id = row["right_assignment_id"]
        order_digest = sha256(
            f"{S2A_PROTOCOL_VERSION}|ab|{row['pair_id']}".encode("utf-8")
        ).digest()
        if order_digest[0] & 1:
            a_id, b_id = right_id, left_id
        else:
            a_id, b_id = left_id, right_id
        task_id = _opaque_hash("s2a-task-sha256:", f"{S2A_PROTOCOL_VERSION}|{row['pair_id']}")
        a_assignment = by_assignment_id[a_id]
        b_assignment = by_assignment_id[b_id]
        teacher_tasks.append({
            "task_id": task_id,
            "pitches_midi": list(pitches),
            "tuning": list(tuning),
            "options": [
                _assignment_payload(a_assignment, "A"),
                _assignment_payload(b_assignment, "B"),
            ],
            "allowed_responses": list(S2A_RESPONSES),
        })
        a_candidate_id, _ = candidate_by_assignment_id[a_id]
        b_candidate_id, _ = candidate_by_assignment_id[b_id]
        audit_rows.append({
            "task_id": task_id,
            "pair_id": row["pair_id"],
            "family_id": family_id,
            "event_id": event_id,
            "pitches_midi": list(pitches),
            "tuning": list(tuning),
            "pair_type": row["pair_type"],
            "distance_stratum": row["distance_stratum"],
            "distance_l1": row["distance_l1"],
            "A_assignment_id": a_id,
            "B_assignment_id": b_id,
            "A_candidate_id": a_candidate_id,
            "B_candidate_id": b_candidate_id,
            "A_features": list(features[a_id]),
            "B_features": list(features[b_id]),
        })

    teacher_manifest = {
        "schema": S2A_TEACHER_MANIFEST_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": provenance,
        "target": "STATIC_STANDARD_FINGERING_NATURALNESS",
        "annotation_blinded": True,
        "source_identity": "withheld",
        "family_identity": "withheld",
        "model_identity": "withheld",
        "model_scores": "withheld",
        "feature_values": "withheld",
        "observed_source_fingering": "withheld",
        "pair_selection_stratum": "withheld",
        "prior_responses": "withheld",
        "task_count": len(teacher_tasks),
        "tasks": teacher_tasks,
    }
    internal_audit = {
        "schema": S2A_INTERNAL_AUDIT_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": provenance,
        "teacher_facing": False,
        "label_used_for_pair_sampling": False,
        "observed_source_fingering_used": False,
        "task_count": len(audit_rows),
        "rows": audit_rows,
    }
    return teacher_manifest, internal_audit


def _parse_utc(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("S2-A collection timestamp must be offset-aware UTC")
    return parsed.astimezone(timezone.utc)


def validate_s2a_choice_export(payload: dict, teacher_manifest: dict) -> dict[str, str]:
    if payload.get("schema") != S2A_CHOICE_EXPORT_SCHEMA:
        raise ValueError("unexpected S2-A choice export schema")
    if payload.get("annotation_blinded") is not True:
        raise ValueError("S2-A choice export must remain blind")
    if payload.get("provenance") != teacher_manifest.get("provenance"):
        raise ValueError("S2-A choice provenance mismatch")
    if teacher_manifest.get("schema") != S2A_TEACHER_MANIFEST_SCHEMA:
        raise ValueError("unexpected S2-A teacher manifest schema")
    if not str(payload.get("annotator_id", "")).strip():
        raise ValueError("S2-A annotator_id is required")
    _parse_utc(str(payload.get("collected_at_utc", "")))

    known_ids = {row["task_id"] for row in teacher_manifest.get("tasks", [])}
    choices = payload.get("choices")
    if not isinstance(choices, list):
        raise ValueError("S2-A choices must be a list")
    out: dict[str, str] = {}
    for row in choices:
        task_id = str(row.get("task_id", ""))
        response = str(row.get("response", ""))
        if task_id not in known_ids:
            raise ValueError("S2-A choice export contains unknown task_id")
        if task_id in out:
            raise ValueError("S2-A choice export contains duplicate task_id")
        if response not in S2A_RESPONSES:
            raise ValueError("S2-A response must be A, B, or EQUAL_OR_UNSURE")
        out[task_id] = response
    if set(out) != known_ids:
        raise ValueError("S2-A choice export must cover the complete sealed manifest")
    return out


def build_s2a_repeat_package(
    first_manifest: dict,
    first_audit: dict,
    *,
    repeat_count: int,
) -> tuple[dict, dict]:
    if first_manifest.get("schema") != S2A_TEACHER_MANIFEST_SCHEMA:
        raise ValueError("unexpected S2-A first-pass manifest schema")
    if first_manifest.get("provenance") != S2A_FIRST_PASS_PROVENANCE:
        raise ValueError("S2-A repeats may only be built from FIRST_PASS tasks")
    if first_audit.get("schema") != S2A_INTERNAL_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A first-pass audit schema")
    tasks = {row["task_id"]: row for row in first_manifest.get("tasks", [])}
    audit = {row["task_id"]: row for row in first_audit.get("rows", [])}
    if set(tasks) != set(audit) or not tasks:
        raise ValueError("S2-A first-pass manifest/audit task mismatch")
    if repeat_count <= 0 or repeat_count > len(tasks) or repeat_count % 2:
        raise ValueError("S2-A repeat_count must be positive, even, and within the first-pass task count")

    selected_ids = sorted(
        tasks,
        key=lambda task_id: sha256(
            f"{S2A_PROTOCOL_VERSION}|repeat-select|{task_id}".encode("utf-8")
        ).hexdigest(),
    )[:repeat_count]
    reversed_ids = set(sorted(
        selected_ids,
        key=lambda task_id: sha256(
            f"{S2A_PROTOCOL_VERSION}|repeat-reverse|{task_id}".encode("utf-8")
        ).hexdigest(),
    )[: repeat_count // 2])

    repeat_tasks: list[dict] = []
    repeat_audit_rows: list[dict] = []
    for first_task_id in selected_ids:
        first_task = tasks[first_task_id]
        first_row = audit[first_task_id]
        options = {option["option_id"]: option for option in first_task["options"]}
        reverse = first_task_id in reversed_ids
        source_a = options["B"] if reverse else options["A"]
        source_b = options["A"] if reverse else options["B"]
        repeat_task_id = _opaque_hash(
            "s2a-repeat-task-sha256:",
            f"{S2A_PROTOCOL_VERSION}|repeat|{first_task_id}",
        )

        def relabel(option: dict, label: str) -> dict:
            copied = dict(option)
            copied["option_id"] = label
            return copied

        repeat_tasks.append({
            "task_id": repeat_task_id,
            "pitches_midi": list(first_task["pitches_midi"]),
            "tuning": list(first_task["tuning"]),
            "options": [relabel(source_a, "A"), relabel(source_b, "B")],
            "allowed_responses": list(S2A_RESPONSES),
        })
        repeat_audit_rows.append({
            "repeat_task_id": repeat_task_id,
            "first_task_id": first_task_id,
            "family_id": first_row["family_id"],
            "event_id": first_row["event_id"],
            "pair_id": first_row["pair_id"],
            "presentation_reversed": reverse,
            "canonical_assignment_ids": sorted((
                first_row["A_assignment_id"],
                first_row["B_assignment_id"],
            )),
            "first_A_assignment_id": first_row["A_assignment_id"],
            "first_B_assignment_id": first_row["B_assignment_id"],
            "repeat_A_assignment_id": source_a["assignment_id"],
            "repeat_B_assignment_id": source_b["assignment_id"],
        })

    repeat_manifest = {
        "schema": S2A_TEACHER_MANIFEST_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "provenance": S2A_REPEAT_PROVENANCE,
        "target": "STATIC_STANDARD_FINGERING_NATURALNESS",
        "annotation_blinded": True,
        "source_identity": "withheld",
        "family_identity": "withheld",
        "model_identity": "withheld",
        "model_scores": "withheld",
        "feature_values": "withheld",
        "observed_source_fingering": "withheld",
        "pair_selection_stratum": "withheld",
        "prior_responses": "withheld",
        "task_count": len(repeat_tasks),
        "tasks": repeat_tasks,
    }
    repeat_audit = {
        "schema": S2A_REPEAT_AUDIT_SCHEMA,
        "protocol_version": S2A_PROTOCOL_VERSION,
        "teacher_facing": False,
        "old_answers_included": False,
        "repeat_count": repeat_count,
        "reversed_count": len(reversed_ids),
        "rows": repeat_audit_rows,
    }
    return repeat_manifest, repeat_audit


def _semantic_choice(response: str, a_id: str, b_id: str, canonical: list[str]):
    if response == "EQUAL_OR_UNSURE":
        return "EQUAL_OR_UNSURE"
    chosen = a_id if response == "A" else b_id
    if chosen == canonical[0]:
        return 0
    if chosen == canonical[1]:
        return 1
    raise AssertionError("S2-A response references assignment outside canonical repeat pair")


def _binary_cohen_kappa(left: list[int], right: list[int]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / n
    p_left_0 = left.count(0) / n
    p_left_1 = left.count(1) / n
    p_right_0 = right.count(0) / n
    p_right_1 = right.count(1) / n
    expected = p_left_0 * p_right_0 + p_left_1 * p_right_1
    if expected >= 1.0:
        return 0.0
    return (observed - expected) / (1.0 - expected)


def evaluate_s2a_repeat_reliability(
    first_manifest: dict,
    first_payload: dict,
    repeat_manifest: dict,
    repeat_audit: dict,
    repeat_payload: dict,
) -> dict:
    first_choices = validate_s2a_choice_export(first_payload, first_manifest)
    repeat_choices = validate_s2a_choice_export(repeat_payload, repeat_manifest)
    if repeat_audit.get("schema") != S2A_REPEAT_AUDIT_SCHEMA:
        raise ValueError("unexpected S2-A repeat audit schema")
    if repeat_audit.get("old_answers_included") is not False:
        raise ValueError("S2-A repeat audit may not contain old answers")

    first_tasks = {row["task_id"]: row for row in first_manifest["tasks"]}
    rows = repeat_audit.get("rows", [])
    repeat_task_ids = {row["repeat_task_id"] for row in rows}
    if repeat_task_ids != set(repeat_choices):
        raise ValueError("S2-A repeat response/audit task mismatch")

    semantic_first = []
    semantic_repeat = []
    decisive_first: list[int] = []
    decisive_repeat: list[int] = []
    for row in rows:
        first_task_id = row["first_task_id"]
        repeat_task_id = row["repeat_task_id"]
        if first_task_id not in first_choices or first_task_id not in first_tasks:
            raise ValueError("S2-A repeat audit references unknown first-pass task")
        canonical = list(row["canonical_assignment_ids"])
        if len(canonical) != 2 or canonical != sorted(set(canonical)):
            raise ValueError("S2-A repeat canonical pair must contain two unique IDs")

        first_value = _semantic_choice(
            first_choices[first_task_id],
            row["first_A_assignment_id"],
            row["first_B_assignment_id"],
            canonical,
        )
        repeat_value = _semantic_choice(
            repeat_choices[repeat_task_id],
            row["repeat_A_assignment_id"],
            row["repeat_B_assignment_id"],
            canonical,
        )
        semantic_first.append(first_value)
        semantic_repeat.append(repeat_value)
        if isinstance(first_value, int) and isinstance(repeat_value, int):
            decisive_first.append(first_value)
            decisive_repeat.append(repeat_value)

    if not semantic_first:
        raise ValueError("S2-A repeat reliability requires repeated tasks")
    exact_agreement = sum(a == b for a, b in zip(semantic_first, semantic_repeat)) / len(semantic_first)
    kappa = _binary_cohen_kappa(decisive_first, decisive_repeat)

    first_time = _parse_utc(str(first_payload.get("collected_at_utc", "")))
    repeat_time = _parse_utc(str(repeat_payload.get("collected_at_utc", "")))
    interval_hours = (repeat_time - first_time).total_seconds() / 3600.0
    interval_pass = 24.0 <= interval_hours <= 72.0
    reversed_count = sum(bool(row.get("presentation_reversed")) for row in rows)
    reversal_pass = reversed_count * 2 == len(rows)

    passed = (
        exact_agreement >= 0.85
        and kappa >= 0.75
        and interval_pass
        and reversal_pass
        and repeat_audit.get("old_answers_included") is False
    )
    return {
        "protocol_version": S2A_PROTOCOL_VERSION,
        "repeat_tasks": len(rows),
        "three_class_exact_agreement": exact_agreement,
        "decisive_overlap_tasks": len(decisive_first),
        "decisive_cohen_kappa": kappa,
        "repeat_interval_hours": interval_hours,
        "repeat_interval_24_to_72h": interval_pass,
        "presentation_reversed_count": reversed_count,
        "presentation_reversal_exactly_50_percent": reversal_pass,
        "old_answers_included": False,
        "status": "PASS" if passed else "FAIL",
    }
