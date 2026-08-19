from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from st_guitar_fingering_training.intake import MAX_SOURCE_BYTES
from st_guitar_fingering_training.s2a_source_reservation import (
    TOTAL_RESERVED_FAMILIES,
    assign_reservation_roles,
    exposed_work_keys_from_filenames,
    fresh_work_groups,
    parse_full_track_tree_entries,
)
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml


ANIMETAB_OWNER = "amamiya-yuuko"
ANIMETAB_REPO = "AnimeTAB"
ANIMETAB_COMMIT = "18c0993cbe0a0948cbf0b7768bcb09ff81c23a9a"
STANDARD_TUNING = (64, 59, 55, 50, 45, 40)
_HEX64 = set("0123456789abcdef")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "st-guitar-fingering-training-s2a-reservation/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str) -> Any:
    request = Request(url, headers=_headers())
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status} for {url}")
        return json.loads(response.read().decode("utf-8"))


def _fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": _headers()["User-Agent"]})
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status} for source")
        raw = response.read(MAX_SOURCE_BYTES + 1)
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"downloaded source byte size outside allowed range: {len(raw)}")
    return raw


def _git_blob_sha1(raw: bytes) -> str:
    prefix = f"blob {len(raw)}\0".encode("ascii")
    return sha1(prefix + raw).hexdigest()


