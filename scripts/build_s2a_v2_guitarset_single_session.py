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
from st_guitar_fingering_training.guitarset_voicing_prereg import GUITARSET_SOURCE_ARCHIVE_SHA256
from st_guitar_fingering_training.s2a_v2_fixed_voicing import (
    BUCKET_DEVELOPMENT,
    BUCKET_FINAL,
    S2A_V2_AUDIT_SCHEMA,
    S2A_V2_PROTOCOL_VERSION,
    build_fixed_voicing_task,
    build_single_session_manifest,
    canonical_sha256,
    render_single_session_html,
)


DEFAULT_DEVELOPMENT_TASKS = 200
DEFAULT_REPEAT_TASKS = 30
DEFAULT_FINAL_TASKS = 60
DEFAULT_MAX_ASSIGNMENTS = 8
BATCH_ID = "S2A_V2_GUITARSET_SINGLE_SESSION_01"
SESSION_ID = "ST_Guitar_S2A_V2_Tek_Oturum"


def _track_rank(track_key: str, source_sha: str) -> str:
    return sha256(
        f"{S2A_V2_PROTOCOL_VERSION}|TRACK_SPLIT|{source_sha}|{track_key}".encode("utf-8")
    ).hexdigest()


def _task_rank(task_id: str, salt: str) -> str:
    return sha256(f"{S2A_V2_PROTOCOL_VERSION}|{salt}|{task_id}".encode("utf-8")).hexdigest()


