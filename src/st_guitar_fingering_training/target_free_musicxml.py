from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from defusedxml import ElementTree as ET

from .intake import MAX_SOURCE_BYTES, pitch_to_midi


SUPPORTED_PITCH_MODES = ("sounding_exact", "written_octave_plus_12")


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _child_text(element: ET.Element, name: str) -> str | None:
    child = _first_child(element, name)
    return None if child is None else child.text


def _read_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"source byte size outside allowed range: {size}")
    return path.read_bytes()


def _validate_family_id(value: str) -> str:
    if not value or len(value) > 128 or any(ch.isspace() for ch in value):
        raise ValueError("family_id must be a non-empty whitespace-free identifier up to 128 characters")
    return value


def _validate_tuning(values: Iterable[int]) -> tuple[int, ...]:
    tuning = tuple(int(value) for value in values)
    if len(tuning) != 6:
        raise ValueError("Stage 7G-C v1 requires an explicit six-string guitar tuning")
    if any(value < 0 or value > 127 for value in tuning):
        raise ValueError("tuning MIDI pitches must be within 0..127")
    return tuning


def _select_part(root: ET.Element, part_id: str | None) -> tuple[ET.Element, str]:
    parts = _children(root, "part")
    if not parts:
        raise ValueError("MusicXML contains no parts")
    if part_id is None:
        if len(parts) != 1:
            raise ValueError("multi-part MusicXML requires explicit part_id for Stage 7G-C")
        selected = parts[0]
    else:
        matches = [part for part in parts if part.attrib.get("id") == part_id]
        if len(matches) != 1:
            raise ValueError("part_id must identify exactly one MusicXML part")
        selected = matches[0]
    selected_id = selected.attrib.get("id") or ""
    if not selected_id:
        raise ValueError("selected MusicXML part must have an id")
    return selected, selected_id


def _select_staff(part: ET.Element, staff_id: str | None) -> str | None:
    observed_staffs: set[str] = set()
    for measure in _children(part, "measure"):
        for note in _children(measure, "note"):
            if _first_child(note, "pitch") is None:
                continue
            value = _child_text(note, "staff")
            if value:
                observed_staffs.add(value)
    if staff_id is not None:
        if observed_staffs and staff_id not in observed_staffs:
            raise ValueError("staff_id does not occur on pitched notes in selected part")
        return staff_id
    if len(observed_staffs) > 1:
        raise ValueError("multi-staff MusicXML requires explicit staff_id for Stage 7G-C")
    return next(iter(observed_staffs)) if observed_staffs else None


def _declared_tuning(part: ET.Element, selected_staff: str | None) -> tuple[int, ...] | None:
    details = [element for element in part.iter() if _local_name(element.tag) == "staff-details"]
    chosen: ET.Element | None = None
    for detail in details:
        tunings = _children(detail, "staff-tuning")
        if not tunings:
            continue
        if selected_staff is not None and detail.attrib.get("number") == selected_staff:
            chosen = detail
            break
        if chosen is None:
            chosen = detail
    if chosen is None:
        return None

    by_line: dict[int, int] = {}
    for item in _children(chosen, "staff-tuning"):
        line_text = item.attrib.get("line")
        if line_text is None:
            raise ValueError("staff-tuning requires line")
        line = int(line_text)
        by_line[line] = pitch_to_midi(
            _child_text(item, "tuning-step") or "",
            _child_text(item, "tuning-octave") or "",
            _child_text(item, "tuning-alter"),
        )
    if sorted(by_line) != list(range(1, len(by_line) + 1)):
        raise ValueError("declared tuning lines must be contiguous from 1")
    max_line = max(by_line)
    return tuple(by_line[max_line + 1 - string_no] for string_no in range(1, max_line + 1))


def _sounding_pitch(note: ET.Element, pitch_mode: str) -> int:
    pitch = _first_child(note, "pitch")
    if pitch is None:
        raise ValueError("pitched note is missing pitch element")
    xml_midi = pitch_to_midi(
        _child_text(pitch, "step") or "",
        _child_text(pitch, "octave") or "",
        _child_text(pitch, "alter"),
    )
    sounding = xml_midi if pitch_mode == "sounding_exact" else xml_midi - 12
    if sounding < 0 or sounding > 127:
        raise ValueError("resolved sounding pitch outside MIDI range")
    return sounding


@dataclass(frozen=True)
class TargetFreeEvent:
    family_id: str
    source_sha256: str
    musicxml_version: str
    software: str
    pitch_mode: str
    tuning: tuple[int, ...]
    measure: str
    onset: int
    duration: int
    voice: str
    pitches_midi: tuple[int, ...]

    @property
    def is_chord(self) -> bool:
        return len(self.pitches_midi) > 1


