from __future__ import annotations

from dataclasses import dataclass
from string import hexdigits
from typing import Iterable, Mapping

from .dataset import Voicing, valid_chord_voicings


TEACHER_GOLD_LABEL = "TEACHER_GOLD"
STATELESS_SPECIALISTS = (
    "open_low",
    "compact",
    "mid_position",
    "high_position",
)
STAGE7G_MINIMUM_INDEPENDENT_FAMILIES = 30
STAGE7G_MINIMUM_TEACHER_LABELED_AMBIGUOUS_EVENTS = 600
STAGE7G_MINIMUM_SPECIALIST_DISAGREEMENT_EVENTS = 100


@dataclass(frozen=True)
class TeacherAnnotationTask:
    """Target-blind annotation task containing the complete physical candidate set."""

    source_sha256: str
    source_origin: str
    family_id: str
    event_id: str
    pitches_midi: tuple[int, ...]
    tuning: tuple[int, ...]
    candidates: tuple[Voicing, ...]


@dataclass(frozen=True)
class TeacherGoldRecord:
    """One accepted human guitaristic preference label for an ambiguous chord event."""

    source_sha256: str
    source_origin: str
    family_id: str
    event_id: str
    pitches_midi: tuple[int, ...]
    tuning: tuple[int, ...]
    teacher_preferred: Voicing
    annotator_id: str
    specialist_top1: tuple[tuple[str, Voicing], ...]
    annotation_blinded_to_specialists: bool = True
    label_semantics: str = TEACHER_GOLD_LABEL


@dataclass(frozen=True)
class TeacherGoldCorpusSummary:
    independent_families: int
    teacher_labeled_ambiguous_events: int
    specialist_disagreement_events: int
    stage7g_minimums_met: bool


def _canonical_voicing(voicing: Iterable[tuple[int, int, int]]) -> Voicing:
    return tuple(sorted((int(pitch), int(string), int(fret)) for pitch, string, fret in voicing))


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(char not in hexdigits for char in value):
        raise ValueError("source_sha256 must be a 64-character hexadecimal SHA-256")


def build_teacher_annotation_task(
    *,
    source_sha256: str,
    source_origin: str,
    family_id: str,
    event_id: str,
    pitches_midi: Iterable[int],
    tuning: Iterable[int],
) -> TeacherAnnotationTask:
    """Create a blind Teacher-GOLD task from deterministic physical candidates only.

    No observed guitar placement and no specialist prediction enters this task.
    The teacher therefore chooses only among the complete deterministic candidate set.
    """

    _validate_sha256(source_sha256)
    if not source_origin.strip():
        raise ValueError("source_origin is required")
    if not family_id.strip():
        raise ValueError("family_id is required")
    if not event_id.strip():
        raise ValueError("event_id is required")

    pitches = tuple(sorted(int(pitch) for pitch in pitches_midi))
    guitar_tuning = tuple(int(open_midi) for open_midi in tuning)
    if len(guitar_tuning) != 6:
        raise ValueError("Stage 7G Teacher-GOLD v1 supports six-string guitars only")
    if len(pitches) < 2:
        raise ValueError("Teacher-GOLD chord tasks require at least two pitches")
    if any(pitch < 0 or pitch > 127 for pitch in pitches):
        raise ValueError("MIDI pitches must be within 0..127")

    candidates = valid_chord_voicings(pitches, guitar_tuning)
    if len(candidates) < 2:
        raise ValueError("Teacher-GOLD v1 accepts ambiguous events with at least two physical candidates")

    return TeacherAnnotationTask(
        source_sha256=source_sha256.lower(),
        source_origin=source_origin,
        family_id=family_id,
        event_id=event_id,
        pitches_midi=pitches,
        tuning=guitar_tuning,
        candidates=candidates,
    )


def finalize_teacher_gold_record(
    task: TeacherAnnotationTask,
    *,
    teacher_preferred: Iterable[tuple[int, int, int]],
    annotator_id: str,
    specialist_top1: Mapping[str, Iterable[tuple[int, int, int]]],
) -> TeacherGoldRecord:
    """Finalize a blind teacher choice and attach model diagnostics after annotation.

    `specialist_top1` is audit/sampling metadata. It must contain the four stateless
    specialists and is never allowed to include `common_tone` in Stage 7G v1.
    """

    if set(specialist_top1) != set(STATELESS_SPECIALISTS):
        raise ValueError("specialist_top1 must contain exactly the four stateless specialists")

    preferred = _canonical_voicing(teacher_preferred)
    predictions = tuple(
        (style, _canonical_voicing(specialist_top1[style]))
        for style in STATELESS_SPECIALISTS
    )
    record = TeacherGoldRecord(
        source_sha256=task.source_sha256,
        source_origin=task.source_origin,
        family_id=task.family_id,
        event_id=task.event_id,
        pitches_midi=task.pitches_midi,
        tuning=task.tuning,
        teacher_preferred=preferred,
        annotator_id=annotator_id,
        specialist_top1=predictions,
        annotation_blinded_to_specialists=True,
        label_semantics=TEACHER_GOLD_LABEL,
    )
    validate_teacher_gold_record(record)
    if task.candidates != valid_chord_voicings(task.pitches_midi, task.tuning):
        raise ValueError("annotation task candidate set no longer matches deterministic candidates")
    return record


