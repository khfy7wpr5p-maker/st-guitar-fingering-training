from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

import numpy as np

from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource
from .synthetic_behavior import _feature_vector
from .teacher_gold import (
    STATELESS_SPECIALISTS,
    TeacherAnnotationTask,
    build_teacher_annotation_task,
)


@dataclass(frozen=True)
class AnnotationSamplingDiagnostic:
    """Internal-only sampling metadata; never serialize this into the teacher view."""

    family_id: str
    source_sha256: str
    source_origin: str
    event_id: str
    candidate_count: int
    open_low_compact_disagreement: bool
    any_specialist_disagreement: bool
    specialist_top1: tuple[tuple[str, Voicing], ...]

    @property
    def priority_tier(self) -> int:
        if self.open_low_compact_disagreement:
            return 0
        if self.any_specialist_disagreement:
            return 1
        return 2


@dataclass(frozen=True)
class AnnotationSamplingEnvelope:
    task: TeacherAnnotationTask
    diagnostic: AnnotationSamplingDiagnostic


@dataclass(frozen=True)
class TeacherAnnotationBatch:
    """Selected blind tasks plus internal audit rows kept in a separate channel."""

    tasks: tuple[TeacherAnnotationTask, ...]
    diagnostics: tuple[AnnotationSamplingDiagnostic, ...]
    eligible_events: int
    eligible_families: int
    selected_families: int
    open_low_compact_disagreement_selected: int
    any_specialist_disagreement_selected: int


def _event_id(source: ParsedSource, event, index: int) -> str:
    return f"{source.source_sha256[:16]}:{event.measure}:{event.onset}:{event.voice}:{index}"


def _validate_specialist_models(models: Mapping[str, object]) -> None:
    if set(models) != set(STATELESS_SPECIALISTS):
        raise ValueError("Stage 7G-B requires exactly the four stateless specialists")


def _source_origin_map(
    sources: tuple[ParsedSource, ...],
    source_origins: Mapping[str, str],
) -> dict[str, str]:
    expected = {source.source_sha256.lower() for source in sources}
    supplied = {str(key).lower() for key in source_origins}
    if supplied != expected:
        raise ValueError("source_origins must contain exactly one entry for every source SHA-256")
    result = {str(key).lower(): str(value) for key, value in source_origins.items()}
    if any(not value.strip() for value in result.values()):
        raise ValueError("source origins must be non-empty")
    return result


def _specialist_predictions(
    candidates: tuple[Voicing, ...],
    models: Mapping[str, object],
) -> tuple[tuple[str, Voicing], ...]:
    predictions: list[tuple[str, Voicing]] = []
    for style in STATELESS_SPECIALISTS:
        features = np.asarray(
            [_feature_vector(style, candidate, None) for candidate in candidates],
            dtype=np.float64,
        )
        scores = np.asarray(models[style].decision_function(features), dtype=np.float64)
        if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
            raise ValueError(f"invalid specialist score vector for {style}")
        winner = max(range(len(candidates)), key=lambda item: (scores[item], -item))
        predictions.append((style, candidates[winner]))
    return tuple(predictions)


