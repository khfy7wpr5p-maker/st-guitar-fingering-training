from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dataset import Voicing
from .guitaristic_plausibility import (
    S1H_RULE_VERSION,
    analyze_valid_chord_voicings,
)


S1HB_RULE_VERSION = "S1-H-B.v1"
S1HB_OK = "OK"
S1HB_NO_STANDARD_FINGERING_CANDIDATE = "NO_STANDARD_FINGERING_CANDIDATE"

U100_UPSTREAM_S1H_A_PRUNED = "U100_UPSTREAM_S1H_A_PRUNED"
H101_MIN_STANDARD_FINGERS_GE_5 = "H101_MIN_STANDARD_FINGERS_GE_5"

S1HB_REASON_PRIORITY = (
    U100_UPSTREAM_S1H_A_PRUNED,
    H101_MIN_STANDARD_FINGERS_GE_5,
)


@dataclass(frozen=True)
class FrettingGroup:
    fret: int
    strings: tuple[int, ...]
    span_start_string: int
    span_end_string: int


@dataclass(frozen=True)
class FrettingResourceFacts:
    positive_frets: tuple[int, ...]
    groups: tuple[FrettingGroup, ...]
    blockers_by_fret: tuple[tuple[int, tuple[int, ...]], ...]
    minimum_standard_fingers: int
    canonical_assignment: tuple[tuple[int, int, tuple[int, ...]], ...]


@dataclass(frozen=True)
class FingeringResourceAssessment:
    candidate_id: str
    candidate: Voicing
    upstream_classification: str
    classification: str
    pruned: bool
    reason_codes: tuple[str, ...]
    facts: FrettingResourceFacts | None


@dataclass(frozen=True)
class FingeringFeasibilityResult:
    rule_version: str
    upstream_rule_version: str
    status: str
    raw_candidates: tuple[Voicing, ...]
    upstream_retained_candidates: tuple[Voicing, ...]
    retained_candidates: tuple[Voicing, ...]
    assessments: tuple[FingeringResourceAssessment, ...]


def _ordered_reason_codes(codes: Iterable[str]) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(codes))
    unknown = set(values) - set(S1HB_REASON_PRIORITY)
    if unknown:
        raise AssertionError(f"unknown S1-H-B reason code(s): {sorted(unknown)}")
    return tuple(code for code in S1HB_REASON_PRIORITY if code in values)


def _string_fret_map(candidate: Voicing) -> dict[int, int]:
    by_string: dict[int, int] = {}
    for _, string, fret in candidate:
        string = int(string)
        fret = int(fret)
        if not 1 <= string <= 6:
            raise ValueError("S1-H-B supports six-string guitar candidates only")
        if string in by_string:
            raise ValueError("candidate uses the same string more than once")
        by_string[string] = fret
    return by_string


def _blocking_strings_between(
    string_frets: dict[int, int],
    fret: int,
    left_string: int,
    right_string: int,
) -> tuple[int, ...]:
    """Return strings that prevent one continuous barre between two targets.

    An unused string is passable. A string at the same or a higher fret is also
    passable because the same barre may cover it or a higher-fret finger may
    override the underlying barre. A required open string or a required lower
    positive fret is blocking.
    """

    lo, hi = sorted((int(left_string), int(right_string)))
    blockers: list[int] = []
    for string in range(lo + 1, hi):
        required_fret = string_frets.get(string)
        if required_fret is None:
            continue
        if required_fret == 0 or 0 < required_fret < fret:
            blockers.append(string)
    return tuple(blockers)


def _groups_for_fret(
    candidate: Voicing,
    fret: int,
    string_frets: dict[int, int],
) -> tuple[tuple[FrettingGroup, ...], tuple[int, ...]]:
    targets = tuple(sorted(string for _, string, value in candidate if value == fret))
    if not targets:
        return (), ()

    groups: list[list[int]] = [[targets[0]]]
    blockers: list[int] = []
    previous = targets[0]
    for string in targets[1:]:
        gap_blockers = _blocking_strings_between(string_frets, fret, previous, string)
        if gap_blockers:
            blockers.extend(gap_blockers)
            groups.append([string])
        else:
            groups[-1].append(string)
        previous = string

    frozen_groups = tuple(
        FrettingGroup(
            fret=fret,
            strings=tuple(group),
            span_start_string=group[0],
            span_end_string=group[-1],
        )
        for group in groups
    )
    return frozen_groups, tuple(sorted(set(blockers)))


