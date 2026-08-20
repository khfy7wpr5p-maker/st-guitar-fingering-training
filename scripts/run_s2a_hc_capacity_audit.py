from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

from build_s2a_fresh_source_reservation import (
    ANIMETAB_COMMIT,
    ANIMETAB_OWNER,
    ANIMETAB_REPO,
    STANDARD_TUNING,
    _collect_sha256_values,
    _fetch_bytes,
    _fetch_json,
    _git_blob_sha1,
    _load_json,
    _source_url,
)
from st_guitar_fingering_training.intake import MAX_SOURCE_BYTES
from st_guitar_fingering_training.s2a_hc_capacity import (
    S2A_HC_CAPACITY_RULE_VERSION,
    S2A_HC_MIN_ELIGIBLE_EVENTS,
    audit_hc_capacity,
    audit_to_dict,
)
from st_guitar_fingering_training.s2a_prior_final_semantics import (
    load_prior_final_semantic_quarantine,
    reserved_semantic_overlaps,
)
from st_guitar_fingering_training.s2a_source_isolation import (
    QualifiedIsolatedSource,
    ReservedIsolatedSource,
    assign_origin_isolated_roles,
    evaluate_source_isolation,
    exposed_origin_keys_from_filenames,
    historical_origin_quarantine,
    load_alias_groups,
    origin_family_id,
    resolved_origin_group_key,
)
from st_guitar_fingering_training.s2a_source_reservation import (
    exposed_work_keys_from_filenames,
    fresh_work_groups,
    parse_full_track_tree_entries,
)
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml


SCHEMA = "st-guitar-stage7g-e3-s2a-hc-capacity-audit-v1"
ROLE_ORDER = {
    "PRIMARY_DEVELOPMENT": 0,
    "CONTINGENCY_DEVELOPMENT": 1,
    "UNTOUCHED_FINAL": 2,
}
EXPECTED_SOURCE_COUNTS = {
    "PRIMARY_DEVELOPMENT": 80,
    "CONTINGENCY_DEVELOPMENT": 20,
    "UNTOUCHED_FINAL": 20,
}


def _canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _source_identity(row) -> dict:
    return {
        "role": row.role,
        "ordinal": int(row.ordinal),
        "family_id": row.family_id,
        "canonical_work_key": row.canonical_work_key,
        "origin_group_key": row.origin_group_key,
        "path": row.path,
        "blob_sha": row.blob_sha,
        "raw_sha256": row.raw_sha256,
        "byte_size": int(row.byte_size),
        "pitched_event_count": int(row.pitched_event_count),
        "chord_event_count": int(row.chord_event_count),
    }


def _qualified_identity(row: QualifiedIsolatedSource, *, sequence_ordinal: int) -> dict:
    return {
        "sequence_ordinal": int(sequence_ordinal),
        "family_id": origin_family_id(row.origin_group_key),
        "canonical_work_key": row.canonical_work_key,
        "origin_group_key": row.origin_group_key,
        "path": row.path,
        "blob_sha": row.blob_sha,
        "raw_sha256": row.raw_sha256,
        "byte_size": int(row.byte_size),
        "pitched_event_count": int(row.pitched_event_count),
        "chord_event_count": int(row.chord_event_count),
    }


def _reserved_from_qualified(candidate: QualifiedIsolatedSource, *, role: str, ordinal: int) -> ReservedIsolatedSource:
    return ReservedIsolatedSource(
        role=role,
        ordinal=int(ordinal),
        family_id=origin_family_id(candidate.origin_group_key),
        canonical_work_key=candidate.canonical_work_key,
        origin_group_key=candidate.origin_group_key,
        path=candidate.path,
        blob_sha=candidate.blob_sha,
        raw_sha256=candidate.raw_sha256,
        byte_size=int(candidate.byte_size),
        pitched_event_count=int(candidate.pitched_event_count),
        chord_event_count=int(candidate.chord_event_count),
    )