def _track_split(members: tuple[str, ...], source_sha: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tracks = tuple(sorted({parse_comp_member_identity(member)[1] for member in members}))
    if len(tracks) != 30:
        raise RuntimeError(f"STOP: expected exactly 30 GuitarSet track families, got {len(tracks)}")
    ranked = tuple(sorted(tracks, key=lambda track: (_track_rank(track, source_sha), track)))
    final_tracks = tuple(sorted(ranked[:6]))
    development_tracks = tuple(sorted(ranked[6:]))
    if len(development_tracks) != 24 or len(final_tracks) != 6:
        raise AssertionError("S2-A.v2 track split cardinality drift")
    if set(development_tracks) & set(final_tracks):
        raise AssertionError("S2-A.v2 track split overlap")
    return development_tracks, final_tracks


def _candidate_rows(voicings, *, max_assignments: int) -> list[tuple[dict, dict]]:
    rows: list[tuple[dict, dict]] = []
    for voicing in voicings:
        performer, track_key, style_key = parse_comp_member_identity(voicing.source_member)
        fixed = tuple(voicing.placements)
        try:
            task = build_fixed_voicing_task(
                event_id=voicing.voicing_id,
                fixed_voicing=fixed,
                export_bucket=BUCKET_DEVELOPMENT,
                presentation_nonce="ORIGINAL",
            )
        except ValueError:
            continue
        if not 2 <= int(task["assignment_count"]) <= max_assignments:
            continue
        audit = {
            "event_id": voicing.voicing_id,
            "source_member": voicing.source_member,
            "recording_id": voicing.recording_id,
            "performer": performer,
            "track_key": track_key,
            "style_key": style_key,
            "family_id": f"guitarset-track:{track_key}",
            "semantic_fingerprint": task["semantic_fingerprint"],
            "assignment_count": task["assignment_count"],
            "fixed_voicing": task["fixed_voicing"],
            "anchor_onset_seconds": voicing.anchor_onset_seconds,
            "onset_spread_seconds": voicing.onset_spread_seconds,
        }
        rows.append((task, audit))
    return rows


def _select_balanced(
    candidates: list[tuple[dict, dict]],
    *,
    allowed_tracks: tuple[str, ...],
    count: int,
    bucket: str,
    used_semantics: set[str],
) -> tuple[tuple[dict, dict], ...]:
    by_track: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    allowed = set(allowed_tracks)
    for task, audit in candidates:
        track = str(audit["track_key"])
        semantic = str(task["semantic_fingerprint"])
        if track not in allowed or semantic in used_semantics:
            continue
        by_track[track].append((task, audit))
    if set(by_track) != allowed:
        missing = sorted(allowed - set(by_track))
        raise RuntimeError(f"STOP: S2-A.v2 track families without eligible tasks: {missing}")
    for track in by_track:
        by_track[track].sort(key=lambda pair: (
            int(pair[0]["assignment_count"]),
            _task_rank(str(pair[0]["task_id"]), f"CANDIDATE|{track}"),
        ))

    selected: list[tuple[dict, dict]] = []
    positions = {track: 0 for track in allowed_tracks}
    track_order = tuple(sorted(allowed_tracks, key=lambda track: (_track_rank(track, "selection"), track)))
    while len(selected) < count:
        progressed = False
        for track in track_order:
            rows = by_track[track]
            while positions[track] < len(rows):
                source_task, source_audit = rows[positions[track]]
                positions[track] += 1
                semantic = str(source_task["semantic_fingerprint"])
                if semantic in used_semantics:
                    continue
                task = build_fixed_voicing_task(
                    event_id=str(source_audit["event_id"]),
                    fixed_voicing=[
                        (row["pitch_midi"], row["string"], row["fret"])
                        for row in source_task["fixed_voicing"]
                    ],
                    export_bucket=bucket,
                    presentation_nonce=f"ORIGINAL|{bucket}",
                )
                audit = dict(source_audit)
                audit.update({
                    "task_id": task["task_id"],
                    "role": "DEVELOPMENT_ORIGINAL" if bucket == BUCKET_DEVELOPMENT else "UNTOUCHED_FINAL",
                    "export_bucket": bucket,
                })
                selected.append((task, audit))
                used_semantics.add(semantic)
                progressed = True
                break
            if len(selected) == count:
                break
        if not progressed:
            raise RuntimeError(
                f"STOP: only {len(selected)} unique balanced S2-A.v2 tasks available for requested {count}"
            )
    return tuple(selected)


def _build_repeats(
    development: tuple[tuple[dict, dict], ...],
    *,
    repeat_count: int,
) -> tuple[tuple[dict, dict], ...]:
    if repeat_count > len(development):
        raise ValueError("repeat count exceeds development task count")
    ranked = sorted(
        development,
        key=lambda pair: _task_rank(str(pair[0]["task_id"]), "HIDDEN_REPEAT_SELECTION"),
    )[:repeat_count]
    out = []
    for original_task, original_audit in ranked:
        repeat = build_fixed_voicing_task(
            event_id=str(original_audit["event_id"]),
            fixed_voicing=[
                (row["pitch_midi"], row["string"], row["fret"])
                for row in original_task["fixed_voicing"]
            ],
            export_bucket=BUCKET_DEVELOPMENT,
            presentation_nonce=f"HIDDEN_REPEAT|{original_task['task_id']}",
        )
        if repeat["semantic_fingerprint"] != original_task["semantic_fingerprint"]:
            raise AssertionError("hidden repeat semantic drift")
        audit = dict(original_audit)
        audit.update({
            "task_id": repeat["task_id"],
            "role": "RELIABILITY_REPEAT",
            "export_bucket": BUCKET_DEVELOPMENT,
            "repeat_of": original_task["task_id"],
        })
        out.append((repeat, audit))
    return tuple(out)


def build(
    archive_path: Path,
    output_dir: Path,
    *,
    development_count: int,
    repeat_count: int,
    final_count: int,
    max_assignments: int,
) -> dict:
    source_sha = archive_sha256(archive_path)
    if source_sha != GUITARSET_SOURCE_ARCHIVE_SHA256:
        raise RuntimeError(
            f"STOP: GuitarSet archive SHA mismatch; expected {GUITARSET_SOURCE_ARCHIVE_SHA256}, got {source_sha}"
        )
    accepted = []
    quarantined = []
    with zipfile.ZipFile(archive_path) as archive:
        members = _validated_comp_members(archive_path, archive)
        development_tracks, final_tracks = _track_split(members, source_sha)
        for member in members:
            notes, rejects = extract_comp_jams(member, archive.read(member))
            accepted.extend(notes)
            quarantined.extend(rejects)
    voicings = derive_strum_voicings(accepted)
    candidates = _candidate_rows(voicings, max_assignments=max_assignments)

    used_semantics: set[str] = set()
    development = _select_balanced(
        candidates,
        allowed_tracks=development_tracks,
        count=development_count,
        bucket=BUCKET_DEVELOPMENT,
        used_semantics=used_semantics,
    )
    final = _select_balanced(
        candidates,
        allowed_tracks=final_tracks,
        count=final_count,
        bucket=BUCKET_FINAL,
        used_semantics=used_semantics,
    )
    repeats = _build_repeats(development, repeat_count=repeat_count)

    all_rows = [*development, *repeats, *final]
    all_rows.sort(key=lambda pair: _task_rank(str(pair[0]["task_id"]), "SINGLE_SESSION_PRESENTATION_ORDER"))
    tasks = [task for task, _ in all_rows]
    audits = [audit for _, audit in all_rows]
    manifest = build_single_session_manifest(
        batch_id=BATCH_ID,
        session_id=SESSION_ID,
        tasks=tasks,
    )

    teacher_dir = output_dir / "teacher"
    internal_dir = output_dir / "internal"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)
    html_path = teacher_dir / "ST_Guitar_S2A_V2_Tek_Oturum.html"
    manifest_path = teacher_dir / "ST_Guitar_S2A_V2_Tek_Oturum_manifest.json"
    audit_path = internal_dir / "ST_Guitar_S2A_V2_Tek_Oturum_audit.json"
    html_path.write_text(render_single_session_html(manifest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    original_by_id = {task["task_id"]: task for task, _ in development}
    repeat_pairs = []
    for repeat_task, repeat_audit in repeats:
        original_id = str(repeat_audit["repeat_of"])
        original_task = original_by_id[original_id]
        repeat_pairs.append({
            "original_task_id": original_id,
            "repeat_task_id": repeat_task["task_id"],
            "semantic_fingerprint": original_task["semantic_fingerprint"],
        })

    dev_semantics = {task["semantic_fingerprint"] for task, _ in development}
    final_semantics = {task["semantic_fingerprint"] for task, _ in final}
    if dev_semantics & final_semantics:
        raise AssertionError("S2-A.v2 development/final semantic overlap")
    if {audit["track_key"] for _, audit in development} & {audit["track_key"] for _, audit in final}:
        raise AssertionError("S2-A.v2 development/final track-family overlap")

    audit = {
        "schema": S2A_V2_AUDIT_SCHEMA,
        "protocol_version": S2A_V2_PROTOCOL_VERSION,
        "status": "READY_FOR_ONE_HUMAN_SESSION",
        "source_archive_sha256": source_sha,
        "source_archive_role": "GUITARSET_OBSERVED_STRING_FRET_GEOMETRY_ONLY",
        "source_archive_teacher_label_role": False,
        "accepted_note_count": len(accepted),
        "quarantined_note_count": len(quarantined),
        "derived_voicing_count": len(voicings),
        "eligible_fixed_voicing_task_count": len(candidates),
        "max_assignments_per_task": max_assignments,
        "track_split": {
            "development_tracks": list(development_tracks),
            "final_tracks": list(final_tracks),
            "split_identity_sha256": canonical_sha256({
                "protocol": S2A_V2_PROTOCOL_VERSION,
                "source_sha": source_sha,
                "development_tracks": development_tracks,
                "final_tracks": final_tracks,
            }),
        },
        "development_original_count": len(development),
        "reliability_repeat_count": len(repeats),
        "untouched_final_count": len(final),
        "teacher_presentation_count": len(tasks),
        "repeat_pairs": repeat_pairs,
        "rows": audits,
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "selection_used_teacher_labels": False,
        "selection_used_model_scores": False,
        "selection_used_baseline_scores": False,
        "historical_s2a_v1_labels_used": False,
        "historical_teacher_correction_labels_used": False,
        "real_fit_authorized_before_development_gate": False,
        "final_labels_authorized_before_model_seal": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": audit["status"],
        "source_archive_sha256": source_sha,
        "eligible_fixed_voicing_task_count": len(candidates),
        "development_original_count": len(development),
        "reliability_repeat_count": len(repeats),
        "untouched_final_count": len(final),
        "teacher_presentation_count": len(tasks),
        "development_family_count": len(development_tracks),
        "final_family_count": len(final_tracks),
        "max_assignments_per_task": max_assignments,
        "teacher_manifest_sha256": manifest["manifest_sha256"],
        "html": str(html_path),
        "manifest": str(manifest_path),
        "internal_audit": str(audit_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GuitarSet-anchored S2-A.v2 one-session Teacher package")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--development-count", type=int, default=DEFAULT_DEVELOPMENT_TASKS)
    parser.add_argument("--repeat-count", type=int, default=DEFAULT_REPEAT_TASKS)
    parser.add_argument("--final-count", type=int, default=DEFAULT_FINAL_TASKS)
    parser.add_argument("--max-assignments", type=int, default=DEFAULT_MAX_ASSIGNMENTS)
    args = parser.parse_args()
    if args.development_count < 160 or args.repeat_count < 30 or args.final_count < 50:
        raise SystemExit("STOP: requested S2-A.v2 package is below preregistered evidence minima")
    summary = build(
        args.archive,
        args.output_dir,
        development_count=args.development_count,
        repeat_count=args.repeat_count,
        final_count=args.final_count,
        max_assignments=args.max_assignments,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
