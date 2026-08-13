from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from defusedxml import ElementTree as ET

STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_FRET = 24


def pitch_to_midi(step: str, octave: str, alter: str | None = None) -> int:
    if step not in STEP_PC:
        raise ValueError(f"unsupported pitch step: {step!r}")
    value = 12 * (int(octave) + 1) + STEP_PC[step] + int(alter or 0)
    if not 0 <= value <= 127:
        raise ValueError("pitch outside MIDI range")
    return value


@dataclass(frozen=True)
class Placement:
    sounding_midi: int
    xml_midi: int
    string: int
    fret: int


@dataclass(frozen=True)
class GuitarEvent:
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
    placements: tuple[Placement, ...]

    @property
    def is_chord(self) -> bool:
        return len(self.placements) > 1


@dataclass(frozen=True)
class ParsedSource:
    family_id: str
    source_sha256: str
    musicxml_version: str
    software: str
    pitch_mode: str
    tuning: tuple[int, ...]
    selected_staff: str | None
    events: tuple[GuitarEvent, ...]


def _read_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"source byte size outside allowed range: {size}")
    return path.read_bytes()


def _select_staff(root: ET.Element) -> str | None:
    candidates: dict[str | None, int] = {}
    for note in root.findall(".//note"):
        if note.findtext(".//technical/string") and note.findtext(".//technical/fret") is not None:
            staff = note.findtext("staff")
            candidates[staff] = candidates.get(staff, 0) + 1
    if not candidates:
        raise ValueError("no technical string/fret labels found")
    if "2" in candidates:
        return "2"
    return max(candidates, key=candidates.get)


def _extract_tuning(root: ET.Element, selected_staff: str | None) -> tuple[int, ...]:
    details = root.findall(".//staff-details")
    chosen = None
    for sd in details:
        if selected_staff is not None and sd.attrib.get("number") == selected_staff and sd.findall("staff-tuning"):
            chosen = sd
            break
    if chosen is None:
        for sd in details:
            if sd.findall("staff-tuning"):
                chosen = sd
                break
    if chosen is None:
        raise ValueError("missing guitar tuning")
    by_line: dict[int, int] = {}
    for item in chosen.findall("staff-tuning"):
        line = int(item.attrib["line"])
        by_line[line] = pitch_to_midi(
            item.findtext("tuning-step") or "",
            item.findtext("tuning-octave") or "",
            item.findtext("tuning-alter"),
        )
    if not by_line or sorted(by_line) != list(range(1, len(by_line) + 1)):
        raise ValueError("tuning lines must be contiguous from 1")
    max_line = max(by_line)
    return tuple(by_line[max_line + 1 - string_no] for string_no in range(1, max_line + 1))


def _iter_selected_notes(root: ET.Element, selected_staff: str | None):
    for measure in root.findall(".//part/measure"):
        cursor = 0
        last_nonchord_onset = 0
        for child in list(measure):
            tag = child.tag.split("}")[-1]
            if tag == "backup":
                cursor -= int(child.findtext("duration") or 0)
                if cursor < 0:
                    raise ValueError("backup moved cursor before measure start")
                continue
            if tag == "forward":
                cursor += int(child.findtext("duration") or 0)
                continue
            if tag != "note":
                continue
            chord = child.find("chord") is not None
            duration = int(child.findtext("duration") or 0)
            if duration <= 0:
                raise ValueError("note/rest duration must be positive")
            onset = last_nonchord_onset if chord else cursor
            if not chord:
                last_nonchord_onset = cursor
                cursor += duration
            staff = child.findtext("staff")
            selected = staff == selected_staff if selected_staff is not None else staff is None
            if selected:
                yield measure.attrib.get("number", ""), onset, duration, child


def parse_guitar_musicxml(path: str | Path, family_id: str | None = None) -> ParsedSource:
    path = Path(path)
    raw = _read_bytes(path)
    digest = sha256(raw).hexdigest()
    source_id = digest[:24]
    family_id = family_id or source_id
    if not family_id or len(family_id) > 128 or any(ch.isspace() for ch in family_id):
        raise ValueError("family_id must be a non-empty whitespace-free identifier up to 128 characters")
    root = ET.fromstring(raw)
    if root.tag.split("}")[-1] != "score-partwise":
        raise ValueError("only score-partwise MusicXML is supported")
    selected_staff = _select_staff(root)
    tuning = _extract_tuning(root, selected_staff)
    software = root.findtext(".//software") or "unknown"
    version = root.attrib.get("version") or "1.0-unspecified"

    raw_notes = []
    diffs = []
    for measure, onset, duration, note in _iter_selected_notes(root, selected_staff):
        string_text = note.findtext(".//technical/string")
        fret_text = note.findtext(".//technical/fret")
        pitch = note.find("pitch")
        if pitch is None or string_text is None or fret_text is None:
            continue
        string_no = int(string_text)
        fret = int(fret_text)
        if not 1 <= string_no <= len(tuning):
            raise ValueError("technical string outside tuning")
        if not 0 <= fret <= MAX_FRET:
            raise ValueError("fret outside supported range 0..24")
        xml_midi = pitch_to_midi(
            pitch.findtext("step") or "",
            pitch.findtext("octave") or "",
            pitch.findtext("alter"),
        )
        physical = tuning[string_no - 1] + fret
        diffs.append(xml_midi - physical)
        raw_notes.append((measure, onset, duration, note.findtext("voice") or "1", xml_midi, physical, string_no, fret))
    if not raw_notes:
        raise ValueError("no complete pitch/string/fret labels")
    unique_diffs = set(diffs)
    if unique_diffs == {0}:
        pitch_mode = "sounding_exact"
    elif unique_diffs == {12}:
        pitch_mode = "written_octave_plus_12"
    else:
        raise ValueError(f"unresolved XML-vs-physical pitch relation: {sorted(unique_diffs)}")

    grouped: dict[tuple[str, int, str], list[tuple[int, int, int, int]]] = {}
    durations: dict[tuple[str, int, str], int] = {}
    for measure, onset, duration, voice, xml_midi, physical, string_no, fret in raw_notes:
        key = (measure, onset, voice)
        grouped.setdefault(key, []).append((xml_midi, physical, string_no, fret))
        durations[key] = max(durations.get(key, 0), duration)

    events = []
    for (measure, onset, voice), items in grouped.items():
        raw_placements = [
            Placement(sounding_midi=physical, xml_midi=xml_midi, string=string_no, fret=fret)
            for xml_midi, physical, string_no, fret in items
        ]
        placements = tuple(dict.fromkeys(raw_placements))
        if len({p.string for p in placements}) != len(placements):
            raise ValueError("simultaneous event reuses one technical string with conflicting placement")
        events.append(
            GuitarEvent(
                family_id=family_id,
                source_sha256=digest,
                musicxml_version=version,
                software=software,
                pitch_mode=pitch_mode,
                tuning=tuning,
                measure=measure,
                onset=onset,
                duration=durations[(measure, onset, voice)],
                voice=voice,
                placements=placements,
            )
        )
    events.sort(key=lambda e: (int(e.measure) if e.measure.isdigit() else 10**9, e.measure, e.onset, e.voice))
    return ParsedSource(
        family_id=family_id,
        source_sha256=digest,
        musicxml_version=version,
        software=software,
        pitch_mode=pitch_mode,
        tuning=tuning,
        selected_staff=selected_staff,
        events=tuple(events),
    )