@dataclass(frozen=True)
class TargetFreeSource:
    family_id: str
    source_sha256: str
    musicxml_version: str
    software: str
    pitch_mode: str
    tuning: tuple[int, ...]
    part_id: str
    selected_staff: str | None
    events: tuple[TargetFreeEvent, ...]


def parse_target_free_musicxml(
    path: str | Path,
    *,
    family_id: str,
    tuning: Iterable[int],
    pitch_mode: str,
    part_id: str | None = None,
    staff_id: str | None = None,
) -> TargetFreeSource:
    """Parse pitch/rhythm only; technical string/fret metadata is never consulted.

    Stage 7G-C deliberately requires the caller to state how MusicXML pitches map
    to sounding guitar pitches. Without existing string/fret labels there is no
    trustworthy physical target from which to infer the octave relation.
    """

    family = _validate_family_id(family_id)
    guitar_tuning = _validate_tuning(tuning)
    if pitch_mode not in SUPPORTED_PITCH_MODES:
        raise ValueError(
            "pitch_mode must be explicitly 'sounding_exact' or 'written_octave_plus_12'"
        )

    source_path = Path(path)
    raw = _read_bytes(source_path)
    digest = sha256(raw).hexdigest()
    root = ET.fromstring(raw)
    if _local_name(root.tag) != "score-partwise":
        raise ValueError("Stage 7G-C supports score-partwise MusicXML only")

    part, selected_part_id = _select_part(root, part_id)
    selected_staff = _select_staff(part, staff_id)
    declared = _declared_tuning(part, selected_staff)
    if declared is not None and declared != guitar_tuning:
        raise ValueError("explicit Stage 7G-C tuning conflicts with MusicXML staff-tuning")

    software = "unknown"
    for element in root.iter():
        if _local_name(element.tag) == "software" and element.text:
            software = element.text
            break
    version = root.attrib.get("version") or "1.0-unspecified"

    grouped: dict[tuple[str, int, str], list[int]] = {}
    durations: dict[tuple[str, int, str], int] = {}

    for measure in _children(part, "measure"):
        cursor = 0
        last_nonchord_onset = 0
        measure_no = measure.attrib.get("number", "")
        for child in list(measure):
            tag = _local_name(child.tag)
            if tag == "backup":
                cursor -= int(_child_text(child, "duration") or 0)
                if cursor < 0:
                    raise ValueError("backup moved cursor before measure start")
                continue
            if tag == "forward":
                cursor += int(_child_text(child, "duration") or 0)
                continue
            if tag != "note":
                continue

            chord = _first_child(child, "chord") is not None
            duration = int(_child_text(child, "duration") or 0)
            if duration <= 0:
                raise ValueError("note/rest duration must be positive")
            onset = last_nonchord_onset if chord else cursor
            if not chord:
                last_nonchord_onset = cursor
                cursor += duration

            note_staff = _child_text(child, "staff")
            selected = note_staff == selected_staff if selected_staff is not None else note_staff is None
            if not selected:
                continue
            if _first_child(child, "rest") is not None or _first_child(child, "pitch") is None:
                continue

            voice = _child_text(child, "voice") or "1"
            key = (measure_no, onset, voice)
            grouped.setdefault(key, []).append(_sounding_pitch(child, pitch_mode))
            durations[key] = max(durations.get(key, 0), duration)

    events: list[TargetFreeEvent] = []
    for (measure_no, onset, voice), pitches in grouped.items():
        canonical = tuple(sorted(int(pitch) for pitch in pitches))
        events.append(
            TargetFreeEvent(
                family_id=family,
                source_sha256=digest,
                musicxml_version=version,
                software=software,
                pitch_mode=pitch_mode,
                tuning=guitar_tuning,
                measure=measure_no,
                onset=onset,
                duration=durations[(measure_no, onset, voice)],
                voice=voice,
                pitches_midi=canonical,
            )
        )
    if not events:
        raise ValueError("no pitched events found in selected MusicXML part/staff")
    events.sort(
        key=lambda event: (
            int(event.measure) if event.measure.isdigit() else 10**9,
            event.measure,
            event.onset,
            event.voice,
        )
    )
    return TargetFreeSource(
        family_id=family,
        source_sha256=digest,
        musicxml_version=version,
        software=software,
        pitch_mode=pitch_mode,
        tuning=guitar_tuning,
        part_id=selected_part_id,
        selected_staff=selected_staff,
        events=tuple(events),
    )