def _reservation_invariants(rows: tuple[ReservedIsolatedSource, ...]) -> dict:
    counts = Counter(row.role for row in rows)
    origins_by_role = {
        role: {row.origin_group_key for row in rows if row.role == role}
        for role in ROLE_ORDER
    }
    families_by_role = {
        role: {row.family_id for row in rows if row.role == role}
        for role in ROLE_ORDER
    }
    cross_role_overlap = sum(
        len(origins_by_role[left] & origins_by_role[right])
        for left, right in (
            ("PRIMARY_DEVELOPMENT", "CONTINGENCY_DEVELOPMENT"),
            ("PRIMARY_DEVELOPMENT", "UNTOUCHED_FINAL"),
            ("CONTINGENCY_DEVELOPMENT", "UNTOUCHED_FINAL"),
        )
    )
    paths = [row.path for row in rows]
    raw_hashes = [row.raw_sha256 for row in rows]
    works = [row.canonical_work_key for row in rows]
    valid = (
        dict(counts) == EXPECTED_SOURCE_COUNTS
        and len(rows) == 120
        and len(paths) == len(set(paths))
        and len(raw_hashes) == len(set(raw_hashes))
        and len(works) == len(set(works))
        and cross_role_overlap == 0
        and len(families_by_role["PRIMARY_DEVELOPMENT"]) >= 40
        and len(families_by_role["CONTINGENCY_DEVELOPMENT"]) == 20
        and len(families_by_role["UNTOUCHED_FINAL"]) == 20
    )
    return {
        "pass": bool(valid),
        "source_counts_by_role": dict(sorted(counts.items())),
        "family_counts_by_role": {
            role: len(families_by_role[role]) for role in sorted(families_by_role)
        },
        "cross_role_origin_overlap_count": cross_role_overlap,
        "unique_path_count": len(set(paths)),
        "unique_raw_sha256_count": len(set(raw_hashes)),
        "unique_work_count": len(set(works)),
    }


def _candidate_fits_slot(
    current_without_failed: tuple[ReservedIsolatedSource, ...],
    candidate: QualifiedIsolatedSource,
    *,
    role: str,
    ordinal: int,
) -> tuple[bool, str, ReservedIsolatedSource]:
    replacement = _reserved_from_qualified(candidate, role=role, ordinal=ordinal)
    origins_other_roles = {
        row.role
        for row in current_without_failed
        if row.origin_group_key == replacement.origin_group_key and row.role != role
    }
    if origins_other_roles:
        return False, "S2A_HC_REPL_002_CROSS_ROLE_ORIGIN_CONFLICT", replacement
    if role in ("CONTINGENCY_DEVELOPMENT", "UNTOUCHED_FINAL"):
        if any(
            row.origin_group_key == replacement.origin_group_key and row.role == role
            for row in current_without_failed
        ):
            return False, "S2A_HC_REPL_003_INDEPENDENT_FAMILY_REQUIRED", replacement

    tentative = tuple(sorted(
        current_without_failed + (replacement,),
        key=lambda row: (ROLE_ORDER[row.role], row.ordinal, row.path),
    ))
    inv = _reservation_invariants(tentative)
    if not inv["pass"]:
        return False, "S2A_HC_REPL_004_RESERVATION_INVARIANT", replacement
    return True, "S2A_HC_REPL_000_ELIGIBLE", replacement


def _qualify_variant_and_audit(entry, *, family_id: str, quarantine_sha256: set[str]):
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
    if len(chord_events) < S2A_HC_MIN_ELIGIBLE_EVENTS:
        raise ValueError(
            f"fewer than {S2A_HC_MIN_ELIGIBLE_EVENTS} target-free chord events"
        )
    hc_audit = audit_hc_capacity(
        source.events,
        min_eligible_events=S2A_HC_MIN_ELIGIBLE_EVENTS,
    )
    return raw_sha256, source, len(chord_events), hc_audit


