from __future__ import annotations

from collections import Counter
from hashlib import sha256

from .s2a_batch import S2AEventPackage
from .s2a_features import S2A_PROTOCOL_VERSION
from .s2a_teacher import S2A_FIRST_PASS_PROVENANCE, build_s2a_teacher_package
from .target_free_musicxml import TargetFreeSource


S2A_SOURCE_POOL_MIN_EVENTS_PER_FAMILY = 8
S2A_SOURCE_POOL_MIN_CANDIDATES_PER_CELL = 180
_CELLS = tuple(
    (pair_type, stratum)
    for pair_type in ("FINGER_ONLY", "MIXED")
    for stratum in ("NEAR", "MID", "FAR")
)


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _event_id(source: TargetFreeSource, event) -> str:
    payload = "|".join(
        (
            S2A_PROTOCOL_VERSION,
            source.family_id,
            source.source_sha256,
            str(event.measure),
            str(event.onset),
            str(event.voice),
            ",".join(str(value) for value in event.pitches_midi),
        )
    )
    return f"s2a-event-sha256:{_digest(payload)}"


def build_bounded_real_source_pool(
    sources: tuple[TargetFreeSource, ...],
    *,
    min_events_per_family: int = S2A_SOURCE_POOL_MIN_EVENTS_PER_FAMILY,
    min_candidates_per_cell: int = S2A_SOURCE_POOL_MIN_CANDIDATES_PER_CELL,
) -> tuple[S2AEventPackage, ...]:
    """Round-robin real sources and stop once the downstream batch has a safe pool.

    The stop rule uses only label-free source/event identity and S1-H-C/S2-A sampling
    metadata. It never consumes historical or current Teacher responses.
    """

    ordered_sources = tuple(sorted(sources, key=lambda source: source.family_id))
    if len(ordered_sources) != 40 or len({source.family_id for source in ordered_sources}) != 40:
        raise ValueError("S2-A real-source pool requires exactly 40 distinct families")
    if min_events_per_family < 5 or min_candidates_per_cell < 120:
        raise ValueError("S2-A bounded-pool safety margins cannot be below fit/batch minimums")

    events_by_family = {}
    for source in ordered_sources:
        eligible = tuple(
            event
            for event in source.events
            if event.is_chord and len(event.pitches_midi) <= 6
        )
        if not eligible:
            raise ValueError(f"S2-A source family {source.family_id} has no chord events")
        events_by_family[source.family_id] = eligible

    cursors = Counter()
    family_package_counts = Counter()
    cell_candidate_counts = Counter()
    packages: list[S2AEventPackage] = []
    seen_event_ids: set[str] = set()

    def goal_reached() -> bool:
        return (
            all(family_package_counts[source.family_id] >= min_events_per_family for source in ordered_sources)
            and all(cell_candidate_counts[cell] >= min_candidates_per_cell for cell in _CELLS)
        )

    while not goal_reached():
        made_progress = False
        for source in ordered_sources:
            family_id = source.family_id
            events = events_by_family[family_id]
            while cursors[family_id] < len(events):
                event = events[cursors[family_id]]
                cursors[family_id] += 1
                event_id = _event_id(source, event)
                if event_id in seen_event_ids:
                    raise ValueError("duplicate S2-A event identity while building bounded pool")
                seen_event_ids.add(event_id)
                try:
                    teacher_manifest, audit = build_s2a_teacher_package(
                        family_id=family_id,
                        event_id=event_id,
                        pitches_midi=event.pitches_midi,
                        tuning=event.tuning,
                        provenance=S2A_FIRST_PASS_PROVENANCE,
                    )
                except ValueError as exc:
                    if "at least two distinct H-C assignments" in str(exc):
                        continue
                    raise
                package = S2AEventPackage(
                    family_id=family_id,
                    event_id=event_id,
                    teacher_tasks=tuple(teacher_manifest["tasks"]),
                    audit_rows=tuple(audit["rows"]),
                )
                packages.append(package)
                family_package_counts[family_id] += 1
                for row in package.audit_rows:
                    cell_candidate_counts[(row["pair_type"], row["distance_stratum"])] += 1
                made_progress = True
                break
        if not made_progress:
            missing_families = sorted(
                source.family_id
                for source in ordered_sources
                if family_package_counts[source.family_id] < min_events_per_family
            )
            missing_cells = {
                f"{cell[0]}|{cell[1]}": cell_candidate_counts[cell]
                for cell in _CELLS
                if cell_candidate_counts[cell] < min_candidates_per_cell
            }
            raise ValueError(
                f"S2-A real sources exhausted before bounded-pool gate; "
                f"families={missing_families}, cells={missing_cells}"
            )

    packages.sort(key=lambda item: (item.family_id, item.event_id))
    return tuple(packages)
