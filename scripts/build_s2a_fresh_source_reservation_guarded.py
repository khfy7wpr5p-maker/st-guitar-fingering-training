from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from build_s2a_fresh_source_reservation import build_reservation
from st_guitar_fingering_training.s2a_prior_final_semantics import (
    load_prior_final_semantic_quarantine,
    reserved_semantic_overlaps,
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json_sha256(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def build_guarded_reservation(
    *,
    old_teacher_manifest: Path,
    origin_alias_manifest: Path,
    quarantine_manifests: tuple[Path, ...],
    prior_final_semantic_quarantine: Path,
    min_chord_events: int,
):
    semantic_payload = _load_json(prior_final_semantic_quarantine)
    semantic = load_prior_final_semantic_quarantine(semantic_payload)

    provenance = semantic_payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("prior-final semantic quarantine provenance is missing")
    stage7e = provenance.get("stage7e")
    stagee = provenance.get("stage7g_e3_e")
    if not isinstance(stage7e, dict) or not isinstance(stagee, dict):
        raise ValueError("prior-final semantic quarantine provenance stages are missing")
    if stage7e.get("corrected_semantic_family_count") != 8:
        raise ValueError("Stage 7E semantic family correction must remain frozen at 8")
    if stage7e.get("corrected_semantic_families_with_ambiguous_events") != 8:
        raise ValueError("Stage 7E ambiguous semantic family count must remain frozen at 8")
    if stage7e.get("corrected_sufficiency_gate_passed") is not True:
        raise ValueError("Stage 7E corrected sufficiency evidence is not closed")
    if stagee.get("semantic_family_count") != 32:
        raise ValueError("Stage 7G-E3-E semantic family count must remain frozen at 32")

    payload = build_reservation(
        old_teacher_manifest=old_teacher_manifest,
        origin_alias_manifest=origin_alias_manifest,
        quarantine_manifests=quarantine_manifests,
        min_chord_events=min_chord_events,
    )

    reservation = payload.get("reservation")
    if not isinstance(reservation, dict) or not isinstance(reservation.get("sources"), list):
        raise ValueError("base reservation payload has no source identities")
    source_paths = []
    for row in reservation["sources"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise ValueError("base reservation source identity is malformed")
        source_paths.append(row["path"])

    overlaps = reserved_semantic_overlaps(source_paths, quarantine=semantic)
    if overlaps:
        detail = "; ".join(f"{path} -> {family}" for path, _, family in overlaps[:8])
        raise ValueError(f"S2A_SRC_007_PRIOR_FINAL_SEMANTIC_OVERLAP: {detail}")

    payload["schema"] = "st-guitar-stage7g-e3-s2a-fresh-source-reservation-census-v3"
    payload["selection"]["prior_final_semantic_quarantine_enabled"] = True
    payload["selection"]["prior_final_semantic_quarantine_manifest_sha256"] = _canonical_json_sha256(
        semantic_payload
    )
    payload["selection"]["prior_final_semantic_overlap_policy"] = "REJECT_BEFORE_SCIENTIFIC_GATE"
    payload["census"]["prior_final_semantic_family_quarantine_count"] = semantic.family_count
    payload["census"]["prior_final_semantic_key_quarantine_count"] = semantic.semantic_key_count
    payload["reservation"]["prior_final_semantic_overlap_count"] = 0
    payload["scientific_boundary"]["prior_final_semantic_isolation_gate_passed"] = True
    payload["scientific_boundary"]["source_identity_isolation_gate_passed"] = True
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-teacher-manifest", type=Path, required=True)
    parser.add_argument("--origin-alias-manifest", type=Path, required=True)
    parser.add_argument("--quarantine-manifest", type=Path, action="append", default=[])
    parser.add_argument("--prior-final-semantic-quarantine", type=Path, required=True)
    parser.add_argument("--min-chord-events", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_guarded_reservation(
        old_teacher_manifest=args.old_teacher_manifest,
        origin_alias_manifest=args.origin_alias_manifest,
        quarantine_manifests=tuple(args.quarantine_manifest),
        prior_final_semantic_quarantine=args.prior_final_semantic_quarantine,
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
        "S2-A semantically guarded fresh source census PASS: "
        f"qualified_works={census['qualified_work_count']} "
        f"reserved_sources={reservation['total_source_count']} "
        f"prior_final_families={census['prior_final_semantic_family_quarantine_count']} "
        f"semantic_overlap={reservation['prior_final_semantic_overlap_count']} "
        f"identity={reservation['identity_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