def build_annotation_sampling_pool(
    sources: Iterable[ParsedSource],
    *,
    source_origins: Mapping[str, str],
    specialist_models: Mapping[str, object],
    forbidden_source_hashes: Iterable[str] = (),
    forbidden_source_origins: Iterable[str] = (),
) -> tuple[AnnotationSamplingEnvelope, ...]:
    """Build a target-blind pool from new sources without consulting observed voicings.

    Event eligibility and priority use pitches, tuning, deterministic physical
    candidates, and frozen stateless specialist predictions only. The source's
    observed string/fret placement is deliberately never read by this function.
    """

    _validate_specialist_models(specialist_models)
    source_rows = tuple(sources)
    if not source_rows:
        raise ValueError("no sources supplied for Stage 7G-B annotation sampling")

    origins = _source_origin_map(source_rows, source_origins)
    forbidden_hashes = {str(value).lower() for value in forbidden_source_hashes}
    forbidden_origins = {str(value) for value in forbidden_source_origins}

    seen_source_hashes: set[str] = set()
    source_family: dict[str, str] = {}
    seen_event_ids: set[str] = set()
    envelopes: list[AnnotationSamplingEnvelope] = []

    for source in source_rows:
        digest = source.source_sha256.lower()
        if digest in seen_source_hashes:
            raise ValueError("duplicate source SHA-256 in Stage 7G-B input")
        seen_source_hashes.add(digest)
        origin = origins[digest]
        if digest in forbidden_hashes:
            raise ValueError("Stage 7G-B source hash overlaps a quarantined source")
        if origin in forbidden_origins:
            raise ValueError("Stage 7G-B source origin overlaps a quarantined source")

        known_family = source_family.setdefault(digest, source.family_id)
        if known_family != source.family_id:
            raise ValueError("one source hash cannot belong to multiple families")
        if len(source.tuning) != 6:
            raise ValueError("Stage 7G-B v1 supports six-string guitar sources only")

        for index, event in enumerate(source.events):
            if not event.is_chord:
                continue
            pitches = tuple(sorted(int(placement.sounding_midi) for placement in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if len(candidates) < 2:
                continue

            event_id = _event_id(source, event, index)
            if event_id in seen_event_ids:
                raise ValueError("duplicate annotation event_id")
            seen_event_ids.add(event_id)

            task = build_teacher_annotation_task(
                source_sha256=digest,
                source_origin=origin,
                family_id=source.family_id,
                event_id=event_id,
                pitches_midi=pitches,
                tuning=event.tuning,
            )
            if task.candidates != candidates:
                raise AssertionError("Stage 7G-B candidate set changed across deterministic boundary")

            predictions = _specialist_predictions(candidates, specialist_models)
            prediction_map = dict(predictions)
            distinct_predictions = {prediction for _, prediction in predictions}
            diagnostic = AnnotationSamplingDiagnostic(
                family_id=source.family_id,
                source_sha256=digest,
                source_origin=origin,
                event_id=event_id,
                candidate_count=len(candidates),
                open_low_compact_disagreement=(
                    prediction_map["open_low"] != prediction_map["compact"]
                ),
                any_specialist_disagreement=len(distinct_predictions) > 1,
                specialist_top1=predictions,
            )
            envelopes.append(AnnotationSamplingEnvelope(task=task, diagnostic=diagnostic))

    if not envelopes:
        raise ValueError("no ambiguous chord events eligible for Stage 7G-B")
    return tuple(envelopes)


def _stable_family_order(family_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(family_ids), key=lambda value: sha256(value.encode()).hexdigest()))


def select_annotation_batch(
    pool: Iterable[AnnotationSamplingEnvelope],
    *,
    max_tasks: int,
) -> TeacherAnnotationBatch:
    """Select tasks deterministically with disagreement-first, family-balanced rounds."""

    if max_tasks <= 0:
        raise ValueError("max_tasks must be positive")
    envelopes = tuple(pool)
    if not envelopes:
        raise ValueError("cannot select from an empty annotation pool")

    event_ids = [envelope.task.event_id for envelope in envelopes]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("annotation pool contains duplicate event ids")

    selected: list[AnnotationSamplingEnvelope] = []
    selected_ids: set[str] = set()
    family_ids = _stable_family_order(envelope.task.family_id for envelope in envelopes)

    # Global priority remains open_low-vs-compact disagreement, then any other
    # stateless disagreement, then consensus. Inside each tier, families are
    # round-robin balanced so one long piece cannot dominate the teacher queue.
    for tier in (0, 1, 2):
        by_family: dict[str, list[AnnotationSamplingEnvelope]] = defaultdict(list)
        for envelope in envelopes:
            if envelope.diagnostic.priority_tier == tier:
                by_family[envelope.task.family_id].append(envelope)
        for family in by_family:
            by_family[family].sort(
                key=lambda envelope: (
                    -envelope.diagnostic.candidate_count,
                    sha256(envelope.task.event_id.encode()).hexdigest(),
                )
            )

        cursor = 0
        while len(selected) < max_tasks:
            progressed = False
            for family in family_ids:
                rows = by_family.get(family, ())
                if cursor >= len(rows):
                    continue
                envelope = rows[cursor]
                if envelope.task.event_id in selected_ids:
                    raise AssertionError("Stage 7G-B selected one task more than once")
                selected.append(envelope)
                selected_ids.add(envelope.task.event_id)
                progressed = True
                if len(selected) >= max_tasks:
                    break
            if not progressed:
                break
            cursor += 1
        if len(selected) >= max_tasks:
            break

    selected_tuple = tuple(selected)
    selected_families = {envelope.task.family_id for envelope in selected_tuple}
    return TeacherAnnotationBatch(
        tasks=tuple(envelope.task for envelope in selected_tuple),
        diagnostics=tuple(envelope.diagnostic for envelope in selected_tuple),
        eligible_events=len(envelopes),
        eligible_families=len({envelope.task.family_id for envelope in envelopes}),
        selected_families=len(selected_families),
        open_low_compact_disagreement_selected=sum(
            diagnostic.open_low_compact_disagreement
            for diagnostic in (envelope.diagnostic for envelope in selected_tuple)
        ),
        any_specialist_disagreement_selected=sum(
            diagnostic.any_specialist_disagreement
            for diagnostic in (envelope.diagnostic for envelope in selected_tuple)
        ),
    )


def teacher_facing_manifest(batch: TeacherAnnotationBatch) -> dict:
    """Serialize only information a blinded teacher is allowed to see."""

    tasks = []
    for task in batch.tasks:
        tasks.append({
            "task_id": task.event_id,
            "pitches_midi": list(task.pitches_midi),
            "tuning": list(task.tuning),
            "candidates": [
                {
                    "candidate_id": f"candidate_{index + 1:04d}",
                    "placements": [
                        {"pitch_midi": pitch, "string": string, "fret": fret}
                        for pitch, string, fret in candidate
                    ],
                }
                for index, candidate in enumerate(task.candidates)
            ],
        })
    return {
        "schema": "st-guitar-stage7g-teacher-task-manifest-v1",
        "annotation_blinded": True,
        "model_predictions": "withheld",
        "observed_source_voicing": "withheld",
        "task_count": len(tasks),
        "tasks": tasks,
    }


def internal_sampling_audit(batch: TeacherAnnotationBatch) -> dict:
    """Serialize diagnostics separately; this object must not be teacher-facing."""

    rows = []
    for diagnostic in batch.diagnostics:
        rows.append({
            "event_id": diagnostic.event_id,
            "family_id": diagnostic.family_id,
            "source_sha256": diagnostic.source_sha256,
            "source_origin": diagnostic.source_origin,
            "candidate_count": diagnostic.candidate_count,
            "priority_tier": diagnostic.priority_tier,
            "open_low_compact_disagreement": diagnostic.open_low_compact_disagreement,
            "any_specialist_disagreement": diagnostic.any_specialist_disagreement,
            "specialist_top1": {
                style: [list(placement) for placement in voicing]
                for style, voicing in diagnostic.specialist_top1
            },
        })
    return {
        "schema": "st-guitar-stage7g-sampling-audit-v1",
        "teacher_facing": False,
        "target_voicing_used_for_sampling": False,
        "observed_string_fret_used_for_sampling": False,
        "priority_order": [
            "open_low_vs_compact_disagreement",
            "other_stateless_specialist_disagreement",
            "stateless_consensus",
        ],
        "family_balanced": True,
        "eligible_events": batch.eligible_events,
        "eligible_families": batch.eligible_families,
        "selected_events": len(batch.tasks),
        "selected_families": batch.selected_families,
        "open_low_compact_disagreement_selected": batch.open_low_compact_disagreement_selected,
        "any_specialist_disagreement_selected": batch.any_specialist_disagreement_selected,
        "rows": rows,
    }
