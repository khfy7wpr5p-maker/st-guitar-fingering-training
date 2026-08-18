from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

from .curriculum_contract import STAGE7G_E3_GEOMETRY_NAMES, stage7g_e3_proposal_geometry
from .dataset import Voicing, valid_chord_voicings


S1H_RULE_VERSION = "S1-H-A.v1"
S1H_CLASSES = ("PLAUSIBLE", "BORDERLINE", "DOMINATED", "IMPRACTICAL")
S1H_OK = "OK"
S1H_NO_PLAUSIBLE_CANDIDATE = "NO_PLAUSIBLE_CANDIDATE"

H001_MIN_FINGER_PROXY_GE_6 = "H001_MIN_FINGER_PROXY_GE_6"
D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY = "D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY"
B001_FIVE_DISTINCT_POSITIVE_FRETS = "B001_FIVE_DISTINCT_POSITIVE_FRETS"

S1H_REASON_PRIORITY = (
    H001_MIN_FINGER_PROXY_GE_6,
    D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY,
    B001_FIVE_DISTINCT_POSITIVE_FRETS,
)


@dataclass(frozen=True)
class GuitaristicFacts:
    geometry: tuple[tuple[str, float], ...]
    used_strings: tuple[int, ...]
    open_strings: tuple[int, ...]
    fretted_strings: tuple[int, ...]
    fretted_string_topology: tuple[str, ...]
    contiguous_fretted_runs: tuple[tuple[int, ...], ...]
    isolated_fretted_string_count: int
    internal_gap_positions: tuple[int, ...]
    effective_fretted_hand_span: int
    same_fret_contiguous_barre_opportunities: tuple[tuple[int, int, int, int], ...]
    conservative_minimum_finger_proxy: int


@dataclass(frozen=True)
class CandidateAssessment:
    candidate_id: str
    candidate: Voicing
    classification: str
    pruned: bool
    reason_codes: tuple[str, ...]
    compared_candidate_id: str | None
    facts: GuitaristicFacts


@dataclass(frozen=True)
class GuitaristicPlausibilityResult:
    rule_version: str
    status: str
    raw_candidates: tuple[Voicing, ...]
    retained_candidates: tuple[Voicing, ...]
    assessments: tuple[CandidateAssessment, ...]


def _canonical_voicing(candidate: Iterable[tuple[int, int, int]]) -> Voicing:
    placements = tuple(sorted((int(pitch), int(string), int(fret)) for pitch, string, fret in candidate))
    if not placements:
        raise ValueError("candidate voicing must not be empty")
    return placements


