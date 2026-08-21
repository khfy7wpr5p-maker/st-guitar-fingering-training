from __future__ import annotations

from typing import Iterable

from .guitarset_teacher_voicing import (
    STANDARD_TUNING_BY_STRING,
    build_teacher_voicing_task,
    exact_candidates,
)


def build_complete_blinded_teacher_voicing_task(
    *,
    event_id: str,
    pitches_midi: Iterable[int],
    observed_placements: Iterable[Iterable[int]],
    tuning: tuple[int, ...] = STANDARD_TUNING_BY_STRING,
    option_cap: int = 6,
) -> tuple[dict, dict]:
    """Build a task only when every exact physical candidate can be shown.

    This is the fail-closed public seam for the GuitarSet Teacher Voicing pilot.
    It prevents the hidden observed answer from becoming inferable through
    an observed-plus-sampled-alternatives display rule.
    """
    pitches = tuple(sorted(int(value) for value in pitches_midi))
    candidates = exact_candidates(pitches, tuning)
    if len(candidates) < 2:
        raise ValueError("teacher voicing pilot requires at least two physical candidates")
    if len(candidates) > option_cap:
        raise ValueError("teacher voicing pilot refuses partial candidate display")
    task, audit = build_teacher_voicing_task(
        event_id=event_id,
        pitches_midi=pitches,
        observed_placements=observed_placements,
        tuning=tuning,
        option_cap=option_cap,
    )
    if task["option_count"] != task["full_candidate_count"]:
        raise AssertionError("teacher voicing pilot must show every exact physical candidate")
    return task, audit
