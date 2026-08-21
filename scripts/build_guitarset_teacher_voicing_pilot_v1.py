from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from st_guitar_fingering_training.guitarset_observed_gold import (
    _validated_comp_members,
    archive_sha256,
    derive_strum_voicings,
    extract_comp_jams,
)
from st_guitar_fingering_training.guitarset_split import parse_comp_member_identity
from st_guitar_fingering_training.guitarset_teacher_voicing import (
    TEACHER_VOICING_AUDIT_SCHEMA,
    TEACHER_VOICING_PILOT_VERSION,
    build_teacher_voicing_manifest,
    development_members_from_archive_metadata,
    exact_candidates,
    render_teacher_voicing_html,
)
from st_guitar_fingering_training.guitarset_teacher_voicing_blind import (
    build_complete_blinded_teacher_voicing_task,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import GUITARSET_SOURCE_ARCHIVE_SHA256


DEFAULT_TASK_COUNT = 24
DEFAULT_OPTION_CAP = 6
BATCH_ID = "GUITARSET_TVPV1_PILOT01"
SESSION_ID = "GuitarSet_TeacherVoicing_Pilot01"


def _row_rank(task_id: str) -> str:
    return sha256(f"{TEACHER_VOICING_PILOT_VERSION}|PILOT01|{task_id}".encode("utf-8")).hexdigest()


def _select_balanced(rows: list[tuple[dict, dict]], task_count: int) -> tuple[tuple[dict, dict], ...]:
    if task_count < 4:
        raise ValueError("teacher voicing pilot requires at least four tasks")
    by_performer: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for task, audit in rows:
        by_performer[str(audit["performer"])].append((task, audit))
    performers = tuple(sorted(by_performer))
    if len(performers) != 4:
        raise RuntimeError(f"STOP: expected four DEVELOPMENT performers, got {performers}")

    for performer in performers:
        by_performer[performer].sort(
            key=lambda pair: (
                int(pair[0]["full_candidate_count"]),
                _row_rank(str(pair[0]["task_id"])),
            )
        )

    base = task_count // len(performers)
    remainder = task_count % len(performers)
    quotas = {performer: base + (1 if index < remainder else 0) for index, performer in enumerate(performers)}

    selected: list[tuple[dict, dict]] = []
    used_semantics: set[str] = set()
    used_task_ids: set[str] = set()
    for performer in performers:
        for task, audit in by_performer[performer]:
            semantic = str(task["semantic_fingerprint"])
            task_id = str(task["task_id"])
            if semantic in used_semantics or task_id in used_task_ids:
                continue
            selected.append((task, audit))
            used_semantics.add(semantic)
            used_task_ids.add(task_id)
            if sum(1 for _, row in selected if row["performer"] == performer) == quotas[performer]:
                break

    if len(selected) < task_count:
        fallback = sorted(
            rows,
            key=lambda pair: (
                int(pair[0]["full_candidate_count"]),
                _row_rank(str(pair[0]["task_id"])),
            ),
        )
        for task, audit in fallback:
            semantic = str(task["semantic_fingerprint"])
            task_id = str(task["task_id"])
            if semantic in used_semantics or task_id in used_task_ids:
                continue
            selected.append((task, audit))
            used_semantics.add(semantic)
            used_task_ids.add(task_id)
            if len(selected) == task_count:
                break

    if len(selected) != task_count:
        raise RuntimeError(
            f"STOP: only {len(selected)} distinct DEVELOPMENT semantic tasks available for requested {task_count}"
        )

    selected.sort(key=lambda pair: _row_rank(str(pair[0]["task_id"])))
    return tuple(selected)


def build(archive_path: Path, output_dir: Path, *, task_count: int, option_cap: int) -> dict:
    source_sha = archive_sha256(archive_path)
    if source_sha != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise RuntimeError(
            f"STOP: GuitarSet archive SHA mismatch; expected {GUITARSET_SOURCE_ARCHIVE_SHA256}, got {source_sha}"
        )

    accepted = []
    quarantined = []
    with zipfile.ZipFile(archive_path) as archive:
        all_members = _validated_comp_members(archive_path, archive)
        development_members = development_members_from_archive_metadata(
            all_members,
            source_archive_sha256=source_sha,
        )
        for member in development_members:
            performer, _, _ = parse_comp_member_identity(member)
            if performer not in {"00", "01", "04", "05"}:
                raise AssertionError("DEVELOPMENT member isolation failure")
            notes, rejects = extract_comp_jams(member, archive.read(member))
            accepted.extend(notes)
            quarantined.extend(rejects)

    voicings = derive_strum_voicings(accepted)
    candidates: list[tuple[dict, dict]] = []
    for voicing in voicings:
        pitches = tuple(sorted(pitch for pitch, _, _ in voicing.placements))
        physical = exact_candidates(pitches)
        if len(physical) < 2 or len(physical) > option_cap:
            continue
        task, audit = build_complete_blinded_teacher_voicing_task(
            event_id=voicing.voicing_id,
            pitches_midi=pitches,
            observed_placements=voicing.placements,
            option_cap=option_cap,
        )
        performer, track_key, style_key = parse_comp_member_identity(voicing.source_member)
        audit.update(
            {
                "source_member": voicing.source_member,
                "recording_id": voicing.recording_id,
                "performer": performer,
                "track_key": track_key,
                "style_key": style_key,
                "voicing_id": voicing.voicing_id,
                "anchor_onset_seconds": voicing.anchor_onset_seconds,
                "onset_spread_seconds": voicing.onset_spread_seconds,
                "candidate_selection_used_model_scores": False,
                "candidate_selection_used_baseline_scores": False,
                "candidate_selection_used_teacher_labels": False,
            }
        )
        candidates.append((task, audit))

    selected = _select_balanced(candidates, task_count)
    tasks = [task for task, _ in selected]
    audits = [audit for _, audit in selected]
    manifest = build_teacher_voicing_manifest(
        batch_id=BATCH_ID,
        session_id=SESSION_ID,
        tasks=tasks,
    )

    teacher_dir = output_dir / "teacher"
    internal_dir = output_dir / "internal"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

    html_path = teacher_dir / "ST_Guitar_GuitarSet_TeacherVoicing_Pilot01.html"
    manifest_path = teacher_dir / "ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_manifest.json"
    audit_path = internal_dir / "ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_audit.json"

    html_path.write_text(render_teacher_voicing_html(manifest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    performer_counts = defaultdict(int)
    for row in audits:
        performer_counts[str(row["performer"])] += 1

    audit = {
        "schema": TEACHER_VOICING_AUDIT_SCHEMA,
        "protocol_version": TEACHER_VOICING_PILOT_VERSION,
        "status": "READY_FOR_DIAGNOSTIC_TEACHER_VOICING_PILOT",
        "batch_id": BATCH_ID,
        "session_id": SESSION_ID,
        "source_archive_sha256": source_sha,
        "source_role": "DEVELOPMENT_ONLY",
        "development_recording_count": 120,
        "development_accepted_note_count": len(accepted),
        "development_quarantined_note_count": len(quarantined),
        "development_derived_voicing_count": len(voicings),
        "eligible_ambiguous_development_voicing_count": len(candidates),
        "task_count": len(tasks),
        "option_cap": option_cap,
        "selected_performer_counts": dict(sorted(performer_counts.items())),
        "selection_policy": (
            "DEVELOPMENT-only, label-blind diagnostic pilot; require 2..option_cap exact physical voicings; "
            "show the complete physical candidate set for every task; deduplicate semantic pitch/candidate sets; "
            "balance across four DEVELOPMENT performers; prefer lower candidate-count tasks then deterministic hash; "
            "blind option order; never identify the observed GuitarSet placement to the annotator"
        ),
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "rows": audits,
        "diagnostic_only_never_training": True,
        "teacher_labels_may_not_modify_preregistered_model": True,
        "validation_performer_opened": False,
        "untouched_final_performer_opened": False,
        "training_authorized": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "status": audit["status"],
        "task_count": audit["task_count"],
        "selected_performer_counts": audit["selected_performer_counts"],
        "eligible_ambiguous_development_voicing_count": audit["eligible_ambiguous_development_voicing_count"],
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "html": str(html_path),
        "manifest": str(manifest_path),
        "internal_audit": str(audit_path),
        "validation_performer_opened": False,
        "untouched_final_performer_opened": False,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a blinded DEVELOPMENT-only GuitarSet Teacher Voicing diagnostic pilot"
    )
    parser.add_argument("archive", type=Path, help="Exact approved GuitarSet archive")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--task-count", type=int, default=DEFAULT_TASK_COUNT)
    parser.add_argument("--option-cap", type=int, default=DEFAULT_OPTION_CAP)
    args = parser.parse_args()
    summary = build(
        args.archive,
        args.output_dir,
        task_count=args.task_count,
        option_cap=args.option_cap,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
