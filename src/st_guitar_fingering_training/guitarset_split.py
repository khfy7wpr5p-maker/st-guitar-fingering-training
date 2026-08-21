from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath
import re
from typing import Iterable

GUITARSET_SPLIT_VERSION = "GUITARSET-SPLIT.v1"
ROLE_DEVELOPMENT = "DEVELOPMENT"
ROLE_VALIDATION = "VALIDATION"
ROLE_UNTOUCHED_FINAL = "UNTOUCHED_FINAL"
PURPOSE_FIT = "FIT"
PURPOSE_DEV_CV = "DEV_CV"
PURPOSE_VALIDATION_EVAL = "VALIDATION_EVAL"
PURPOSE_FINAL_EVAL = "FINAL_EVAL"

_EXPECTED_PERFORMERS = ("00", "01", "02", "03", "04", "05")
_EXPECTED_RECORDINGS_PER_PERFORMER = 30
_EXPECTED_TRACK_COUNT = 30
_EXPECTED_STYLE_COUNT = 15
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_comp_member_identity(source_member: str) -> tuple[str, str, str]:
    path = PurePosixPath(source_member)
    if path.parent.as_posix() != "annotation" or not path.name.endswith("_comp.jams"):
        raise ValueError("expected annotation/*_comp.jams member")
    stem = path.name[: -len("_comp.jams")]
    if "_" not in stem:
        raise ValueError("recording name is missing performer separator")
    performer, track_key = stem.split("_", 1)
    if not re.fullmatch(r"\d{2}", performer):
        raise ValueError("performer id must be exactly two digits")
    if not track_key or "-" not in track_key:
        raise ValueError("recording is missing track/style identity")
    style_key = track_key.split("-", 1)[0]
    if not style_key:
        raise ValueError("empty style key")
    return performer, track_key, style_key


def _performer_rank(performer: str, source_archive_sha256: str) -> str:
    payload = f"{GUITARSET_SPLIT_VERSION}|{source_archive_sha256}|{performer}".encode("ascii")
    return sha256(payload).hexdigest()


def frozen_performer_roles(
    performers: Iterable[str], *, source_archive_sha256: str
) -> dict[str, tuple[str, ...]]:
    performers = tuple(sorted(set(performers)))
    if performers != _EXPECTED_PERFORMERS:
        raise ValueError(f"performer identity drift: expected {_EXPECTED_PERFORMERS}, got {performers}")
    if not _SHA256_RE.fullmatch(source_archive_sha256):
        raise ValueError("source archive SHA-256 must be lowercase hexadecimal")
    ranked = tuple(sorted(performers, key=lambda p: (_performer_rank(p, source_archive_sha256), p)))
    return {
        ROLE_UNTOUCHED_FINAL: (ranked[0],),
        ROLE_VALIDATION: (ranked[1],),
        ROLE_DEVELOPMENT: tuple(sorted(ranked[2:])),
    }