def _candidate_id(candidate: Voicing) -> str:
    payload = json.dumps(candidate, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return f"voicing-sha256:{sha256(payload).hexdigest()}"


def _contiguous_runs(strings: Iterable[int]) -> tuple[tuple[int, ...], ...]:
    ordered = tuple(sorted(set(int(value) for value in strings)))
    if not ordered:
        return ()
    runs: list[list[int]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value == runs[-1][-1] + 1:
            runs[-1].append(value)
        else:
            runs.append([value])
    return tuple(tuple(run) for run in runs)


def _facts(candidate: Voicing) -> GuitaristicFacts:
    geometry_values = stage7g_e3_proposal_geometry(candidate)
    geometry = tuple(zip(STAGE7G_E3_GEOMETRY_NAMES, geometry_values))
    geometry_map = dict(geometry)

    used_strings = tuple(sorted(string for _, string, _ in candidate))
    open_strings = tuple(sorted(string for _, string, fret in candidate if fret == 0))
    fretted_strings = tuple(sorted(string for _, string, fret in candidate if fret > 0))
    fretted_runs = _contiguous_runs(fretted_strings)

    used_set = set(used_strings)
    internal_gap_positions = tuple(
        string
        for string in range(min(used_strings), max(used_strings) + 1)
        if string not in used_set
    )

    by_fret: dict[int, list[int]] = {}
    for _, string, fret in candidate:
        if fret > 0:
            by_fret.setdefault(fret, []).append(string)
    barre_opportunities: list[tuple[int, int, int, int]] = []
    for fret in sorted(by_fret):
        for run in _contiguous_runs(by_fret[fret]):
            if len(run) >= 2:
                barre_opportunities.append((fret, run[0], run[-1], len(run)))

    topology = tuple(
        "O" if string in open_strings else "F" if string in fretted_strings else "-"
        for string in range(1, 7)
    )
    minimum_finger_proxy = int(geometry_map["unique_positive_frets"])

    return GuitaristicFacts(
        geometry=geometry,
        used_strings=used_strings,
        open_strings=open_strings,
        fretted_strings=fretted_strings,
        fretted_string_topology=topology,
        contiguous_fretted_runs=fretted_runs,
        isolated_fretted_string_count=sum(len(run) == 1 for run in fretted_runs),
        internal_gap_positions=internal_gap_positions,
        effective_fretted_hand_span=int(geometry_map["positive_fret_span"]),
        same_fret_contiguous_barre_opportunities=tuple(barre_opportunities),
        conservative_minimum_finger_proxy=minimum_finger_proxy,
    )


def _mechanically_dominates(left: GuitaristicFacts, right: GuitaristicFacts) -> bool:
    """Return factual, diagnostic-only dominance inside an identical string topology.

    Position height, open-string count, tone, resonance, and voicing beauty are not
    compared. This relation is deliberately too conservative to authorize pruning.
    """

    if (
        left.used_strings != right.used_strings
        or left.open_strings != right.open_strings
        or left.fretted_strings != right.fretted_strings
    ):
        return False
    left_vector = (
        left.conservative_minimum_finger_proxy,
        left.effective_fretted_hand_span,
    )
    right_vector = (
        right.conservative_minimum_finger_proxy,
        right.effective_fretted_hand_span,
    )
    return all(a <= b for a, b in zip(left_vector, right_vector)) and any(
        a < b for a, b in zip(left_vector, right_vector)
    )


def _ordered_reason_codes(codes: Iterable[str]) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(codes))
    unknown = set(values) - set(S1H_REASON_PRIORITY)
    if unknown:
        raise AssertionError(f"unknown S1-H reason code(s): {sorted(unknown)}")
    return tuple(code for code in S1H_REASON_PRIORITY if code in values)


def analyze_guitaristic_plausibility(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
    raw_candidates: Iterable[Voicing],
) -> GuitaristicPlausibilityResult:
    """Analyze and conservatively prune a physically-valid candidate set.

    Every supplied candidate must already belong to the authoritative
    ``valid_chord_voicings()`` set for the same pitch-set and tuning. The analyzer
    never invents, repairs, or legalizes a voicing.
    """

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    if len(tuning) != 6:
        raise ValueError("S1-H-A supports six-string guitar tuning only")

    authoritative = set(valid_chord_voicings(pitches, tuning))
    supplied = tuple(_canonical_voicing(candidate) for candidate in raw_candidates)
    if not supplied:
        raise ValueError("raw physically-valid candidate set must not be empty")
    if len(supplied) != len(set(supplied)):
        raise ValueError("raw physically-valid candidate set contains duplicates")
    invalid = tuple(candidate for candidate in supplied if candidate not in authoritative)
    if invalid:
        raise ValueError("candidate outside authoritative valid_chord_voicings() set")

    raw = tuple(sorted(supplied, key=_candidate_id))
    facts_by_id = {_candidate_id(candidate): _facts(candidate) for candidate in raw}
    candidate_by_id = {_candidate_id(candidate): candidate for candidate in raw}

    assessments: list[CandidateAssessment] = []
    for candidate_id in sorted(candidate_by_id):
        candidate = candidate_by_id[candidate_id]
        facts = facts_by_id[candidate_id]

        dominators = [
            other_id
            for other_id, other_facts in facts_by_id.items()
            if other_id != candidate_id and _mechanically_dominates(other_facts, facts)
        ]
        compared_candidate_id = None
        reason_codes: list[str] = []

        if facts.conservative_minimum_finger_proxy >= 6:
            classification = "IMPRACTICAL"
            pruned = True
            reason_codes.append(H001_MIN_FINGER_PROXY_GE_6)
        elif dominators:
            classification = "DOMINATED"
            pruned = False
            compared_candidate_id = min(
                dominators,
                key=lambda other_id: (
                    facts_by_id[other_id].conservative_minimum_finger_proxy,
                    facts_by_id[other_id].effective_fretted_hand_span,
                    other_id,
                ),
            )
            reason_codes.append(D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY)
        elif facts.conservative_minimum_finger_proxy == 5:
            classification = "BORDERLINE"
            pruned = False
            reason_codes.append(B001_FIVE_DISTINCT_POSITIVE_FRETS)
        else:
            classification = "PLAUSIBLE"
            pruned = False

        assessments.append(CandidateAssessment(
            candidate_id=candidate_id,
            candidate=candidate,
            classification=classification,
            pruned=pruned,
            reason_codes=_ordered_reason_codes(reason_codes),
            compared_candidate_id=compared_candidate_id,
            facts=facts,
        ))

    assessments_tuple = tuple(assessments)
    retained = tuple(item.candidate for item in assessments_tuple if not item.pruned)
    if not set(retained).issubset(set(raw)):
        raise AssertionError("S1-H-A created a voicing outside the raw candidate set")
    status = S1H_OK if retained else S1H_NO_PLAUSIBLE_CANDIDATE
    return GuitaristicPlausibilityResult(
        rule_version=S1H_RULE_VERSION,
        status=status,
        raw_candidates=raw,
        retained_candidates=retained,
        assessments=assessments_tuple,
    )


def analyze_valid_chord_voicings(
    pitches_midi: Iterable[int],
    tuning: tuple[int, ...],
) -> GuitaristicPlausibilityResult:
    """Preferred full-set entry point immediately after physical enumeration."""

    pitches = tuple(sorted(int(value) for value in pitches_midi))
    tuning = tuple(int(value) for value in tuning)
    raw = valid_chord_voicings(pitches, tuning)
    if not raw:
        raise ValueError("valid_chord_voicings() produced no physical candidates")
    return analyze_guitaristic_plausibility(pitches, tuning, raw)
