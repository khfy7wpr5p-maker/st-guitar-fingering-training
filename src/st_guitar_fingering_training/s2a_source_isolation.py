from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Iterable, Mapping


_LEADING_ORIGIN = re.compile(r"^\s*\[([^\]]+)\]")
PRIMARY_SOURCE_COUNT = 80
CONTINGENCY_SOURCE_COUNT = 20
UNTOUCHED_FINAL_SOURCE_COUNT = 20
MIN_PRIMARY_ORIGIN_FAMILIES = 40
CONTINGENCY_ORIGIN_FAMILIES = 20
UNTOUCHED_FINAL_ORIGIN_FAMILIES = 20


def canonical_origin_key(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    key = "".join(ch for ch in text if ch.isalnum())
    if not key:
        raise ValueError("origin identity is empty or ambiguous")
    return key


def origin_group_key(filename: str) -> str:
    """Extract the raw normalized bracketed origin identity from one filename."""

    name = PurePosixPath(filename).name
    match = _LEADING_ORIGIN.match(unicodedata.normalize("NFKC", name))
    if match is None:
        raise ValueError("source filename has no explicit bracketed origin identity")
    return canonical_origin_key(match.group(1))


def _normalized_alias_components(
    alias_groups: Iterable[Iterable[str]],
) -> tuple[frozenset[str], ...]:
    """Build transitive alias/franchise components deterministically."""

    components: list[set[str]] = []
    for raw_group in alias_groups:
        group = {canonical_origin_key(value) for value in raw_group}
        if len(group) < 2:
            raise ValueError("origin alias groups must contain at least two distinct aliases")
        overlapping = [component for component in components if component & group]
        merged = set(group)
        for component in overlapping:
            merged.update(component)
            components.remove(component)
        components.append(merged)
    return tuple(
        sorted(
            (frozenset(component) for component in components),
            key=lambda component: tuple(sorted(component)),
        )
    )


def build_origin_alias_index(alias_groups: Iterable[Iterable[str]]) -> dict[str, str]:
    """Map every known alias to one opaque canonical franchise/origin family key."""

    index: dict[str, str] = {}
    for component in _normalized_alias_components(alias_groups):
        digest = sha256("|".join(sorted(component)).encode("utf-8")).hexdigest()[:24]
        group_key = f"s2aalias{digest}"
        for alias in component:
            prior = index.get(alias)
            if prior is not None and prior != group_key:
                raise AssertionError("origin alias resolved to two franchise groups")
            index[alias] = group_key
    return index


def resolve_origin_key(origin_key: str, *, alias_groups: Iterable[Iterable[str]] = ()) -> str:
    raw = canonical_origin_key(origin_key)
    return build_origin_alias_index(alias_groups).get(raw, raw)


def resolved_origin_group_key(
    filename: str,
    *,
    alias_groups: Iterable[Iterable[str]] = (),
) -> str:
    return resolve_origin_key(origin_group_key(filename), alias_groups=alias_groups)


def exposed_origin_keys_from_filenames(
    filenames: Iterable[str],
    *,
    alias_groups: Iterable[Iterable[str]] = (),
) -> frozenset[str]:
    return frozenset(
        resolved_origin_group_key(filename, alias_groups=alias_groups)
        for filename in filenames
    )


def historical_origin_quarantine(
    *,
    exposed_origin_keys: Iterable[str],
    alias_groups: Iterable[Iterable[str]],
) -> frozenset[str]:
    """Resolve every historical raw origin to its canonical alias/franchise family."""

    return frozenset(
        resolve_origin_key(value, alias_groups=alias_groups)
        for value in exposed_origin_keys
    )


@dataclass(frozen=True)
class IsolationDecision:
    status: str
    reason: str
    origin_group_key: str | None

    @property
    def accepted(self) -> bool:
        return self.status == "ELIGIBLE"


def evaluate_source_isolation(
    filename: str,
    *,
    historical_quarantine: Iterable[str],
    already_reserved_origins: Iterable[str] = (),
    alias_groups: Iterable[Iterable[str]] = (),
) -> IsolationDecision:
    """Fail-closed source-isolation decision independent of Teacher labels/model scores."""

    try:
        origin = resolved_origin_group_key(filename, alias_groups=alias_groups)
    except ValueError:
        return IsolationDecision("REJECT", "S2A_SRC_005_IDENTITY_AMBIGUOUS", None)

    historical = {canonical_origin_key(value) for value in historical_quarantine}
    reserved = {canonical_origin_key(value) for value in already_reserved_origins}
    if origin in historical:
        return IsolationDecision("REJECT", "S2A_SRC_004_FRANCHISE_ORIGIN_OVERLAP", origin)
    if origin in reserved:
        return IsolationDecision("REJECT", "S2A_SRC_006_RESERVED_ORIGIN_REUSE", origin)
    return IsolationDecision("ELIGIBLE", "S2A_SRC_000_DISTINCT_ORIGIN", origin)


def load_alias_groups(payload: Mapping[str, object]) -> tuple[tuple[str, ...], ...]:
    if payload.get("schema") != "st-guitar-s2a-historical-origin-aliases-v1":
        raise ValueError("unexpected S2-A historical origin alias schema")
    raw_groups = payload.get("alias_groups")
    if not isinstance(raw_groups, list):
        raise ValueError("historical origin alias manifest requires alias_groups")
    groups: list[tuple[str, ...]] = []
    for row in raw_groups:
        if not isinstance(row, dict) or not isinstance(row.get("aliases"), list):
            raise ValueError("historical origin alias row is malformed")
        aliases = tuple(str(value) for value in row["aliases"])
        normalized = {canonical_origin_key(value) for value in aliases}
        if len(normalized) < 2:
            raise ValueError("historical origin alias row must contain two distinct normalized aliases")
        groups.append(aliases)
    # Validate transitive component construction now, before any source selection.
    build_origin_alias_index(groups)
    return tuple(groups)


@dataclass(frozen=True)
class QualifiedIsolatedSource:
    canonical_work_key: str
    origin_group_key: str
    path: str
    blob_sha: str
    raw_sha256: str
    byte_size: int
    pitched_event_count: int
    chord_event_count: int


@dataclass(frozen=True)
class ReservedIsolatedSource:
    role: str
    ordinal: int
    family_id: str
    canonical_work_key: str
    origin_group_key: str
    path: str
    blob_sha: str
    raw_sha256: str
    byte_size: int
    pitched_event_count: int
    chord_event_count: int


def origin_family_id(origin_key: str) -> str:
    key = canonical_origin_key(origin_key)
    return f"animetabs2a-origin-{sha256(key.encode('utf-8')).hexdigest()[:20]}"


def _origin_rank(*, pinned_commit: str, origin_key: str) -> str:
    payload = f"{pinned_commit}\0origin-role\0{canonical_origin_key(origin_key)}"
    return sha256(payload.encode("utf-8")).hexdigest()


def _source_rank(*, pinned_commit: str, row: QualifiedIsolatedSource) -> str:
    payload = (
        f"{pinned_commit}\0origin-source\0{row.origin_group_key}\0"
        f"{row.canonical_work_key}\0{row.path}\0{row.blob_sha}"
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def assign_origin_isolated_roles(
    rows: Iterable[QualifiedIsolatedSource],
    *,
    pinned_commit: str,
) -> tuple[ReservedIsolatedSource, ...]:
    """Assign 80/20/20 sources while keeping origin/franchise families isolated by role.

    Multiple works from one fresh origin may be used only inside PRIMARY_DEVELOPMENT.
    They share one family_id, so family-isolated CV cannot split one franchise across
    folds. CONTINGENCY_DEVELOPMENT and UNTOUCHED_FINAL each use exactly one source per
    origin family. Role assignment is label-free and deterministic from pinned source
    identity only.
    """

    source_rows = tuple(rows)
    if len({row.path for row in source_rows}) != len(source_rows):
        raise ValueError("qualified isolated sources contain duplicate paths")
    if len({row.canonical_work_key for row in source_rows}) != len(source_rows):
        raise ValueError("qualified isolated sources contain duplicate work keys")
    if len({row.raw_sha256 for row in source_rows}) != len(source_rows):
        raise ValueError("qualified isolated sources contain duplicate raw source hashes")

    grouped: dict[str, list[QualifiedIsolatedSource]] = {}
    for row in source_rows:
        origin = canonical_origin_key(row.origin_group_key)
        grouped.setdefault(origin, []).append(row)
    ordered_origins = sorted(
        grouped,
        key=lambda key: (_origin_rank(pinned_commit=pinned_commit, origin_key=key), key),
    )
    minimum_origins = (
        MIN_PRIMARY_ORIGIN_FAMILIES
        + CONTINGENCY_ORIGIN_FAMILIES
        + UNTOUCHED_FINAL_ORIGIN_FAMILIES
    )
    if len(ordered_origins) < minimum_origins:
        raise ValueError(
            f"origin-isolated reservation requires at least {minimum_origins} qualified origin families; "
            f"got {len(ordered_origins)}"
        )

    final_origins = tuple(ordered_origins[:UNTOUCHED_FINAL_ORIGIN_FAMILIES])
    contingency_origins = tuple(
        ordered_origins[
            UNTOUCHED_FINAL_ORIGIN_FAMILIES:
            UNTOUCHED_FINAL_ORIGIN_FAMILIES + CONTINGENCY_ORIGIN_FAMILIES
        ]
    )
    primary_candidates = tuple(
        ordered_origins[
            UNTOUCHED_FINAL_ORIGIN_FAMILIES + CONTINGENCY_ORIGIN_FAMILIES:
        ]
    )
    primary_origins = primary_candidates[:PRIMARY_SOURCE_COUNT]
    if len(primary_origins) < MIN_PRIMARY_ORIGIN_FAMILIES:
        raise ValueError("primary development origin-family minimum cannot be satisfied")

    ordered_by_origin = {
        origin: tuple(
            sorted(
                grouped[origin],
                key=lambda row: (_source_rank(pinned_commit=pinned_commit, row=row), row.path),
            )
        )
        for origin in ordered_origins
    }

    selected: list[tuple[str, QualifiedIsolatedSource]] = []
    for origin in final_origins:
        selected.append(("UNTOUCHED_FINAL", ordered_by_origin[origin][0]))
    for origin in contingency_origins:
        selected.append(("CONTINGENCY_DEVELOPMENT", ordered_by_origin[origin][0]))

    primary_rows: list[QualifiedIsolatedSource] = [ordered_by_origin[origin][0] for origin in primary_origins]
    next_index = {origin: 1 for origin in primary_origins}
    while len(primary_rows) < PRIMARY_SOURCE_COUNT:
        made_progress = False
        for origin in primary_origins:
            index = next_index[origin]
            candidates = ordered_by_origin[origin]
            if index >= len(candidates):
                continue
            primary_rows.append(candidates[index])
            next_index[origin] = index + 1
            made_progress = True
            if len(primary_rows) >= PRIMARY_SOURCE_COUNT:
                break
        if not made_progress:
            raise ValueError(
                f"primary development needs {PRIMARY_SOURCE_COUNT} isolated sources; "
                f"only {len(primary_rows)} available inside its predeclared origin families"
            )
    selected.extend(("PRIMARY_DEVELOPMENT", row) for row in primary_rows)

    role_order = {
        "PRIMARY_DEVELOPMENT": 0,
        "CONTINGENCY_DEVELOPMENT": 1,
        "UNTOUCHED_FINAL": 2,
    }
    selected.sort(
        key=lambda item: (
            role_order[item[0]],
            _source_rank(pinned_commit=pinned_commit, row=item[1]),
            item[1].path,
        )
    )
    ordinals = {role: 0 for role in role_order}
    reserved: list[ReservedIsolatedSource] = []
    for role, row in selected:
        ordinals[role] += 1
        reserved.append(
            ReservedIsolatedSource(
                role=role,
                ordinal=ordinals[role],
                family_id=origin_family_id(row.origin_group_key),
                canonical_work_key=row.canonical_work_key,
                origin_group_key=canonical_origin_key(row.origin_group_key),
                path=row.path,
                blob_sha=row.blob_sha,
                raw_sha256=row.raw_sha256,
                byte_size=int(row.byte_size),
                pitched_event_count=int(row.pitched_event_count),
                chord_event_count=int(row.chord_event_count),
            )
        )

    role_counts = {role: sum(row.role == role for row in reserved) for role in role_order}
    if role_counts != {
        "PRIMARY_DEVELOPMENT": PRIMARY_SOURCE_COUNT,
        "CONTINGENCY_DEVELOPMENT": CONTINGENCY_SOURCE_COUNT,
        "UNTOUCHED_FINAL": UNTOUCHED_FINAL_SOURCE_COUNT,
    }:
        raise AssertionError("origin-isolated source role counts do not match 80/20/20")

    origins_by_role = {
        role: {row.origin_group_key for row in reserved if row.role == role}
        for role in role_order
    }
    if any(
        origins_by_role[left] & origins_by_role[right]
        for left, right in (
            ("PRIMARY_DEVELOPMENT", "CONTINGENCY_DEVELOPMENT"),
            ("PRIMARY_DEVELOPMENT", "UNTOUCHED_FINAL"),
            ("CONTINGENCY_DEVELOPMENT", "UNTOUCHED_FINAL"),
        )
    ):
        raise AssertionError("origin family leaked across reservation roles")
    if len(origins_by_role["PRIMARY_DEVELOPMENT"]) < MIN_PRIMARY_ORIGIN_FAMILIES:
        raise AssertionError("primary development family count below frozen minimum")
    if len(origins_by_role["CONTINGENCY_DEVELOPMENT"]) != CONTINGENCY_ORIGIN_FAMILIES:
        raise AssertionError("contingency development must use 20 independent origin families")
    if len(origins_by_role["UNTOUCHED_FINAL"]) != UNTOUCHED_FINAL_ORIGIN_FAMILIES:
        raise AssertionError("untouched final must use 20 independent origin families")
    return tuple(reserved)