def _collect_sha256_values(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and "sha256" in str(key).casefold():
                candidate = child.casefold()
                if len(candidate) == 64 and all(ch in _HEX64 for ch in candidate):
                    result.add(candidate)
            result.update(_collect_sha256_values(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_collect_sha256_values(child))
    return result


def _source_url(path: str) -> str:
    encoded = quote(path, safe="/")
    return (
        f"https://raw.githubusercontent.com/{ANIMETAB_OWNER}/{ANIMETAB_REPO}/"
        f"{ANIMETAB_COMMIT}/{encoded}"
    )


def _validate_variant(entry, *, family_id: str, quarantine_sha256: set[str], min_chord_events: int):
    if entry.size <= 0 or entry.size > MAX_SOURCE_BYTES:
        raise ValueError("tree source size outside parser limit")
    raw = _fetch_bytes(_source_url(entry.path))
    if len(raw) != entry.size:
        raise ValueError("downloaded byte size does not match pinned Git tree")
    if _git_blob_sha1(raw) != entry.blob_sha:
        raise ValueError("downloaded bytes do not match pinned Git blob SHA")
    raw_sha256 = sha256(raw).hexdigest()
    if raw_sha256 in quarantine_sha256:
        raise ValueError("source raw SHA-256 collides with protected/quarantined evidence")

    with tempfile.NamedTemporaryFile(suffix=".xml") as handle:
        handle.write(raw)
        handle.flush()
        source = parse_target_free_musicxml(
            handle.name,
            family_id=family_id,
            tuning=STANDARD_TUNING,
            pitch_mode="sounding_exact",
            part_id="P1",
            staff_id="2",
        )
    if source.source_sha256 != raw_sha256:
        raise ValueError("target-free parser source SHA-256 mismatch")
    chord_events = tuple(
        event for event in source.events if event.is_chord and len(event.pitches_midi) <= 6
    )
    if len(chord_events) < min_chord_events:
        raise ValueError(f"fewer than {min_chord_events} target-free chord events")
    return raw_sha256, len(source.events), len(chord_events)


def build_reservation(*, old_teacher_manifest: Path, quarantine_manifests: tuple[Path, ...], min_chord_events: int):
    if min_chord_events < 8:
        raise ValueError("fresh reservation minimum chord-event gate cannot be below 8")

    old = _load_json(old_teacher_manifest)
    sources = old.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("old Teacher-exposed manifest has no source list")
    filenames = []
    for row in sources:
        if not isinstance(row, dict) or not isinstance(row.get("filename"), str):
            raise ValueError("old Teacher-exposed source row is malformed")
        filenames.append(row["filename"])
    exposed_keys = exposed_work_keys_from_filenames(filenames)

    quarantine_sha256: set[str] = set()
    for path in quarantine_manifests:
        quarantine_sha256.update(_collect_sha256_values(_load_json(path)))

    tree_url = (
        f"https://api.github.com/repos/{ANIMETAB_OWNER}/{ANIMETAB_REPO}/git/trees/"
        f"{ANIMETAB_COMMIT}?recursive=1"
    )
    tree = _fetch_json(tree_url)
    if not isinstance(tree, dict) or tree.get("truncated") is True:
        raise ValueError("pinned AnimeTAB recursive Git tree is missing or truncated")
    rows = tree.get("tree")
    if not isinstance(rows, list):
        raise ValueError("pinned AnimeTAB tree response has no tree rows")

    entries = parse_full_track_tree_entries(rows)
    all_work_keys = {entry.canonical_work_key for entry in entries}
    groups = fresh_work_groups(
        entries,
        pinned_commit=ANIMETAB_COMMIT,
        exposed_work_keys=exposed_keys,
    )
    if len(groups) < TOTAL_RESERVED_FAMILIES:
        raise ValueError(
            f"only {len(groups)} fresh canonical works remain before structural validation; "
            f"need {TOTAL_RESERVED_FAMILIES}"
        )

    qualified = []
    rejected_reasons = Counter()
    attempted_works = 0
    attempted_variants = 0
    for work_key, variants in groups:
        attempted_works += 1
        family_id = f"animetabs2a-{sha256(work_key.encode('utf-8')).hexdigest()[:20]}"
        accepted = None
        for entry in variants:
            attempted_variants += 1
            try:
                raw_sha256, pitched_events, chord_events = _validate_variant(
                    entry,
                    family_id=family_id,
                    quarantine_sha256=quarantine_sha256,
                    min_chord_events=min_chord_events,
                )
            except (ValueError, RuntimeError, OSError) as exc:
                rejected_reasons[str(exc)] += 1
                continue
            accepted = (work_key, entry, raw_sha256, pitched_events, chord_events)
            break
        if accepted is not None:
            qualified.append(accepted)
        if len(qualified) >= TOTAL_RESERVED_FAMILIES:
            break

    reserved = assign_reservation_roles(qualified)
    role_counts = Counter(item.role for item in reserved)
    reservation_identity = [
        {
            "role": item.role,
            "ordinal": item.ordinal,
            "family_id": item.family_id,
            "canonical_work_key": item.canonical_work_key,
            "path": item.path,
            "blob_sha": item.blob_sha,
            "raw_sha256": item.raw_sha256,
            "byte_size": item.byte_size,
            "pitched_event_count": item.pitched_event_count,
            "chord_event_count": item.chord_event_count,
        }
        for item in reserved
    ]
    identity_bytes = json.dumps(
        reservation_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    return {
        "schema": "st-guitar-stage7g-e3-s2a-fresh-source-reservation-census-v1",
        "stage": "7G-E3-S2-A-FRESH-SOURCE-RESERVATION",
        "status": "PROVISIONAL_STRUCTURAL_RESERVATION_PENDING_HC_CAPACITY_AUDIT",
        "selection": {
            "label_blind": True,
            "teacher_responses_loaded": False,
            "model_scores_loaded": False,
            "pinned_dataset": "AnimeTAB",
            "pinned_commit": ANIMETAB_COMMIT,
            "scope": "AnimeTAB/Entire songs/*.xml only",
            "canonical_work_key_used_for_variant_leakage_control": True,
            "one_source_variant_per_canonical_work": True,
            "raw_source_bytes_retained": False,
            "part_id": "P1",
            "staff_id": "2",
            "pitch_mode": "sounding_exact",
            "tuning_midi": list(STANDARD_TUNING),
            "min_target_free_chord_events": min_chord_events,
        },
        "census": {
            "full_track_xml_blob_count": len(entries),
            "canonical_work_count_before_exposure_exclusion": len(all_work_keys),
            "teacher_exposed_exact_file_count": len(filenames),
            "teacher_exposed_canonical_work_key_count": len(exposed_keys),
            "fresh_canonical_work_count_before_structural_validation": len(groups),
            "attempted_work_count_until_120_qualified": attempted_works,
            "attempted_variant_count_until_120_qualified": attempted_variants,
            "qualified_work_count": len(qualified),
            "rejected_variant_reason_counts": dict(sorted(rejected_reasons.items())),
            "quarantine_sha256_value_count": len(quarantine_sha256),
        },
        "reservation": {
            "total": len(reserved),
            "role_counts": dict(sorted(role_counts.items())),
            "identity_sha256": sha256(identity_bytes).hexdigest(),
            "sources": reservation_identity,
        },
        "scientific_boundary": {
            "h_c_capacity_audit_executed": False,
            "teacher_task_identities_frozen": False,
            "new_teacher_labels_collected": False,
            "real_model_fit_executed": False,
            "untouched_final_opened": False,
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
        },
        "next_gate": "RUN_HC_CAPACITY_AUDIT_AND_FREEZE_FINAL_80_20_20_SOURCE_RESERVATION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-teacher-manifest", type=Path, required=True)
    parser.add_argument("--quarantine-manifest", type=Path, action="append", default=[])
    parser.add_argument("--min-chord-events", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_reservation(
        old_teacher_manifest=args.old_teacher_manifest,
        quarantine_manifests=tuple(args.quarantine_manifest),
        min_chord_events=args.min_chord_events,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    census = payload["census"]
    reservation = payload["reservation"]
    print(
        "S2-A fresh source census PASS: "
        f"full_track_xml={census['full_track_xml_blob_count']} "
        f"fresh_works={census['fresh_canonical_work_count_before_structural_validation']} "
        f"qualified={census['qualified_work_count']} "
        f"reserved={reservation['total']} "
        f"identity={reservation['identity_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
