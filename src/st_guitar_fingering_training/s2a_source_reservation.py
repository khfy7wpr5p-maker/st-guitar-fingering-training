from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Iterable, Mapping

from .s2a_prior_final_semantics import (
    FROZEN_PRIOR_FINAL_SEMANTIC_KEYS,
    semantic_work_key,
)


ANIMETAB_FULL_TRACK_PREFIX = "AnimeTAB/Entire songs/"
PRIMARY_DEVELOPMENT_FAMILIES = 80
CONTINGENCY_DEVELOPMENT_FAMILIES = 20
UNTOUCHED_FINAL_FAMILIES = 20
TOTAL_RESERVED_FAMILIES = (
    PRIMARY_DEVELOPMENT_FAMILIES
    + CONTINGENCY_DEVELOPMENT_FAMILIES
    + UNTOUCHED_FINAL_FAMILIES
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_TRAILING_PARENS = re.compile(r"\s*\([^()]*\)\s*$")
_TRAILING_BY = re.compile(r"\s+by\s*.+$", re.IGNORECASE)
_TRAILING_VERSION = re.compile(
    r"(?:[\s._-]+(?:"
    r"tv[\s._-]*(?:side|size)|"
    r"short(?:[\s._-]*ver(?:sion)?)?|"
    r"full(?:[\s._-]*ver(?:sion)?)?|"
    r"ver(?:sion)?[\s._-]*[0-9a-z]+|"
    r"v[0-9]+|"
    r"[0-9]+"
    r"))+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnimeTabTreeEntry:
    path: str
    blob_sha: str
    size: int

    @property
    def filename(self) -> str:
        return PurePosixPath(self.path).name

    @property
    def canonical_work_key(self) -> str:
        return canonical_work_key(self.filename)


@dataclass(frozen=True)
class ReservedSource:
    role: str
    ordinal: int
    family_id: str
    canonical_work_key: str
    path: str
    blob_sha: str
    raw_sha256: str
    byte_size: int
    pitched_event_count: int
    chord_event_count: int


def canonical_work_key(filename: str) -> str:
    """Collapse obvious same-work arrangement/version filenames without labels.

    The key deliberately keeps the bracketed origin text as part of the work identity,
    but removes presentation/arranger suffixes that can create multiple files for the
    same musical work. It is only a leakage-control key; it is never a model feature.
    """

    name = PurePosixPath(filename).name
    text = unicodedata.normalize("NFKC", name).strip()
    if text.casefold().endswith(".xml"):
        text = text[:-4].rstrip()
    text = _TRAILING_BY.sub("", text).rstrip()
    while True:
        stripped = _TRAILING_PARENS.sub("", text).rstrip()
        if stripped == text:
            break
        text = stripped
    text = _TRAILING_VERSION.sub("", text).rstrip()
    key = "".join(ch for ch in text.casefold() if ch.isalnum())
    if not key:
        raise ValueError("canonical work key is empty")
    return key


def family_id_for_work_key(work_key: str) -> str:
    if not work_key:
        raise ValueError("work_key must be non-empty")
    return f"animetabs2a-{sha256(work_key.encode('utf-8')).hexdigest()[:20]}"


def source_rank(*, pinned_commit: str, work_key: str) -> str:
    return sha256(f"{pinned_commit}\0work\0{work_key}".encode("utf-8")).hexdigest()


def variant_rank(*, pinned_commit: str, entry: AnimeTabTreeEntry) -> str:
    payload = f"{pinned_commit}\0variant\0{entry.path}\0{entry.blob_sha}"
    return sha256(payload.encode("utf-8")).hexdigest()


def parse_full_track_tree_entries(
    tree_rows: Iterable[Mapping[str, object]],
) -> tuple[AnimeTabTreeEntry, ...]:
    entries: list[AnimeTabTreeEntry] = []
    seen_paths: set[str] = set()
    for row in tree_rows:
        path = row.get("path")
        kind = row.get("type")
        blob_sha = row.get("sha")
        size = row.get("size", 0)
        if not isinstance(path, str) or kind != "blob":
            continue
        if not path.startswith(ANIMETAB_FULL_TRACK_PREFIX) or not path.casefold().endswith(".xml"):
            continue
        if not isinstance(blob_sha, str) or _HEX40.fullmatch(blob_sha) is None:
            raise ValueError(f"invalid Git blob SHA for {path}")
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"invalid Git blob size for {path}")
        if path in seen_paths:
            raise ValueError(f"duplicate Git tree path: {path}")
        seen_paths.add(path)
        entries.append(AnimeTabTreeEntry(path=path, blob_sha=blob_sha, size=size))
    if not entries:
        raise ValueError("pinned AnimeTAB tree contains no full-track XML blobs")
    entries.sort(key=lambda item: item.path)
    return tuple(entries)


def exposed_work_keys_from_filenames(filenames: Iterable[str]) -> frozenset[str]:
    return frozenset(canonical_work_key(filename) for filename in filenames)


def fresh_work_groups(
    entries: Iterable[AnimeTabTreeEntry],
    *,
    pinned_commit: str,
    exposed_work_keys: Iterable[str],
) -> tuple[tuple[str, tuple[AnimeTabTreeEntry, ...]], ...]:
    """Return deterministic fresh work groups after all label-free quarantines.

    Prior untouched-final works are excluded by semantic title identity before any
    structural qualification or role assignment. This guard is in the core helper,
    not only in CI, so direct callers cannot re-admit a prior final work merely by
    changing its origin, encoding, arrangement container, or exact source bytes.
    """

    exposed = frozenset(exposed_work_keys)
    grouped: dict[str, list[AnimeTabTreeEntry]] = {}
    for entry in entries:
        key = entry.canonical_work_key
        if key in exposed:
            continue
        if semantic_work_key(entry.filename) in FROZEN_PRIOR_FINAL_SEMANTIC_KEYS:
            continue
        grouped.setdefault(key, []).append(entry)
    groups: list[tuple[str, tuple[AnimeTabTreeEntry, ...]]] = []
    for key, variants in grouped.items():
        ordered = tuple(sorted(variants, key=lambda item: variant_rank(pinned_commit=pinned_commit, entry=item)))
        groups.append((key, ordered))
    groups.sort(key=lambda item: (source_rank(pinned_commit=pinned_commit, work_key=item[0]), item[0]))
    return tuple(groups)


def assign_reservation_roles(
    qualified: Iterable[tuple[str, AnimeTabTreeEntry, str, int, int]],
) -> tuple[ReservedSource, ...]:
    """Assign predeclared 80/20/20 roles to already-qualified label-free sources.

    Input rows are `(work_key, entry, raw_sha256, pitched_events, chord_events)` and
    must already be in deterministic source-rank order.
    """

    rows = tuple(qualified)
    if len(rows) < TOTAL_RESERVED_FAMILIES:
        raise ValueError(
            f"fresh source reservation requires at least {TOTAL_RESERVED_FAMILIES} qualified works; "
            f"got {len(rows)}"
        )
    selected = rows[:TOTAL_RESERVED_FAMILIES]
    if len({row[0] for row in selected}) != TOTAL_RESERVED_FAMILIES:
        raise ValueError("reservation work keys must be unique")
    if len({row[1].path for row in selected}) != TOTAL_RESERVED_FAMILIES:
        raise ValueError("reservation source paths must be unique")

    reserved: list[ReservedSource] = []
    for index, (work_key, entry, raw_sha256, pitched_events, chord_events) in enumerate(selected):
        if index < PRIMARY_DEVELOPMENT_FAMILIES:
            role = "PRIMARY_DEVELOPMENT"
            ordinal = index + 1
        elif index < PRIMARY_DEVELOPMENT_FAMILIES + CONTINGENCY_DEVELOPMENT_FAMILIES:
            role = "CONTINGENCY_DEVELOPMENT"
            ordinal = index - PRIMARY_DEVELOPMENT_FAMILIES + 1
        else:
            role = "UNTOUCHED_FINAL"
            ordinal = index - PRIMARY_DEVELOPMENT_FAMILIES - CONTINGENCY_DEVELOPMENT_FAMILIES + 1
        reserved.append(
            ReservedSource(
                role=role,
                ordinal=ordinal,
                family_id=family_id_for_work_key(work_key),
                canonical_work_key=work_key,
                path=entry.path,
                blob_sha=entry.blob_sha,
                raw_sha256=raw_sha256,
                byte_size=entry.size,
                pitched_event_count=int(pitched_events),
                chord_event_count=int(chord_events),
            )
        )
    if len({item.family_id for item in reserved}) != TOTAL_RESERVED_FAMILIES:
        raise ValueError("derived family IDs must be unique")
    return tuple(reserved)
