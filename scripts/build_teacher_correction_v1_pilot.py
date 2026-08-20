from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from build_s2a_teacher_batch02 import (
    _load_and_verify_freeze,
    _load_sources,
    _reproduce_frozen_reservation,
    _select_primary_representatives,
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
PILOT_TASK_COUNT = 40
MAX_ELIGIBLE_EVENTS_SCANNED_PER_SOURCE = 8


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
        if clean:
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
    if not candidates:
        raise RuntimeError(f"STOP: no non-quarantined Teacher Correction event for {source.family_id}")
    candidates.sort(
        key=lambda pair: (
            int(pair[0]["solution_count"]),
            sha256(f"{PILOT_BATCH_ID}|{pair[0]['task_id']}".encode("utf-8")).hexdigest(),
        )
    )
    return tuple(candidates)


def build(args) -> dict:
    freeze, freeze_sha = _load_and_verify_freeze(args.freeze_manifest)
    reproduced = _reproduce_frozen_reservation(args, freeze)
    representatives = _select_primary_representatives(reproduced, freeze_sha)
    if len(representatives) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction pilot requires exactly 40 primary families")
    sources = _load_sources(representatives)
    quarantine = _load_quarantine(args.teacher_quarantine_manifest)

    tasks = []
    audits = []
    for source in sources:
        candidates = _candidate_tasks_for_source(source, quarantine)
        task, audit = candidates[0]
        tasks.append(task)
        audits.append(audit)

    if len(tasks) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction pilot task count drift")
    if len({row["task_id"] for row in tasks}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction duplicate task ID")
    if len({row["task_fingerprint"] for row in tasks}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction duplicate task fingerprint")
    if len({row["family_id"] for row in audits}) != PILOT_TASK_COUNT:
        raise RuntimeError("STOP: Teacher Correction pilot lost family isolation")

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
        "source_role": "PRIMARY_DEVELOPMENT",
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
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 40-task Teacher Correction v1 pilot")
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
