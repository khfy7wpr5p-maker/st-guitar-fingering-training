from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from build_s2a_fresh_source_reservation import (
    ANIMETAB_COMMIT,
    STANDARD_TUNING,
    _fetch_bytes,
    _git_blob_sha1,
    _source_url,
)
from run_s2a_hc_capacity_audit import build_hc_capacity_audit
from st_guitar_fingering_training.s2a_batch import (
    batch_summary,
    render_teacher_html,
    select_balanced_batch,
    split_sessions,
)
from st_guitar_fingering_training.s2a_source_pool import build_bounded_real_source_pool
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml


FREEZE_SCHEMA = "st-guitar-stage7g-e3-s2a-hc-qualified-reservation-freeze-v1"
BATCH02_SCHEMA = "st-guitar-stage7g-e3-s2a-batch02-manifest-v1"
BATCH02_FAMILY_COUNT = 40
BATCH02_TASK_COUNT = 720
PRIMARY_ROLE = "PRIMARY_DEVELOPMENT"


def _canonical_sha(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _load_and_verify_freeze(path: Path) -> tuple[dict, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != FREEZE_SCHEMA or payload.get("status") != "FROZEN":
        raise RuntimeError("STOP: unexpected or unfrozen H-C reservation manifest")
    stored = str(payload.get("manifest_sha256", ""))
    body = dict(payload)
    body.pop("manifest_sha256", None)
    if _canonical_sha(body) != stored:
        raise RuntimeError("STOP: H-C reservation freeze manifest SHA mismatch")
    policy = payload.get("freeze_policy", {})
    if policy.get("reservation_identity_immutable") is not True:
        raise RuntimeError("STOP: reservation identity is not frozen")
    if policy.get("batch02_source_role") != PRIMARY_ROLE:
        raise RuntimeError("STOP: Batch02 source role drift")
    if policy.get("batch02_may_use_contingency") is not False:
        raise RuntimeError("STOP: Batch02 contingency boundary opened")
    if policy.get("batch02_may_use_untouched_final") is not False:
        raise RuntimeError("STOP: Batch02 untouched-final boundary opened")
    return payload, stored


def _reproduce_frozen_reservation(args, freeze: dict) -> dict:
    audit = build_hc_capacity_audit(
        old_teacher_manifest=args.old_teacher_manifest,
        origin_alias_manifest=args.origin_alias_manifest,
        quarantine_manifests=tuple(args.quarantine_manifest),
        prior_final_semantic_quarantine=args.prior_final_semantic_quarantine,
    )
    if audit.get("status") != "PASS":
        raise RuntimeError("STOP: reproduced H-C audit did not PASS")
    final = audit.get("final_reservation", {})
    expected = freeze["reservation"]
    if final.get("identity_sha256") != expected.get("identity_sha256"):
        raise RuntimeError("STOP: reproduced reservation identity differs from frozen identity")
    if final.get("total_source_count") != expected.get("total_source_count"):
        raise RuntimeError("STOP: reproduced reservation source count drift")
    if final.get("invariants", {}).get("source_counts_by_role") != expected.get("source_counts_by_role"):
        raise RuntimeError("STOP: reproduced role counts drift")
    if final.get("invariants", {}).get("family_counts_by_role") != expected.get("family_counts_by_role"):
        raise RuntimeError("STOP: reproduced family counts drift")
    if any(row.get("hc_capacity", {}).get("status") != "PASS" for row in final.get("sources", [])):
        raise RuntimeError("STOP: frozen reservation contains a non-PASS H-C source")
    return audit


def _select_primary_representatives(audit: dict, freeze_sha: str) -> tuple[dict, ...]:
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
    ranked_families = sorted(
        by_family,
        key=lambda family_id: sha256(
            f"{freeze_sha}|S2A_BATCH02|family|{family_id}".encode("utf-8")
        ).hexdigest(),
    )
    selected_families = ranked_families[:BATCH02_FAMILY_COUNT]
    representatives = []
    for family_id in selected_families:
        rows = sorted(
            by_family[family_id],
            key=lambda row: sha256(
                f"{freeze_sha}|S2A_BATCH02|source|{row['path']}|{row['raw_sha256']}".encode("utf-8")
            ).hexdigest(),
        )
        representatives.append(rows[0])
    if len(representatives) != 40 or len({row["family_id"] for row in representatives}) != 40:
        raise RuntimeError("STOP: Batch02 representative-family selection failed")
    if any(row["role"] != PRIMARY_ROLE for row in representatives):
        raise RuntimeError("STOP: non-primary source entered Batch02")
    return tuple(representatives)


def _load_sources(rows: tuple[dict, ...]):
    sources = []
    with TemporaryDirectory() as temp:
        root = Path(temp)
        for index, row in enumerate(rows, start=1):
            raw = _fetch_bytes(_source_url(str(row["path"])))
            if len(raw) != int(row["byte_size"]):
                raise RuntimeError("STOP: Batch02 source byte-size drift")
            if _git_blob_sha1(raw) != row["blob_sha"]:
                raise RuntimeError("STOP: Batch02 Git blob SHA drift")
            raw_sha = sha256(raw).hexdigest()
            if raw_sha != row["raw_sha256"]:
                raise RuntimeError("STOP: Batch02 raw SHA-256 drift")
            local = root / f"{index:03d}.xml"
            local.write_bytes(raw)
            source = parse_target_free_musicxml(
                local,
                family_id=row["family_id"],
                tuning=STANDARD_TUNING,
                pitch_mode="sounding_exact",
                part_id="P1",
                staff_id="2",
            )
            if source.source_sha256 != row["raw_sha256"]:
                raise RuntimeError("STOP: Batch02 parser source identity drift")
            sources.append(source)
    return tuple(sources)


def _retag_sessions(sessions):
    output = []
    for index, (manifest, audit) in enumerate(sessions, start=1):
        session_id = f"S2A_BATCH02_SESSION_{index:02d}"
        manifest = dict(manifest)
        manifest["session_id"] = session_id
        manifest.pop("manifest_sha256", None)
        manifest["manifest_sha256"] = _canonical_sha(manifest)
        audit = dict(audit)
        audit["session_id"] = session_id
        output.append((manifest, audit))
    return tuple(output)


def build(args) -> dict:
    freeze, freeze_sha = _load_and_verify_freeze(args.freeze_manifest)
    reproduced = _reproduce_frozen_reservation(args, freeze)
    representatives = _select_primary_representatives(reproduced, freeze_sha)
    sources = _load_sources(representatives)
    packages = build_bounded_real_source_pool(sources)
    selected = select_balanced_batch(packages, expected_families=BATCH02_FAMILY_COUNT)
    if len(selected) != BATCH02_TASK_COUNT:
        raise RuntimeError("STOP: Batch02 selected task count drift")
    sessions = _retag_sessions(split_sessions(selected))
    summary = batch_summary(selected, sessions)
    summary.update({
        "schema": BATCH02_SCHEMA,
        "batch_id": "S2A_BATCH02",
        "status": "READY_FOR_BLIND_FIRST_PASS_COLLECTION",
        "source_dataset": "AnimeTAB",
        "source_commit": ANIMETAB_COMMIT,
        "source_freeze_manifest_path": str(args.freeze_manifest),
        "source_freeze_manifest_sha256": freeze_sha,
        "reproduced_reservation_identity_sha256": reproduced["final_reservation"]["identity_sha256"],
        "allowed_source_role": PRIMARY_ROLE,
        "selected_primary_family_count": len({row["family_id"] for row in representatives}),
        "selected_primary_source_count": len(representatives),
        "contingency_sources_used": 0,
        "untouched_final_sources_used": 0,
        "historical_teacher_responses_reused": False,
        "source_family_identities_reused_as_label_free_music_sources": False,
        "teacher_task_generation_used_labels": False,
        "teacher_task_generation_used_model_scores": False,
        "eligible_event_package_count": len(packages),
    })
    summary["batch_manifest_sha256"] = _canonical_sha(summary)

    teacher_dir = args.output_dir / "teacher"
    internal_dir = args.output_dir / "internal"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)
    for index, (manifest, audit) in enumerate(sessions, start=1):
        stem = f"ST_Guitar_S2A_Batch02_Session{index:02d}"
        html_manifest = dict(manifest)
        html_manifest.pop("family_identity", None)
        (teacher_dir / f"{stem}.html").write_text(render_teacher_html(html_manifest), encoding="utf-8")
        (teacher_dir / f"{stem}_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (internal_dir / f"{stem}_audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    (teacher_dir / "ST_Guitar_S2A_Batch02_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    internal_summary = dict(summary)
    internal_summary["selected_sources"] = [
        {
            "family_id": row["family_id"],
            "path": row["path"],
            "raw_sha256": row["raw_sha256"],
            "origin_group_key": row["origin_group_key"],
        }
        for row in representatives
    ]
    (internal_dir / "ST_Guitar_S2A_Batch02_internal_summary.json").write_text(
        json.dumps(internal_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build S2-A Batch02 only from the frozen H-C-qualified reservation")
    parser.add_argument("--freeze-manifest", type=Path, required=True)
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
