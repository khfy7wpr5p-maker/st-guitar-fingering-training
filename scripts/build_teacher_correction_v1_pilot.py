from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from build_s2a_teacher_batch02 import (
    _load_and_verify_freeze,
    _load_sources,
    _reproduce_frozen_reservation,
)
from st_guitar_fingering_training.teacher_correction import (
    TCV1_MANIFEST_SCHEMA,
    build_teacher_correction_manifest,
    build_teacher_correction_task,
    filter_quarantined_tasks,
    render_teacher_correction_html,
)


PILOT_BATCH_ID = "TCV1_PILOT01"
PILOT_SESSION_ID = "TCV1_PILOT01"
PILOT_TASK_COUNT = 20
PILOT_MAX_SOLUTIONS_PER_TASK = 24
MAX_ELIGIBLE_EVENTS_SCANNED_PER_SOURCE = 24
PRIMARY_ROLE = "PRIMARY_DEVELOPMENT"


def _event_id(source, event) -> str:
    payload = "|".join(
        (
            "TEACHER_CORRECTION.v1",
            source.family_id,
            source.source_sha256,
            str(event.measure),
            str(event.onset),
            str(event.voice),
            ",".join(str(value) for value in event.pitches_midi),
        )
    )
    return "tcv1-event-sha256:" + sha256(payload.encode("utf-8")).hexdigest()


