from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Iterable, Mapping


_LEADING_ORIGIN = re.compile(r"^\s*\[([^\]]+)\]")


def canonical_origin_key(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    key = "".join(ch for ch in text if ch.isalnum())
    if not key:
        raise ValueError("origin identity is empty or ambiguous")
    return key


def origin_group_key(filename: str) -> str:
    name = PurePosixPath(filename).name
    match = _LEADING_ORIGIN.match(unicodedata.normalize("NFKC", name))
    if match is None:
        raise ValueError("source filename has no explicit bracketed origin identity")
    return canonical_origin_key(match.group(1))


def exposed_origin_keys_from_filenames(filenames: Iterable[str]) -> frozenset[str]:
    return frozenset(origin_group_key(filename) for filename in filenames)


def historical_origin_quarantine(
    *,
    exposed_origin_keys: Iterable[str],
    alias_groups: Iterable[Iterable[str]],
) -> frozenset[str]:
    """Return the complete deterministic quarantine closure for historical origins.

    Alias groups are label-free metadata. If any normalized alias in one group touches
    a Teacher-exposed origin, every alias in that group becomes quarantined. Unknown
    or malformed aliases fail closed instead of being silently ignored.
    """

    exposed = {canonical_origin_key(value) for value in exposed_origin_keys}
    quarantine = set(exposed)
    normalized_groups: list[set[str]] = []
    for raw_group in alias_groups:
        group = {canonical_origin_key(value) for value in raw_group}
        if len(group) < 2:
            raise ValueError("origin alias groups must contain at least two distinct aliases")
        normalized_groups.append(group)

    changed = True
    while changed:
        changed = False
        for group in normalized_groups:
            if group & quarantine and not group <= quarantine:
                quarantine.update(group)
                changed = True
    return frozenset(quarantine)


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
) -> IsolationDecision:
    """Fail-closed source-isolation decision independent of Teacher labels/model scores."""

    try:
        origin = origin_group_key(filename)
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
    return tuple(groups)