def validate_teacher_gold_record(record: TeacherGoldRecord) -> None:
    _validate_sha256(record.source_sha256)
    if not record.source_origin.strip():
        raise ValueError("source_origin is required")
    if not record.family_id.strip():
        raise ValueError("family_id is required")
    if not record.event_id.strip():
        raise ValueError("event_id is required")
    if not record.annotator_id.strip():
        raise ValueError("annotator_id is required")
    if record.label_semantics != TEACHER_GOLD_LABEL:
        raise ValueError("Stage 7G records must use TEACHER_GOLD label semantics")
    if not record.annotation_blinded_to_specialists:
        raise ValueError("Teacher-GOLD annotation must be blind to specialist predictions")
    if len(record.tuning) != 6:
        raise ValueError("Stage 7G Teacher-GOLD v1 supports six-string guitars only")

    pitches = tuple(sorted(int(pitch) for pitch in record.pitches_midi))
    if pitches != record.pitches_midi:
        raise ValueError("pitches_midi must be sorted canonically")
    candidates = valid_chord_voicings(pitches, record.tuning)
    if len(candidates) < 2:
        raise ValueError("Teacher-GOLD record must represent an ambiguous event")

    preferred = _canonical_voicing(record.teacher_preferred)
    if preferred != record.teacher_preferred:
        raise ValueError("teacher_preferred must be canonical")
    if preferred not in candidates:
        raise ValueError("teacher-preferred voicing is not in the deterministic physical candidate set")

    predictions = dict(record.specialist_top1)
    if set(predictions) != set(STATELESS_SPECIALISTS):
        raise ValueError("specialist_top1 must contain exactly the four stateless specialists")
    if len(record.specialist_top1) != len(STATELESS_SPECIALISTS):
        raise ValueError("specialist_top1 contains duplicate specialist entries")
    for style, prediction in record.specialist_top1:
        if style == "common_tone":
            raise ValueError("common_tone is excluded from Stage 7G v1")
        canonical = _canonical_voicing(prediction)
        if canonical != prediction:
            raise ValueError("specialist predictions must be canonical")
        if canonical not in candidates:
            raise ValueError(f"{style} prediction is not a deterministic physical candidate")


def is_specialist_disagreement(record: TeacherGoldRecord) -> bool:
    validate_teacher_gold_record(record)
    return len({prediction for _, prediction in record.specialist_top1}) > 1


def validate_teacher_gold_corpus(
    records: Iterable[TeacherGoldRecord],
    *,
    forbidden_source_hashes: Iterable[str] = (),
    forbidden_source_origins: Iterable[str] = (),
    require_stage7g_minimums: bool = False,
) -> TeacherGoldCorpusSummary:
    """Validate corpus identity, final-test quarantine, and Stage 7G size gates."""

    rows = tuple(records)
    forbidden_hashes = {value.lower() for value in forbidden_source_hashes}
    forbidden_origins = set(forbidden_source_origins)

    event_ids: set[str] = set()
    source_family: dict[str, str] = {}
    families: set[str] = set()
    disagreement_events = 0

    for record in rows:
        validate_teacher_gold_record(record)
        if record.source_sha256.lower() in forbidden_hashes:
            raise ValueError("Teacher-GOLD source hash overlaps a quarantined final-test source")
        if record.source_origin in forbidden_origins:
            raise ValueError("Teacher-GOLD source origin overlaps a quarantined final-test source")
        if record.event_id in event_ids:
            raise ValueError("duplicate Teacher-GOLD event_id")
        event_ids.add(record.event_id)

        known_family = source_family.setdefault(record.source_sha256, record.family_id)
        if known_family != record.family_id:
            raise ValueError("one source hash cannot belong to multiple families")
        families.add(record.family_id)
        disagreement_events += int(is_specialist_disagreement(record))

    summary = TeacherGoldCorpusSummary(
        independent_families=len(families),
        teacher_labeled_ambiguous_events=len(rows),
        specialist_disagreement_events=disagreement_events,
        stage7g_minimums_met=(
            len(families) >= STAGE7G_MINIMUM_INDEPENDENT_FAMILIES
            and len(rows) >= STAGE7G_MINIMUM_TEACHER_LABELED_AMBIGUOUS_EVENTS
            and disagreement_events >= STAGE7G_MINIMUM_SPECIALIST_DISAGREEMENT_EVENTS
        ),
    )
    if require_stage7g_minimums and not summary.stage7g_minimums_met:
        raise ValueError(
            "Stage 7G corpus minimums not met: need >=30 families, >=600 Teacher-GOLD "
            "ambiguous events, and >=100 specialist-disagreement events"
        )
    return summary
