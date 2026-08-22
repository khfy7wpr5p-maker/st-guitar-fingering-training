from __future__ import annotations

from functools import lru_cache
from itertools import permutations, product
from typing import Iterable

from .dataset import Voicing
from .finger_assignments import (
    CandidateFingerings,
    StandardFingering,
    StandardFingeringGenerationResult,
    _assignment_id,
)
from .fingering_feasibility import (
    FrettingGroup,
    S1HB_RULE_VERSION,
    analyze_standard_fingering_feasibility,
)


S1HC_V2_RULE_VERSION = "S1-H-C.v2"


def _strict_fret_order_ok(groups: tuple[FrettingGroup, ...], fingers: tuple[int, ...]) -> bool:
    for left_index, left in enumerate(groups):
        for right_index, right in enumerate(groups):
            if left.fret < right.fret and not fingers[left_index] < fingers[right_index]:
                return False
    return True


def _partition_group(group: FrettingGroup) -> tuple[tuple[FrettingGroup, ...], ...]:
    """Enumerate contiguous partitions of one passable H-B lower-bound group."""
    strings = tuple(group.strings)
    if not strings:
        raise AssertionError("S1-H-C.v2 received an empty H-B group")
    if len(strings) == 1:
        return ((group,),)
    out: list[tuple[FrettingGroup, ...]] = []
    for mask in range(1 << (len(strings) - 1)):
        chunks: list[list[int]] = [[strings[0]]]
        for index, string in enumerate(strings[1:]):
            if mask & (1 << index):
                chunks.append([string])
            else:
                chunks[-1].append(string)
        out.append(tuple(
            FrettingGroup(
                fret=group.fret,
                strings=tuple(chunk),
                span_start_string=chunk[0],
                span_end_string=chunk[-1],
            )
            for chunk in chunks
        ))
    return tuple(out)


def _expanded_groupings(base_groups: tuple[FrettingGroup, ...]) -> tuple[tuple[FrettingGroup, ...], ...]:
    if not base_groups:
        return ((),)
    options = tuple(_partition_group(group) for group in base_groups)
    generated: set[tuple[FrettingGroup, ...]] = set()
    for choice in product(*options):
        flat = tuple(group for partition in choice for group in partition)
        if len(flat) <= 4:
            generated.add(flat)
    return tuple(sorted(
        generated,
        key=lambda groups: tuple(
            (group.fret, group.span_start_string, group.span_end_string, group.strings)
            for group in groups
        ),
    ))


def _build_assignment(
    candidate: Voicing,
    groups: tuple[FrettingGroup, ...],
    fingers: tuple[int, ...],
) -> StandardFingering:
    finger_by_fret_string: dict[tuple[int, int], int] = {}
    barres: list[tuple[int, int, int, int]] = []
    for group, finger in zip(groups, fingers):
        for string in group.strings:
            key = (group.fret, string)
            if key in finger_by_fret_string:
                raise AssertionError("S1-H-C.v2 grouping overlaps one fret/string target")
            finger_by_fret_string[key] = finger
        if len(group.strings) > 1:
            barres.append((finger, group.fret, group.span_start_string, group.span_end_string))
    placements: list[tuple[int, int, int, int]] = []
    for pitch, string, fret in candidate:
        if fret == 0:
            finger = 0
        else:
            finger = finger_by_fret_string.get((fret, string))
            if finger is None:
                raise AssertionError("S1-H-C.v2 fretted note is not covered")
        placements.append((pitch, string, fret, finger))
    frozen_placements = tuple(sorted(placements))
    frozen_barres = tuple(sorted(barres))
    return StandardFingering(
        assignment_id=_assignment_id(frozen_placements, frozen_barres),
        placements=frozen_placements,
        barres=frozen_barres,
    )


def _enumerate_candidate_assignments(candidate: Voicing, facts) -> tuple[StandardFingering, ...]:
    base_groups = tuple(facts.groups)
    if len(base_groups) != facts.minimum_standard_fingers:
        raise AssertionError("S1-H-C.v2 H-B lower-bound mismatch")
    if len(base_groups) > 4:
        raise AssertionError("S1-H-C.v2 received H-B-retained candidate requiring >4 fingers")
    generated: dict[str, StandardFingering] = {}
    for groups in _expanded_groupings(base_groups):
        group_count = len(groups)
        if group_count == 0:
            assignment = _build_assignment(candidate, groups, ())
            generated[assignment.assignment_id] = assignment
            continue
        for fingers in permutations((1, 2, 3, 4), group_count):
            if not _strict_fret_order_ok(groups, fingers):
                continue
            assignment = _build_assignment(candidate, groups, fingers)
            existing = generated.get(assignment.assignment_id)
            if existing is not None and existing != assignment:
                raise AssertionError("S1-H-C.v2 assignment ID collision")
            generated[assignment.assignment_id] = assignment
    assignments = tuple(sorted(generated.values(), key=lambda item: item.assignment_id))
    if not assignments:
        raise AssertionError("S1-H-C.v2 retained voicing produced zero assignments")
    return assignments


@lru_cache(maxsize=4096)
def _generate_standard_fingerings_v2_cached(
    pitches: tuple[int, ...],
    tuning: tuple[int, ...],
) -> StandardFingeringGenerationResult:
    upstream = analyze_standard_fingering_feasibility(pitches, tuning)
    if upstream.rule_version != S1HB_RULE_VERSION:
        raise RuntimeError(
            f"S1-H-C.v2 requires upstream rule version {S1HB_RULE_VERSION}, got {upstream.rule_version}"
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
            raise AssertionError("S1-H-C.v2 retained candidate has inconsistent H-B state")
        assignments = _enumerate_candidate_assignments(item.candidate, item.facts)
        total_assignment_count += len(assignments)
        candidates.append(CandidateFingerings(
            candidate_id=item.candidate_id,
            candidate=item.candidate,
            upstream_classification=item.classification,
            assignments=assignments,
        ))
    if len(candidates) != len(upstream.raw_candidates):
        raise AssertionError("S1-H-C.v2 audit does not cover complete H-B raw set")
    for item in candidates:
        if item.candidate in retained and not item.assignments:
            raise AssertionError("S1-H-C.v2 retained candidate missing assignments")
        for assignment in item.assignments:
            restored = tuple(sorted((pitch, string, fret) for pitch, string, fret, _ in assignment.placements))
            if restored != item.candidate:
                raise AssertionError("S1-H-C.v2 changed pitch/string/fret placement")
            for _, _, fret, finger in assignment.placements:
                if fret == 0 and finger != 0:
                    raise AssertionError("S1-H-C.v2 open string must use finger 0")
                if fret > 0 and finger not in (1, 2, 3, 4):
                    raise AssertionError("S1-H-C.v2 fretted finger outside 1..4")
    return StandardFingeringGenerationResult(
        rule_version=S1HC_V2_RULE_VERSION,
        upstream_rule_version=upstream.rule_version,
        raw_candidates=upstream.raw_candidates,
        retained_candidates=upstream.retained_candidates,
        candidates=tuple(candidates),
        total_assignment_count=total_assignment_count,
    )


def generate_standard_fingerings_v2(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
) -> StandardFingeringGenerationResult:
    """Enumerate H-C.v2 assignments with deterministic pitch-set memoization."""
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    frozen_tuning = tuple(int(value) for value in tuning)
    return _generate_standard_fingerings_v2_cached(pitches, frozen_tuning)
