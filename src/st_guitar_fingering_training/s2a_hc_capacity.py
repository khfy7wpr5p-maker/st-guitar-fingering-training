from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .finger_assignments import generate_standard_fingerings


S2A_HC_CAPACITY_RULE_VERSION = "S2A-HC-CAPACITY.v1"
S2A_HC_MIN_ELIGIBLE_EVENTS = 8


@dataclass(frozen=True)
class HCCapacityEvent:
    measure: int
    onset: str
    voice: str
    pitches_midi: tuple[int, ...]
    assignment_count: int


@dataclass(frozen=True)
class HCCapacityAudit:
    rule_version: str
    status: str
    reason: str
    required_eligible_events: int
    eligible_event_count: int
    checked_chord_event_count: int
    skipped_non_chord_or_wide_event_count: int
    zero_assignment_event_count: int
    one_assignment_event_count: int
    source_scan_exhausted: bool
    qualifying_events: tuple[HCCapacityEvent, ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def _event_identity(event) -> tuple[int, str, str, tuple[int, ...]]:
    return (
        int(event.measure),
        str(event.onset),
        str(event.voice),
        tuple(sorted(int(value) for value in event.pitches_midi)),
    )


def _distinct_assignment_count(generated) -> int:
    assignment_ids: set[str] = set()
    counted = 0
    for candidate in generated.candidates:
        for assignment in candidate.assignments:
            counted += 1
            if assignment.assignment_id in assignment_ids:
                raise AssertionError("H-C capacity audit observed duplicate assignment_id within one event")
            assignment_ids.add(assignment.assignment_id)
    if counted != generated.total_assignment_count:
        raise AssertionError("H-C capacity audit assignment total disagrees with S1-H-C result")
    return len(assignment_ids)


def audit_hc_capacity(
    events: Iterable[object],
    *,
    min_eligible_events: int = S2A_HC_MIN_ELIGIBLE_EVENTS,
    generation_fn: Callable = generate_standard_fingerings,
) -> HCCapacityAudit:
    """Run the bounded S1-H-C capacity gate over one target-free source.

    PASS is reached as soon as ``min_eligible_events`` chord events each yield at
    least two distinct S1-H-C assignments. A FAIL is declared only after the source
    is exhausted. No labels, model scores, source fingering, or preference features
    participate in this decision.
    """

    if min_eligible_events < 1:
        raise ValueError("H-C capacity minimum must be positive")

    eligible: list[HCCapacityEvent] = []
    checked_chords = 0
    skipped = 0
    zero_assignment = 0
    one_assignment = 0

    for event in events:
        pitches = tuple(sorted(int(value) for value in event.pitches_midi))
        if not bool(event.is_chord) or len(pitches) > 6:
            skipped += 1
            continue

        checked_chords += 1
        try:
            generated = generation_fn(pitches, tuple(int(value) for value in event.tuning))
            assignment_count = _distinct_assignment_count(generated)
        except Exception as exc:  # deterministic fail-closed boundary
            return HCCapacityAudit(
                rule_version=S2A_HC_CAPACITY_RULE_VERSION,
                status="FAIL",
                reason=f"S2A_HC_002_GENERATION_ERROR:{type(exc).__name__}",
                required_eligible_events=min_eligible_events,
                eligible_event_count=len(eligible),
                checked_chord_event_count=checked_chords,
                skipped_non_chord_or_wide_event_count=skipped,
                zero_assignment_event_count=zero_assignment,
                one_assignment_event_count=one_assignment,
                source_scan_exhausted=False,
                qualifying_events=tuple(eligible),
            )

        if assignment_count == 0:
            zero_assignment += 1
            continue
        if assignment_count == 1:
            one_assignment += 1
            continue

        measure, onset, voice, event_pitches = _event_identity(event)
        eligible.append(HCCapacityEvent(
            measure=measure,
            onset=onset,
            voice=voice,
            pitches_midi=event_pitches,
            assignment_count=assignment_count,
        ))
        if len(eligible) >= min_eligible_events:
            return HCCapacityAudit(
                rule_version=S2A_HC_CAPACITY_RULE_VERSION,
                status="PASS",
                reason="S2A_HC_000_MIN_CAPACITY_REACHED",
                required_eligible_events=min_eligible_events,
                eligible_event_count=len(eligible),
                checked_chord_event_count=checked_chords,
                skipped_non_chord_or_wide_event_count=skipped,
                zero_assignment_event_count=zero_assignment,
                one_assignment_event_count=one_assignment,
                source_scan_exhausted=False,
                qualifying_events=tuple(eligible),
            )

    return HCCapacityAudit(
        rule_version=S2A_HC_CAPACITY_RULE_VERSION,
        status="FAIL",
        reason="S2A_HC_001_INSUFFICIENT_ELIGIBLE_EVENTS",
        required_eligible_events=min_eligible_events,
        eligible_event_count=len(eligible),
        checked_chord_event_count=checked_chords,
        skipped_non_chord_or_wide_event_count=skipped,
        zero_assignment_event_count=zero_assignment,
        one_assignment_event_count=one_assignment,
        source_scan_exhausted=True,
        qualifying_events=tuple(eligible),
    )


def audit_to_dict(audit: HCCapacityAudit) -> dict:
    return {
        "rule_version": audit.rule_version,
        "status": audit.status,
        "reason": audit.reason,
        "required_eligible_events": audit.required_eligible_events,
        "eligible_event_count": audit.eligible_event_count,
        "checked_chord_event_count": audit.checked_chord_event_count,
        "skipped_non_chord_or_wide_event_count": audit.skipped_non_chord_or_wide_event_count,
        "zero_assignment_event_count": audit.zero_assignment_event_count,
        "one_assignment_event_count": audit.one_assignment_event_count,
        "source_scan_exhausted": audit.source_scan_exhausted,
        "qualifying_events": [
            {
                "measure": event.measure,
                "onset": event.onset,
                "voice": event.voice,
                "pitches_midi": list(event.pitches_midi),
                "assignment_count": event.assignment_count,
            }
            for event in audit.qualifying_events
        ],
    }
