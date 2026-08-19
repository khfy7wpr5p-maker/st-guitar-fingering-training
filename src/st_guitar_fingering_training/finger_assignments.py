from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
import json
from typing import Iterable

from .dataset import Voicing
from .fingering_feasibility import (
    S1HB_RULE_VERSION,
    analyze_standard_fingering_feasibility,
)


S1HC_RULE_VERSION = "S1-H-C.v1"


@dataclass(frozen=True)
class StandardFingering:
    assignment_id: str
    placements: tuple[tuple[int, int, int, int], ...]
    barres: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True)
class CandidateFingerings:
    candidate_id: str
    candidate: Voicing
    upstream_classification: str
    assignments: tuple[StandardFingering, ...]


@dataclass(frozen=True)
class StandardFingeringGenerationResult:
    rule_version: str
    upstream_rule_version: str
    raw_candidates: tuple[Voicing, ...]
    retained_candidates: tuple[Voicing, ...]
    candidates: tuple[CandidateFingerings, ...]
    total_assignment_count: int


def _assignment_id(
    placements: tuple[tuple[int, int, int, int], ...],
    barres: tuple[tuple[int, int, int, int], ...],
) -> str:
    payload = json.dumps(
        {"placements": placements, "barres": barres},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return f"fingering-sha256:{sha256(payload).hexdigest()}"


def _strict_fret_order_ok(groups, fingers: tuple[int, ...]) -> bool:
    for left_index, left in enumerate(groups):
        for right_index, right in enumerate(groups):
            if left.fret < right.fret and not fingers[left_index] < fingers[right_index]:
                return False
    return True


def _build_assignment(candidate: Voicing, groups, fingers: tuple[int, ...]) -> StandardFingering:
    finger_by_fret_string: dict[tuple[int, int], int] = {}
    barres: list[tuple[int, int, int, int]] = []

    for group, finger in zip(groups, fingers):
        for string in group.strings:
            key = (group.fret, string)
            if key in finger_by_fret_string:
                raise AssertionError("S1-H-C group mapping overlaps the same fret/string target")
            finger_by_fret_string[key] = finger
        if group.span_end_string > group.span_start_string:
            barres.append((
                finger,
                group.fret,
                group.span_start_string,
                group.span_end_string,
            ))

    placements: list[tuple[int, int, int, int]] = []
    for pitch, string, fret in candidate:
        if fret == 0:
            finger = 0
        else:
            key = (fret, string)
            if key not in finger_by_fret_string:
                raise AssertionError("S1-H-C fretted note is not covered by an S1-H-B group")
            finger = finger_by_fret_string[key]
        placements.append((pitch, string, fret, finger))

    frozen_placements = tuple(sorted(placements))
    frozen_barres = tuple(sorted(barres))
    return StandardFingering(
        assignment_id=_assignment_id(frozen_placements, frozen_barres),
        placements=frozen_placements,
        barres=frozen_barres,
    )


def _enumerate_candidate_assignments(candidate: Voicing, facts) -> tuple[StandardFingering, ...]:
    groups = facts.groups
    group_count = len(groups)
    if group_count != facts.minimum_standard_fingers:
        raise AssertionError("S1-H-C upstream group count/minimum-finger mismatch")
    if group_count > 4:
        raise AssertionError("S1-H-C received an S1-H-B-retained candidate requiring >4 fingers")

    if group_count == 0:
        assignment = _build_assignment(candidate, groups, ())
        return (assignment,)

    generated: dict[str, StandardFingering] = {}
    for fingers in permutations((1, 2, 3, 4), group_count):
        if not _strict_fret_order_ok(groups, fingers):
            continue
        assignment = _build_assignment(candidate, groups, fingers)
        existing = generated.get(assignment.assignment_id)
        if existing is not None and existing != assignment:
            raise AssertionError("S1-H-C assignment ID collision")
        generated[assignment.assignment_id] = assignment

    assignments = tuple(sorted(generated.values(), key=lambda item: item.assignment_id))
    if not assignments:
        raise AssertionError("S1-H-C retained voicing produced zero standard finger assignments")
    if len({item.assignment_id for item in assignments}) != len(assignments):
        raise AssertionError("S1-H-C duplicate assignment IDs")
    return assignments


def generate_standard_fingerings(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
) -> StandardFingeringGenerationResult:
    """Enumerate every standard four-finger assignment for S1-H-B-retained voicings."""

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    upstream = analyze_standard_fingering_feasibility(pitches, tuning)
    if upstream.rule_version != S1HB_RULE_VERSION:
        raise RuntimeError(
            f"S1-H-C requires upstream rule version {S1HB_RULE_VERSION}, "
            f"got {upstream.rule_version}"
        )

    retained = set(upstream.retained_candidates)
    candidates: list[CandidateFingerings] = []
    total_assignment_count = 0

    for item in upstream.assessments:
        if item.candidate not in retained:
            candidates.append(CandidateFingerings(
                candidate_id=item.candidate_id,
                candidate=item.candidate,
                upstream_classification=item.classification,
                assignments=(),
            ))
            continue

        if item.pruned or item.classification != "RESOURCE_FEASIBLE" or item.facts is None:
            raise AssertionError("S1-H-C retained candidate has inconsistent S1-H-B state")

        assignments = _enumerate_candidate_assignments(item.candidate, item.facts)
        total_assignment_count += len(assignments)
        candidates.append(CandidateFingerings(
            candidate_id=item.candidate_id,
            candidate=item.candidate,
            upstream_classification=item.classification,
            assignments=assignments,
        ))

    if len(candidates) != len(upstream.raw_candidates):
        raise AssertionError("S1-H-C audit does not cover the complete S1-H-B raw set")

    for item in candidates:
        if item.candidate in retained and not item.assignments:
            raise AssertionError("S1-H-C retained candidate is missing assignments")
        if item.candidate not in retained and item.assignments:
            raise AssertionError("S1-H-C generated assignments for an upstream-pruned candidate")
        for assignment in item.assignments:
            original = tuple(sorted((pitch, string, fret) for pitch, string, fret, _ in assignment.placements))
            if original != item.candidate:
                raise AssertionError("S1-H-C assignment changed pitch/string/fret placement")
            for _, _, fret, finger in assignment.placements:
                if fret == 0 and finger != 0:
                    raise AssertionError("S1-H-C open string must use finger 0")
                if fret > 0 and finger not in (1, 2, 3, 4):
                    raise AssertionError("S1-H-C fretted note finger outside 1..4")

    return StandardFingeringGenerationResult(
        rule_version=S1HC_RULE_VERSION,
        upstream_rule_version=upstream.rule_version,
        raw_candidates=upstream.raw_candidates,
        retained_candidates=upstream.retained_candidates,
        candidates=tuple(candidates),
        total_assignment_count=total_assignment_count,
    )