def build_split_contract(
    source_members: Iterable[str], *, source_archive_sha256: str
) -> dict:
    members = tuple(sorted(source_members))
    if len(members) != len(set(members)):
        raise ValueError("duplicate recording member")
    identities = [parse_comp_member_identity(member) for member in members]
    by_performer: dict[str, list[tuple[str, str]]] = {}
    for performer, track_key, style_key in identities:
        by_performer.setdefault(performer, []).append((track_key, style_key))
    if tuple(sorted(by_performer)) != _EXPECTED_PERFORMERS:
        raise ValueError("performer identity drift")
    for performer, rows in by_performer.items():
        if len(rows) != _EXPECTED_RECORDINGS_PER_PERFORMER:
            raise ValueError(f"performer {performer} does not have exactly 30 recordings")
        if len({track for track, _ in rows}) != len(rows):
            raise ValueError(f"performer {performer} repeats a track identity")

    track_sets = {p: {track for track, _ in rows} for p, rows in by_performer.items()}
    style_sets = {p: {style for _, style in rows} for p, rows in by_performer.items()}
    first_performer = _EXPECTED_PERFORMERS[0]
    canonical_tracks = track_sets[first_performer]
    canonical_styles = style_sets[first_performer]
    if len(canonical_tracks) != _EXPECTED_TRACK_COUNT:
        raise ValueError("expected exactly 30 backing-track identities")
    if len(canonical_styles) != _EXPECTED_STYLE_COUNT:
        raise ValueError("expected exactly 15 style identities")
    if any(tracks != canonical_tracks for tracks in track_sets.values()):
        raise ValueError("performers do not share one exact 30-track repertoire")
    if any(styles != canonical_styles for styles in style_sets.values()):
        raise ValueError("performers do not share one exact 15-style set")

    roles = frozen_performer_roles(by_performer, source_archive_sha256=source_archive_sha256)
    role_by_performer = {
        performer: role
        for role, performers in roles.items()
        for performer in performers
    }
    role_members = {
        role: tuple(
            member
            for member in members
            if role_by_performer[parse_comp_member_identity(member)[0]] == role
        )
        for role in (ROLE_DEVELOPMENT, ROLE_VALIDATION, ROLE_UNTOUCHED_FINAL)
    }
    all_role_members = [member for values in role_members.values() for member in values]
    if len(all_role_members) != len(set(all_role_members)) or set(all_role_members) != set(members):
        raise AssertionError("recording roles are not an exact disjoint partition")

    role_tracks = {
        role: {parse_comp_member_identity(member)[1] for member in values}
        for role, values in role_members.items()
    }
    role_styles = {
        role: {parse_comp_member_identity(member)[2] for member in values}
        for role, values in role_members.items()
    }
    shared_tracks = set.intersection(*(set(v) for v in role_tracks.values()))
    shared_styles = set.intersection(*(set(v) for v in role_styles.values()))
    if shared_tracks != canonical_tracks or shared_styles != canonical_styles:
        raise AssertionError("expected repertoire/style matching across performer-isolated roles")

    return {
        "schema": "st-guitar-guitarset-split-contract-v1",
        "version": GUITARSET_SPLIT_VERSION,
        "source_archive_sha256": source_archive_sha256,
        "benchmark_target": "UNSEEN_PERFORMER_SEEN_REPERTOIRE",
        "performer_roles": {role: list(values) for role, values in roles.items()},
        "recording_counts": {role: len(values) for role, values in role_members.items()},
        "performer_overlap_across_roles": 0,
        "recording_overlap_across_roles": 0,
        "shared_track_identity_count_across_roles": len(shared_tracks),
        "shared_style_identity_count_across_roles": len(shared_styles),
        "track_overlap_policy": "INTENTIONAL_COVARIATE_MATCHING_NOT_UNSEEN_REPERTOIRE",
        "style_overlap_policy": "INTENTIONAL_COVARIATE_MATCHING_NOT_UNSEEN_STYLE",
        "development_cv": "LEAVE_ONE_DEVELOPMENT_PERFORMER_OUT_4_FOLDS",
        "fit_roles": [ROLE_DEVELOPMENT],
        "model_selection_roles": [ROLE_VALIDATION],
        "final_evaluation_roles": [ROLE_UNTOUCHED_FINAL],
        "training_authorized": False,
        "final_access_authorized": False,
    }


def source_role(source_member: str, contract: dict) -> str:
    performer, _, _ = parse_comp_member_identity(source_member)
    matches = [
        role
        for role, performers in contract["performer_roles"].items()
        if performer in performers
    ]
    if len(matches) != 1:
        raise ValueError("source performer does not map to exactly one frozen role")
    return matches[0]


def assert_role_use(role: str, purpose: str) -> None:
    allowed = {
        PURPOSE_FIT: {ROLE_DEVELOPMENT},
        PURPOSE_DEV_CV: {ROLE_DEVELOPMENT},
        PURPOSE_VALIDATION_EVAL: {ROLE_VALIDATION},
        PURPOSE_FINAL_EVAL: {ROLE_UNTOUCHED_FINAL},
    }
    if purpose not in allowed or role not in allowed[purpose]:
        raise ValueError(f"role {role!r} is not authorized for purpose {purpose!r}")
