from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Iterable, Mapping


_LEADING_ORIGIN = re.compile(r"^\s*\[[^\]]+\]\s*")
_TRAILING_BY = re.compile(r"\s+by\s*.+$", re.IGNORECASE)
_TRAILING_PARENS = re.compile(r"\s*\([^()]*\)\s*$")
_TRAILING_PRESENTATION_VERSION = re.compile(
    r"(?:[\s._-]+(?:tv[\s._-]*(?:side|size)|short(?:[\s._-]*ver(?:sion)?)?|"
    r"full(?:[\s._-]*ver(?:sion)?)?|ver(?:sion)?[\s._-]*[0-9a-z]+|v[0-9]+))+$",
    re.IGNORECASE,
)
_KNOWN_EXTENSIONS = (".musicxml", ".xml", ".mxl", ".gp5", ".gp4", ".gp3", ".gp2", ".gp")


@dataclass(frozen=True)
class SemanticQuarantine:
    family_count: int
    semantic_key_count: int
    keys: frozenset[str]
    key_to_family: Mapping[str, str]


def semantic_work_key(value: str) -> str:
    """Normalize a work title independently of file encoding and AnimeTAB origin.

    This key is only a leakage-control identity. It is never exposed as a model feature.
    Leading ``[origin]`` text, common presentation suffixes, file extensions, spacing,
    punctuation, and Unicode compatibility variants are intentionally ignored. Bare
    trailing numbers are preserved because they can be musically meaningful work IDs.
    """

    name = PurePosixPath(str(value)).name
    text = unicodedata.normalize("NFKC", name).strip()
    text = _LEADING_ORIGIN.sub("", text, count=1).strip()
    folded = text.casefold()
    for extension in _KNOWN_EXTENSIONS:
        if folded.endswith(extension):
            text = text[: -len(extension)].rstrip()
            break
    text = _TRAILING_BY.sub("", text).rstrip()
    while True:
        stripped = _TRAILING_PARENS.sub("", text).rstrip()
        if stripped == text:
            break
        text = stripped
    text = _TRAILING_PRESENTATION_VERSION.sub("", text).rstrip()
    key = "".join(ch for ch in text.casefold() if ch.isalnum())
    if not key:
        raise ValueError("semantic work identity is empty or ambiguous")
    return key


def load_prior_final_semantic_quarantine(payload: Mapping[str, object]) -> SemanticQuarantine:
    if payload.get("schema") != "st-guitar-s2a-prior-final-semantic-quarantine-v1":
        raise ValueError("unexpected S2-A prior-final semantic quarantine schema")
    families = payload.get("families")
    expected = payload.get("expected_family_count")
    if not isinstance(families, list) or not families:
        raise ValueError("prior-final semantic quarantine requires families")
    if not isinstance(expected, int) or expected <= 0 or len(families) != expected:
        raise ValueError("prior-final semantic family count does not match frozen expectation")

    family_ids: set[str] = set()
    key_to_family: dict[str, str] = {}
    for row in families:
        if not isinstance(row, dict):
            raise ValueError("prior-final semantic family row is malformed")
        family_id = row.get("family_id")
        aliases = row.get("aliases")
        source_stage = row.get("source_stage")
        if not isinstance(family_id, str) or not family_id.strip() or family_id in family_ids:
            raise ValueError("prior-final semantic family_id is missing or duplicated")
        if not isinstance(source_stage, str) or not source_stage.strip():
            raise ValueError("prior-final semantic source_stage is missing")
        if not isinstance(aliases, list) or not aliases:
            raise ValueError("prior-final semantic family requires at least one alias")
        family_ids.add(family_id)
        row_keys = {semantic_work_key(str(alias)) for alias in aliases}
        if not row_keys:
            raise ValueError("prior-final semantic family resolved to no work keys")
        for key in row_keys:
            prior = key_to_family.get(key)
            if prior is not None and prior != family_id:
                raise ValueError("semantic work alias belongs to more than one protected family")
            key_to_family[key] = family_id

    return SemanticQuarantine(
        family_count=len(family_ids),
        semantic_key_count=len(key_to_family),
        keys=frozenset(key_to_family),
        key_to_family=dict(sorted(key_to_family.items())),
    )


def reserved_semantic_overlaps(
    source_paths: Iterable[str],
    *,
    quarantine: SemanticQuarantine,
) -> tuple[tuple[str, str, str], ...]:
    overlaps: list[tuple[str, str, str]] = []
    for path in source_paths:
        key = semantic_work_key(path)
        family = quarantine.key_to_family.get(key)
        if family is not None:
            overlaps.append((str(path), key, family))
    return tuple(sorted(overlaps))