def build_hc_capacity_audit(
    *,
    old_teacher_manifest: Path,
    origin_alias_manifest: Path,
    quarantine_manifests: tuple[Path, ...],
    prior_final_semantic_quarantine: Path,
) -> dict:
    old = _load_json(old_teacher_manifest)
    old_sources = old.get("sources")
    if not isinstance(old_sources, list) or not old_sources:
        raise ValueError("old Teacher-exposed manifest has no source list")
    filenames = []
    for row in old_sources:
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

    semantic_payload = _load_json(prior_final_semantic_quarantine)
    semantic_quarantine = load_prior_final_semantic_quarantine(semantic_payload)
    if semantic_quarantine.family_count != 40:
        raise ValueError("prior-final semantic family quarantine must remain frozen at 40")

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
    tree_rows = tree.get("tree")
    if not isinstance(tree_rows, list):
        raise ValueError("pinned AnimeTAB tree response has no tree rows")

    entries = parse_full_track_tree_entries(tree_rows)
    groups = fresh_work_groups(
        entries,
        pinned_commit=ANIMETAB_COMMIT,
        exposed_work_keys=exposed_work_keys,
    )

    qualified: list[QualifiedIsolatedSource] = []
    hc_by_path = {}
    qualified_raw_hashes: set[str] = set()
    structural_rejections = Counter()
    isolation_rejections = Counter()
    semantic_rejections = Counter()

    for work_key, variants in groups:
        semantic_hits = reserved_semantic_overlaps(
            [entry.path for entry in variants],
            quarantine=semantic_quarantine,
        )
        if semantic_hits:
            semantic_rejections["S2A_SRC_007_PRIOR_FINAL_SEMANTIC_OVERLAP"] += 1
            continue
        try:
            variant_origins = {
                resolved_origin_group_key(entry.filename, alias_groups=alias_groups)
                for entry in variants
            }
        except ValueError:
            isolation_rejections["S2A_SRC_005_IDENTITY_AMBIGUOUS"] += 1
            continue
        if len(variant_origins) != 1:
            isolation_rejections["S2A_SRC_005_IDENTITY_AMBIGUOUS"] += 1
            continue
        origin = next(iter(variant_origins))
        decision = evaluate_source_isolation(
            variants[0].filename,
            historical_quarantine=historical_quarantine,
            alias_groups=alias_groups,
        )
        if not decision.accepted:
            isolation_rejections[decision.reason] += 1
            continue
        if decision.origin_group_key != origin:
            raise AssertionError("source isolation resolver changed origin identity")

        accepted = None
        family_id = origin_family_id(origin)
        for entry in variants:
            try:
                raw_sha256, source, chord_event_count, hc_audit = _qualify_variant_and_audit(
                    entry,
                    family_id=family_id,
                    quarantine_sha256=quarantine_sha256,
                )
            except (ValueError, RuntimeError, OSError) as exc:
                structural_rejections[str(exc)] += 1
                continue
            if raw_sha256 in qualified_raw_hashes:
                isolation_rejections["S2A_SRC_001_EXACT_SOURCE_DUPLICATE"] += 1
                continue
            accepted = QualifiedIsolatedSource(
                canonical_work_key=work_key,
                origin_group_key=origin,
                path=entry.path,
                blob_sha=entry.blob_sha,
                raw_sha256=raw_sha256,
                byte_size=entry.size,
                pitched_event_count=len(source.events),
                chord_event_count=chord_event_count,
            )
            hc_by_path[entry.path] = hc_audit
            break
        if accepted is not None:
            qualified.append(accepted)
            qualified_raw_hashes.add(accepted.raw_sha256)

    initial = assign_origin_isolated_roles(qualified, pinned_commit=ANIMETAB_COMMIT)
    initial_invariants = _reservation_invariants(initial)
    if not initial_invariants["pass"]:
        raise AssertionError("initial source reservation invariants failed before H-C replacement")

    initial_paths = {row.path for row in initial}
    initial_audits = [
        {
            **_source_identity(row),
            "hc_capacity": audit_to_dict(hc_by_path[row.path]),
        }
        for row in initial
    ]
    initial_failures = [row for row in initial if not hc_by_path[row.path].passed]
    initial_role_summary = {}
    for role in ROLE_ORDER:
        role_rows = [row for row in initial if row.role == role]
        passed = sum(hc_by_path[row.path].passed for row in role_rows)
        initial_role_summary[role] = {
            "total": len(role_rows),
            "pass": passed,
            "fail": len(role_rows) - passed,
        }

    sequence_ordinal = {row.path: index for index, row in enumerate(qualified, start=1)}
    replacement_pool = tuple(
        row for row in qualified if row.path not in initial_paths
    )
    current = list(initial)
    used_paths = set(initial_paths)
    replacements = []
    unfilled_failures = []
    global_hc_rejected_candidates: dict[str, dict] = {}

    for failed in sorted(initial_failures, key=lambda row: (ROLE_ORDER[row.role], row.ordinal, row.path)):
        current_without = tuple(row for row in current if row.path != failed.path)
        attempts = []
        chosen = None
        chosen_reserved = None
        for candidate in replacement_pool:
            if candidate.path in used_paths:
                continue
            hc_audit = hc_by_path[candidate.path]
            if not hc_audit.passed:
                if candidate.path not in global_hc_rejected_candidates:
                    global_hc_rejected_candidates[candidate.path] = {
                        **_qualified_identity(candidate, sequence_ordinal=sequence_ordinal[candidate.path]),
                        "reason": "S2A_HC_REPL_001_HC_CAPACITY_FAIL",
                        "hc_capacity": audit_to_dict(hc_audit),
                    }
                attempts.append({
                    "sequence_ordinal": sequence_ordinal[candidate.path],
                    "path": candidate.path,
                    "decision": "SKIP_HC_CAPACITY_FAIL",
                })
                continue
            fits, reason, replacement = _candidate_fits_slot(
                current_without,
                candidate,
                role=failed.role,
                ordinal=failed.ordinal,
            )
            if not fits:
                attempts.append({
                    "sequence_ordinal": sequence_ordinal[candidate.path],
                    "path": candidate.path,
                    "decision": "SKIP_ROLE_INVARIANT",
                    "reason": reason,
                })
                continue
            chosen = candidate
            chosen_reserved = replacement
            attempts.append({
                "sequence_ordinal": sequence_ordinal[candidate.path],
                "path": candidate.path,
                "decision": "SELECT",
            })
            break

        if chosen is None or chosen_reserved is None:
            unfilled_failures.append({
                **_source_identity(failed),
                "hc_capacity": audit_to_dict(hc_by_path[failed.path]),
                "replacement_attempts": attempts,
            })
            continue

        current = list(current_without) + [chosen_reserved]
        current.sort(key=lambda row: (ROLE_ORDER[row.role], row.ordinal, row.path))
        used_paths.add(chosen.path)
        replacements.append({
            "role": failed.role,
            "ordinal": failed.ordinal,
            "removed": {
                **_source_identity(failed),
                "hc_capacity": audit_to_dict(hc_by_path[failed.path]),
            },
            "added": {
                **_source_identity(chosen_reserved),
                "candidate_sequence_ordinal": sequence_ordinal[chosen.path],
                "hc_capacity": audit_to_dict(hc_by_path[chosen.path]),
            },
            "replacement_attempts": attempts,
        })

    final_rows = tuple(sorted(current, key=lambda row: (ROLE_ORDER[row.role], row.ordinal, row.path)))
    final_invariants = _reservation_invariants(final_rows)
    final_hc_failures = [row for row in final_rows if not hc_by_path[row.path].passed]
    final_identity = [_source_identity(row) for row in final_rows]
    final_identity_sha256 = _canonical_json_sha256(final_identity)

    status = "PASS" if (
        not unfilled_failures
        and not final_hc_failures
        and final_invariants["pass"]
        and len(final_rows) == 120
    ) else "FAIL"

    return {
        "schema": SCHEMA,
        "stage": "7G-E3-S2-A-HC-CAPACITY",
        "status": status,
        "policy": {
            "rule_version": S2A_HC_CAPACITY_RULE_VERSION,
            "minimum_hc_eligible_events_per_source": S2A_HC_MIN_ELIGIBLE_EVENTS,
            "eligible_event_definition": "target-free chord, <=6 pitches, >=2 distinct S1-H-C assignments",
            "pass_scan_policy": "stop when minimum capacity is reached",
            "fail_scan_policy": "exhaust source before declaring insufficient capacity",
            "initial_reservation_selected_before_hc_results": True,
            "replacement_order": "ascending deterministic clean candidate sequence ordinal",
            "replacement_selection_uses_teacher_labels": False,
            "replacement_selection_uses_model_scores": False,
            "replacement_selection_uses_hc_capacity_only_after_initial_120_are_fixed": True,
            "candidate_variant_policy": "retain first structurally qualified deterministic variant per canonical work; H-C failure does not reopen variant choice",
            "pinned_dataset": "AnimeTAB",
            "pinned_commit": ANIMETAB_COMMIT,
            "tuning_midi": list(STANDARD_TUNING),
            "part_id": "P1",
            "staff_id": "2",
            "pitch_mode": "sounding_exact",
            "origin_alias_manifest_sha256": _canonical_json_sha256(alias_payload),
            "prior_final_semantic_quarantine_sha256": _canonical_json_sha256(semantic_payload),
        },
        "candidate_census": {
            "full_track_xml_blob_count": len(entries),
            "deterministic_fresh_work_group_count": len(groups),
            "structurally_qualified_clean_source_count": len(qualified),
            "structurally_qualified_clean_origin_family_count": len({row.origin_group_key for row in qualified}),
            "structural_rejected_reason_counts": dict(sorted(structural_rejections.items())),
            "source_isolation_rejected_reason_counts": dict(sorted(isolation_rejections.items())),
            "semantic_rejected_reason_counts": dict(sorted(semantic_rejections.items())),
            "replacement_pool_source_count": len(replacement_pool),
        },
        "candidate_sequence": [
            {
                **_qualified_identity(row, sequence_ordinal=index),
                "hc_capacity": audit_to_dict(hc_by_path[row.path]),
                "initially_reserved": row.path in initial_paths,
            }
            for index, row in enumerate(qualified, start=1)
        ],
        "initial_reservation": {
            "total_source_count": len(initial),
            "invariants": initial_invariants,
            "summary_by_role": initial_role_summary,
            "pass_source_count": len(initial) - len(initial_failures),
            "fail_source_count": len(initial_failures),
            "sources": initial_audits,
            "failures": [
                {
                    **_source_identity(row),
                    "hc_capacity": audit_to_dict(hc_by_path[row.path]),
                }
                for row in initial_failures
            ],
        },
        "replacement_execution": {
            "replacement_count": len(replacements),
            "unfilled_failure_count": len(unfilled_failures),
            "replacements": replacements,
            "unfilled_failures": unfilled_failures,
            "hc_failed_replacement_candidates": list(global_hc_rejected_candidates.values()),
        },
        "final_reservation": {
            "total_source_count": len(final_rows),
            "identity_sha256": final_identity_sha256,
            "invariants": final_invariants,
            "hc_pass_source_count": len(final_rows) - len(final_hc_failures),
            "hc_fail_source_count": len(final_hc_failures),
            "sources": [
                {
                    **_source_identity(row),
                    "hc_capacity": audit_to_dict(hc_by_path[row.path]),
                }
                for row in final_rows
            ],
        },
        "scientific_boundary": {
            "h_c_capacity_audit_executed": True,
            "all_initial_120_sources_audited": len(initial_audits) == 120,
            "teacher_task_identities_frozen": False,
            "new_teacher_labels_collected": False,
            "real_model_fit_executed": False,
            "untouched_final_labels_opened": False,
            "checkpoint_retained": False,
            "shadow_or_production_integration": False,
        },
        "next_gate": (
            "FREEZE_HC_QUALIFIED_SOURCE_RESERVATION_BEFORE_NEW_TEACHER_TASK_GENERATION"
            if status == "PASS"
            else "STOP_AND_REVIEW_HC_CAPACITY_FAILURES"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-teacher-manifest", type=Path, required=True)
    parser.add_argument("--origin-alias-manifest", type=Path, required=True)
    parser.add_argument("--quarantine-manifest", type=Path, action="append", default=[])
    parser.add_argument("--prior-final-semantic-quarantine", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_hc_capacity_audit(
        old_teacher_manifest=args.old_teacher_manifest,
        origin_alias_manifest=args.origin_alias_manifest,
        quarantine_manifests=tuple(args.quarantine_manifest),
        prior_final_semantic_quarantine=args.prior_final_semantic_quarantine,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    initial = payload["initial_reservation"]
    execution = payload["replacement_execution"]
    final = payload["final_reservation"]
    print(
        "S2-A H-C capacity audit " + payload["status"] + ": "
        f"initial_pass={initial['pass_source_count']}/120 "
        f"initial_fail={initial['fail_source_count']} "
        f"replacements={execution['replacement_count']} "
        f"unfilled={execution['unfilled_failure_count']} "
        f"final_pass={final['hc_pass_source_count']}/{final['total_source_count']} "
        f"identity={final['identity_sha256']}"
    )
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
