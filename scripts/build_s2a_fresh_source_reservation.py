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
from st_guitar_fingering_training.s2a_source_isolation import (
    QualifiedIsolatedSource,
    assign_origin_isolated_roles,
    evaluate_source_isolation,
    exposed_origin_keys_from_filenames,
    historical_origin_quarantine,
    load_alias_groups,
    origin_family_id,
    resolved_origin_group_key,
)
from st_guitar_fingering_training.s2a_source_reservation import (
    TOTAL_RESERVED_FAMILIES,
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


def _canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


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


def build_reservation(
    *,
    old_teacher_manifest: Path,
    origin_alias_manifest: Path,
    quarantine_manifests: tuple[Path, ...],
    min_chord_events: int,
):
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
    exposed_work_keys = exposed_work_keys_from_filenames(filenames)
    raw_exposed_origin_keys = exposed_origin_keys_from_filenames(filenames)

    alias_payload = _load_json(origin_alias_manifest)
    alias_groups = load_alias_groups(alias_payload)
    historical_quarantine = historical_origin_quarantine(
        exposed_origin_keys=raw_exposed_origin_keys,
        alias_groups=alias_groups,
    )

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
        exposed_work_keys=exposed_work_keys,
    )
    if len(groups) < TOTAL_RESERVED_FAMILIES:
        raise ValueError(
            f"only {len(groups)} fresh canonical works remain before source isolation; "
            f"need at least {TOTAL_RESERVED_FAMILIES} source candidates"
        )

    qualified: list[QualifiedIsolatedSource] = []
    qualified_raw_hashes: set[str] = set()
    structural_rejected_reasons = Counter()
    isolation_rejected_reasons = Counter()
    attempted_works = 0
    attempted_variants = 0

    for work_key, variants in groups:
        attempted_works += 1
        try:
            variant_origins = {
                resolved_origin_group_key(entry.filename, alias_groups=alias_groups)
                for entry in variants
            }
        except ValueError:
            isolation_rejected_reasons["S2A_SRC_005_IDENTITY_AMBIGUOUS"] += 1
            continue
        if len(variant_origins) != 1:
            isolation_rejected_reasons["S2A_SRC_005_IDENTITY_AMBIGUOUS"] += 1
            continue
        origin = next(iter(variant_origins))
        decision = evaluate_source_isolation(
            variants[0].filename,
            historical_quarantine=historical_quarantine,
            alias_groups=alias_groups,
        )
        if not decision.accepted:
            isolation_rejected_reasons[decision.reason] += 1
            continue
        if decision.origin_group_key != origin:
            raise AssertionError("source isolation resolver changed origin identity")

        source_family_id = origin_family_id(origin)
        accepted = None
        for entry in variants:
            attempted_variants += 1
            try:
                raw_sha256, pitched_events, chord_events = _validate_variant(
                    entry,
                    family_id=source_family_id,
                    quarantine_sha256=quarantine_sha256,
                    min_chord_events=min_chord_events,
                )
            except (ValueError, RuntimeError, OSError) as exc:
                structural_rejected_reasons[str(exc)] += 1
                continue
            if raw_sha256 in qualified_raw_hashes:
                isolation_rejected_reasons["S2A_SRC_001_EXACT_SOURCE_DUPLICATE"] += 1
                continue
            accepted = QualifiedIsolatedSource(
                canonical_work_key=work_key,
                origin_group_key=origin,
                path=entry.path,
                blob_sha=entry.blob_sha,
                raw_sha256=raw_sha256,
                byte_size=entry.size,
                pitched_event_count=pitched_events,
                chord_event_count=chord_events,
            )
            break
        if accepted is not None:
            qualified.append(accepted)
            qualified_raw_hashes.add(accepted.raw_sha256)

    reserved = assign_origin_isolated_roles(qualified, pinned_commit=ANIMETAB_COMMIT)
    role_counts = Counter(item.role for item in reserved)
    family_counts_by_role = {
        role: len({item.family_id for item in reserved if item.role == role})
        for role in role_counts
    }
    origins_by_role = {
        role: {item.origin_group_key for item in reserved if item.role == role}
        for role in role_counts
    }
    cross_role_origin_overlap_count = sum(
        len(origins_by_role[left] & origins_by_role[right])
        for left, right in (
            ("PRIMARY_DEVELOPMENT", "CONTINGENCY_DEVELOPMENT"),
            ("PRIMARY_DEVELOPMENT", "UNTOUCHED_FINAL"),
            ("CONTINGENCY_DEVELOPMENT", "UNTOUCHED_FINAL"),
        )
    )
    reservation_identity = [
        {
            "role": item.role,
            "ordinal": item.ordinal,
            "family_id": item.family_id,
            "canonical_work_key": item.canonical_work_key,
            "origin_group_key": item.origin_group_key,
            "path": item.path,
            "blob_sha": item.blob_sha,
            "raw_sha256": item.raw_sha256,
            "byte_size": item.byte_size,
            "pitched_event_count": item.pitched_event_count,
            "chord_event_count": item.chord_event_count,
        }
        for item in reserved
    ]
    if any(row["origin_group_key"] in historical_quarantine for row in reservation_identity):
        raise AssertionError("accepted S2-A reservation overlaps historical origin quarantine")
    if cross_role_origin_overlap_count:
        raise AssertionError("origin family leaked across development/contingency/final roles")

    identity_bytes = json.dumps(
        reservation_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    qualified_origin_count = len({item.origin_group_key for item in qualified})

    return {
        "schema": "st-guitar-stage7g-e3-s2a-fresh-source-reservation-census-v2",
        "stage": "7G-E3-S2-A-FRESH-SOURCE-RESERVATION",
        "status": "PROVISIONAL_ISOLATED_RESERVATION_PENDING_HC_CAPACITY_AUDIT",
        "selection": {
            "label_blind": True,
            "teacher_responses_loaded": False,
            "model_scores_loaded": False,
            "pinned_dataset": "AnimeTAB",
            "pinned_commit": ANIMETAB_COMMIT,
            "scope": "AnimeTAB/Entire songs/*.xml only",
            "canonical_work_key_used_for_variant_leakage_control": True,
            "historical_origin_franchise_quarantine_enabled": True,
            "alias_groups_resolve_all_source_family_identities": True,
            "origin_alias_manifest_sha256": _canonical_json_sha256(alias_payload),
            "missing_or_ambiguous_origin_policy": "REJECT",
            "cross_role_origin_reuse_policy": "REJECT",
            "same_primary_origin_multiple_sources_policy": "ALLOWED_ONLY_AS_ONE_SHARED_FAMILY",
            "family_id_semantics": "canonical alias-resolved origin/franchise group",
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
            "teacher_exposed_canonical_work_key_count": len(exposed_work_keys),
            "teacher_exposed_raw_origin_key_count": len(raw_exposed_origin_keys),
            "historical_origin_family_quarantine_count": len(historical_quarantine),
            "fresh_canonical_work_count_before_source_isolation": len(groups),
            "attempted_work_count": attempted_works,
            "attempted_variant_count": attempted_variants,
            "qualified_work_count": len(qualified),
            "qualified_origin_family_count": qualified_origin_count,
            "source_isolation_rejected_reason_counts": dict(sorted(isolation_rejected_reasons.items())),
            "structural_rejected_variant_reason_counts": dict(sorted(structural_rejected_reasons.items())),
            "quarantine_sha256_value_count": len(quarantine_sha256),
        },
        "reservation": {
            "total_source_count": len(reserved),
            "source_role_counts": dict(sorted(role_counts.items())),
            "family_counts_by_role": dict(sorted(family_counts_by_role.items())),
            "unique_origin_family_count": len({row["origin_group_key"] for row in reservation_identity}),
            "historical_origin_overlap_count": sum(
                row["origin_group_key"] in historical_quarantine for row in reservation_identity
            ),
            "cross_role_origin_overlap_count": cross_role_origin_overlap_count,
            "identity_sha256": sha256(identity_bytes).hexdigest(),
            "sources": reservation_identity,
        },
        "scientific_boundary": {
            "source_identity_isolation_gate_passed": True,
            "h_c_capacity_audit_executed": False,
            "teacher_task_identities_frozen": False,
            "new_teacher_labels_collected": False,
            "real_model_fit_executed": False,
            "untouched_final_opened": False,
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
        },
        "next_gate": "RUN_HC_CAPACITY_AUDIT_BEFORE_FREEZING_TEACHER_TASK_IDENTITIES",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-teacher-manifest", type=Path, required=True)
    parser.add_argument("--origin-alias-manifest", type=Path, required=True)
    parser.add_argument("--quarantine-manifest", type=Path, action="append", default=[])
    parser.add_argument("--min-chord-events", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_reservation(
        old_teacher_manifest=args.old_teacher_manifest,
        origin_alias_manifest=args.origin_alias_manifest,
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
        "S2-A isolated fresh source census PASS: "
        f"full_track_xml={census['full_track_xml_blob_count']} "
        f"qualified_works={census['qualified_work_count']} "
        f"qualified_origins={census['qualified_origin_family_count']} "
        f"reserved_sources={reservation['total_source_count']} "
        f"reserved_families={reservation['unique_origin_family_count']} "
        f"identity={reservation['identity_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