def _load_quarantine(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_primary_representatives(audit: dict, freeze_sha: str) -> tuple[dict, ...]:
    primary = [
        row for row in audit["final_reservation"]["sources"]
        if row.get("role") == PRIMARY_ROLE
    ]
    if len(primary) != 80:
        raise RuntimeError("STOP: frozen PRIMARY_DEVELOPMENT source count is not 80")
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in primary:
        by_family[str(row["family_id"])].append(row)
    if len(by_family) != 51:
        raise RuntimeError("STOP: frozen PRIMARY_DEVELOPMENT family count is not 51")
    representatives = []
    for family_id in sorted(by_family):
        rows = sorted(
            by_family[family_id],
            key=lambda row: sha256(
                f"{freeze_sha}|TCV1_PILOT01|source|{row['path']}|{row['raw_sha256']}".encode("utf-8")
            ).hexdigest(),
        )
        representatives.append(rows[0])
    return tuple(representatives)


def _candidate_tasks_for_source(source, quarantine: dict) -> tuple[tuple[dict, dict], ...]:
    candidates = []
    eligible_seen = 0
    for event in source.events:
        if not event.is_chord or len(event.pitches_midi) > 6:
            continue
        event_id = _event_id(source, event)
        try:
            task = build_teacher_correction_task(
                event_id=event_id,
                pitches_midi=event.pitches_midi,
                tuning=event.tuning,
            )
        except ValueError as exc:
            if "at least two H-C assignments" in str(exc):
                continue
            raise
        eligible_seen += 1
        clean = filter_quarantined_tasks((task,), quarantine)
        if clean and int(task["solution_count"]) <= PILOT_MAX_SOLUTIONS_PER_TASK:
            audit = {
                "family_id": source.family_id,
                "source_sha256": source.source_sha256,
                "event_id": event_id,
                "measure": int(event.measure),
                "onset": str(event.onset),
                "voice": str(event.voice),
                "pitches_midi": list(event.pitches_midi),
                "task_id": task["task_id"],
                "task_fingerprint": task["task_fingerprint"],
                "solution_count": task["solution_count"],
                "initial_assignment_id": task["initial_assignment_id"],
            }
            candidates.append((task, audit))
        if eligible_seen >= MAX_ELIGIBLE_EVENTS_SCANNED_PER_SOURCE:
            break
    candidates.sort(
        key=lambda pair: (
            int(pair[0]["solution_count"]),
            sha256(f"{PILOT_BATCH_ID}|event|{pair[0]['task_id']}".encode("utf-8")).hexdigest(),
        )
    )
    return tuple(candidates)


def build(args) -> dict:
    freeze, freeze_sha = _load_and_verify_freeze(args.freeze_manifest)
    reproduced = _reproduce_frozen_reservation(args, freeze)
    representatives = _all_primary_representatives(reproduced, freeze_sha)
    sources = _load_sources(representatives)
    quarantine = _load_quarantine(args.teacher_quarantine_manifest)

    family_candidates = []
    for source in sources:
        candidates = _candidate_tasks_for_source(source, quarantine)
        if candidates:
            task, audit = candidates[0]
            family_candidates.append((task, audit))

    if len(family_candidates) < PILOT_TASK_COUNT:
        raise RuntimeError(
            f"STOP: only {len(family_candidates)} primary families have a non-quarantined "
            f"Teacher Correction event with <= {PILOT_MAX_SOLUTIONS_PER_TASK} solutions"
        )

    family_candidates.sort(
        key=lambda pair: (
            int(pair[0]["solution_count"]),
            sha256(
                f"{freeze_sha}|{PILOT_BATCH_ID}|family|{pair[1]['family_id']}|{pair[0]['task_id']}".encode("utf-8")
            ).hexdigest(),
        )
    )
    selected = family_candidates[:PILOT_TASK_COUNT]
    tasks = [pair[0] for pair in selected]
    audits = [pair[1] for pair in selected]

    if len({row["task_id"] for row in tasks}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction duplicate task ID")
    if len({row["task_fingerprint"] for row in tasks}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction duplicate task fingerprint")
    if len({row["family_id"] for row in audits}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction pilot lost family isolation")
    if max(int(row["solution_count"]) for row in tasks) > PILOT_MAX_SOLUTIONS_PER_TASK:
        raise RuntimeError("STOP: Teacher Correction pilot exceeded solution-count UX cap")

    manifest = build_teacher_correction_manifest(
        batch_id=PILOT_BATCH_ID,
        session_id=PILOT_SESSION_ID,
        tasks=tasks,
        quarantine=quarantine,
    )
    if manifest["schema"] != TCV1_MANIFEST_SCHEMA or manifest["task_count"] != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction manifest invariant failed")

    teacher_dir = args.output_dir / "teacher"
    internal_dir = args.output_dir / "internal"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)
    (teacher_dir / "ST_Guitar_TeacherCorrectionV1_Pilot01.html").write_text(
        render_teacher_correction_html(manifest), encoding="utf-8"
    )
    (teacher_dir / "ST_Guitar_TeacherCorrectionV1_Pilot01_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    internal = {
        "schema": "st-guitar-teacher-correction-v1-pilot-audit",
        "protocol_version": "TEACHER_CORRECTION.v1",
        "status": "READY_FOR_TEACHER_CORRECTION",
        "batch_id": PILOT_BATCH_ID,
        "session_id": PILOT_SESSION_ID,
        "source_freeze_manifest_sha256": freeze_sha,
        "reproduced_reservation_identity_sha256": reproduced["final_reservation"]["identity_sha256"],
        "source_role": PRIMARY_ROLE,
        "primary_family_pool_count": len(representatives),
        "manageable_family_pool_count": len(family_candidates),
        "pilot_selection_policy": (
            "label-free UX pilot: one deterministic representative per frozen primary family; "
            "scan up to 24 H-C-eligible events; require <=24 exact H-C solutions; choose the "
            "lowest-complexity clean event per family, then the 20 lowest-complexity families "
            "with deterministic hash tie-breaks"
        ),
        "max_solutions_per_task": PILOT_MAX_SOLUTIONS_PER_TASK,
        "contingency_sources_used": 0,
        "untouched_final_sources_used": 0,
        "historical_teacher_responses_used": False,
        "model_scores_used": False,
        "quarantine_manifest_sha256": manifest["quarantine_manifest_sha256"],
        "task_count": len(tasks),
        "family_count": len({row["family_id"] for row in audits}),
        "solution_count_min": min(row["solution_count"] for row in audits),
        "solution_count_max": max(row["solution_count"] for row in audits),
        "solution_count_mean": sum(row["solution_count"] for row in audits) / len(audits),
        "rows": audits,
        "training_authorized": False,
        "checkpoint_retention_authorized": False,
        "untouched_final_opened": False,
        "shadow_or_production_authorized": False,
    }
    (internal_dir / "ST_Guitar_TeacherCorrectionV1_Pilot01_audit.json").write_text(
        json.dumps(internal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "status": internal["status"],
        "batch_id": PILOT_BATCH_ID,
        "session_id": PILOT_SESSION_ID,
        "task_count": PILOT_TASK_COUNT,
        "family_count": internal["family_count"],
        "primary_family_pool_count": internal["primary_family_pool_count"],
        "manageable_family_pool_count": internal["manageable_family_pool_count"],
        "max_solutions_per_task": PILOT_MAX_SOLUTIONS_PER_TASK,
        "manifest_sha256": manifest["manifest_sha256"],
        "quarantine_manifest_sha256": manifest["quarantine_manifest_sha256"],
        "solution_count_min": internal["solution_count_min"],
        "solution_count_max": internal["solution_count_max"],
        "solution_count_mean": internal["solution_count_mean"],
        "reproduced_reservation_identity_sha256": internal["reproduced_reservation_identity_sha256"],
        "contingency_sources_used": 0,
        "untouched_final_sources_used": 0,
        "historical_teacher_responses_used": False,
        "model_scores_used": False,
        "training_authorized": False,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 20-task Teacher Correction v1 UX pilot")
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--teacher-quarantine-manifest", type=Path, required=True)
    parser.add_argument("--old-teacher-manifest", type=Path, required=True)
    parser.add_argument("--origin-alias-manifest", type=Path, required=True)
    parser.add_argument("--quarantine-manifest", type=Path, action="append", default=[])
    parser.add_argument("--prior-final-semantic-quarantine", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