def fretting_resource_facts(candidate: Voicing) -> FrettingResourceFacts:
    """Compute the frozen four-finger/barre resource lower bound for one voicing."""

    if not candidate:
        raise ValueError("candidate voicing must not be empty")
    string_frets = _string_fret_map(candidate)
    positive_frets = tuple(sorted({fret for fret in string_frets.values() if fret > 0}))

    groups: list[FrettingGroup] = []
    blockers_by_fret: list[tuple[int, tuple[int, ...]]] = []
    for fret in positive_frets:
        fret_groups, blockers = _groups_for_fret(candidate, fret, string_frets)
        groups.extend(fret_groups)
        blockers_by_fret.append((fret, blockers))

    ordered_groups = tuple(sorted(
        groups,
        key=lambda group: (group.fret, group.span_start_string, group.span_end_string, group.strings),
    ))
    minimum_standard_fingers = len(ordered_groups)
    canonical_assignment = (
        tuple(
            (finger, group.fret, group.strings)
            for finger, group in enumerate(ordered_groups, start=1)
        )
        if minimum_standard_fingers <= 4
        else ()
    )

    return FrettingResourceFacts(
        positive_frets=positive_frets,
        groups=ordered_groups,
        blockers_by_fret=tuple(blockers_by_fret),
        minimum_standard_fingers=minimum_standard_fingers,
        canonical_assignment=canonical_assignment,
    )


def analyze_standard_fingering_feasibility(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
) -> FingeringFeasibilityResult:
    """Apply S1-H-B after recomputing the complete authoritative S1-H-A state."""

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    if len(tuning) != 6:
        raise ValueError("S1-H-B supports six-string guitar tuning only")

    upstream = analyze_valid_chord_voicings(pitches, tuning)
    if upstream.rule_version != S1H_RULE_VERSION:
        raise RuntimeError(
            f"S1-H-B requires upstream rule version {S1H_RULE_VERSION}, "
            f"got {upstream.rule_version}"
        )

    upstream_retained = set(upstream.retained_candidates)
    assessments: list[FingeringResourceAssessment] = []
    final_retained: list[Voicing] = []

    for upstream_item in upstream.assessments:
        if upstream_item.pruned:
            assessments.append(FingeringResourceAssessment(
                candidate_id=upstream_item.candidate_id,
                candidate=upstream_item.candidate,
                upstream_classification=upstream_item.classification,
                classification="UPSTREAM_PRUNED",
                pruned=True,
                reason_codes=_ordered_reason_codes((U100_UPSTREAM_S1H_A_PRUNED,)),
                facts=None,
            ))
            continue

        facts = fretting_resource_facts(upstream_item.candidate)
        if facts.minimum_standard_fingers >= 5:
            classification = "RESOURCE_INFEASIBLE"
            pruned = True
            reason_codes = (H101_MIN_STANDARD_FINGERS_GE_5,)
        else:
            classification = "RESOURCE_FEASIBLE"
            pruned = False
            reason_codes = ()
            final_retained.append(upstream_item.candidate)

        assessments.append(FingeringResourceAssessment(
            candidate_id=upstream_item.candidate_id,
            candidate=upstream_item.candidate,
            upstream_classification=upstream_item.classification,
            classification=classification,
            pruned=pruned,
            reason_codes=_ordered_reason_codes(reason_codes),
            facts=facts,
        ))

    raw = upstream.raw_candidates
    retained = tuple(final_retained)
    if not set(retained).issubset(upstream_retained):
        raise AssertionError("S1-H-B retained a candidate outside S1-H-A retained candidates")
    if any(
        item.candidate in retained and item.classification == "UPSTREAM_PRUNED"
        for item in assessments
    ):
        raise AssertionError("S1-H-B reintroduced an upstream-pruned candidate")
    if len(assessments) != len(raw):
        raise AssertionError("S1-H-B audit does not cover the complete upstream raw set")

    status = S1HB_OK if retained else S1HB_NO_STANDARD_FINGERING_CANDIDATE
    return FingeringFeasibilityResult(
        rule_version=S1HB_RULE_VERSION,
        upstream_rule_version=upstream.rule_version,
        status=status,
        raw_candidates=raw,
        upstream_retained_candidates=upstream.retained_candidates,
        retained_candidates=retained,
        assessments=tuple(assessments),
    )
