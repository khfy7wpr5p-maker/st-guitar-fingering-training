from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from .dataset import Voicing, valid_chord_voicings

STANDARD_TUNING: tuple[int, ...] = (64, 59, 55, 50, 45, 40)
SYNTHETIC_LABEL = "RULE_PREFERRED"
PROVENANCE = "synthetic-rule-v1"
MAX_SYNTH_FRET = 12

_MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
_QUALITY_INTERVALS = {
    0: (0, 4, 7),
    1: (0, 3, 7),
    2: (0, 3, 7),
    3: (0, 4, 7),
    4: (0, 4, 7),
    5: (0, 3, 7),
    6: (0, 3, 6),
}
_PROGRESSIONS = (
    (0, 4, 5, 3),  # I-V-vi-IV
    (0, 5, 3, 4),  # I-vi-IV-V
    (1, 4, 0, 5),  # ii-V-I-vi
    (0, 3, 4, 0),  # I-IV-V-I
    (5, 3, 0, 4),  # vi-IV-I-V
)
_STYLES = ("open_low", "compact", "mid_position", "high_position", "common_tone")
_PC_TO_NAME = (
    ("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0),
)


@dataclass(frozen=True)
class SyntheticChordEvent:
    index: int
    degree: int
    pitches_midi: tuple[int, ...]
    preferred: Voicing
    candidate_count: int
    rule_id: str


@dataclass(frozen=True)
class SyntheticFamily:
    family_id: str
    key_pc: int
    style: str
    progression: tuple[int, ...]
    tuning: tuple[int, ...]
    events: tuple[SyntheticChordEvent, ...]
    label_class: str = SYNTHETIC_LABEL
    provenance: str = PROVENANCE
    teacher_gold: bool = False


def _center(voicing: Voicing) -> float:
    frets = [fret for _, _, fret in voicing]
    return sum(frets) / len(frets)


def _rule_key(voicing: Voicing, style: str, previous: Voicing | None) -> tuple:
    frets = [fret for _, _, fret in voicing]
    strings = {string for _, string, _ in voicing}
    span = max(frets) - min(frets)
    total = sum(frets)
    opens = sum(fret == 0 for fret in frets)
    center = _center(voicing)

    if style == "open_low":
        return (-opens, total, max(frets), span, tuple(voicing))
    if style == "compact":
        return (span, total, max(frets), -opens, tuple(voicing))
    if style == "mid_position":
        return (abs(center - 5.0), span, opens, total, tuple(voicing))
    if style == "high_position":
        return (abs(center - 9.0), span, opens, total, tuple(voicing))
    if style == "common_tone":
        if previous is None:
            return (span, total, max(frets), -opens, tuple(voicing))
        shared_pitch_string = len({(p, s) for p, s, _ in voicing} & {(p, s) for p, s, _ in previous})
        overlap = len(strings & {s for _, s, _ in previous})
        return (-shared_pitch_string, abs(center - _center(previous)), -overlap, span, total, tuple(voicing))
    raise ValueError(f"unknown synthetic style: {style}")


def _apply_inversion(root: int, intervals: tuple[int, ...], inversion: int) -> tuple[int, ...]:
    tones = [root + interval for interval in intervals]
    if inversion == 1:
        tones = [tones[1], tones[2], tones[0] + 12]
    elif inversion == 2:
        tones = [tones[2], tones[0] + 12, tones[1] + 12]
    elif inversion != 0:
        raise ValueError("triad inversion must be 0, 1, or 2")
    return tuple(sorted(tones))


def _best_pitch_register(key_pc: int, degree: int, inversion: int) -> tuple[tuple[int, ...], tuple[Voicing, ...]]:
    root_pc = (key_pc + _MAJOR_SCALE[degree]) % 12
    best: tuple[int, float, tuple[int, ...], tuple[Voicing, ...]] | None = None
    for root in range(40, 61):
        if root % 12 != root_pc:
            continue
        pitches = _apply_inversion(root, _QUALITY_INTERVALS[degree], inversion)
        candidates = tuple(
            voicing for voicing in valid_chord_voicings(pitches, STANDARD_TUNING)
            if max(fret for _, _, fret in voicing) <= MAX_SYNTH_FRET
        )
        if not candidates:
            continue
        center_penalty = abs(sum(pitches) / len(pitches) - 58.0)
        score = (len(candidates), -center_penalty, pitches, candidates)
        if best is None or score[:2] > best[:2]:
            best = score
    if best is None:
        raise ValueError("unable to construct physically valid synthetic chord")
    return best[2], best[3]


def generate_synthetic_family(family_index: int, events_per_family: int = 24) -> SyntheticFamily:
    if family_index < 0:
        raise ValueError("family_index must be non-negative")
    if not 4 <= events_per_family <= 64:
        raise ValueError("events_per_family must be within 4..64")

    key_pc = family_index % 12
    style = _STYLES[(family_index // 12) % len(_STYLES)]
    progression = _PROGRESSIONS[(family_index // (12 * len(_STYLES))) % len(_PROGRESSIONS)]
    family_id = f"synth_v1_{family_index:04d}_{style}_k{key_pc:02d}"

    events: list[SyntheticChordEvent] = []
    previous: Voicing | None = None
    for index in range(events_per_family):
        degree = progression[index % len(progression)]
        cycle = index // len(progression)
        if style == "open_low":
            inversion = 0
        elif style == "common_tone":
            inversion = (cycle + (index % len(progression))) % 3
        else:
            inversion = (cycle + family_index + index) % 3

        pitches, candidates = _best_pitch_register(key_pc, degree, inversion)
        preferred = min(candidates, key=lambda candidate: _rule_key(candidate, style, previous))
        events.append(SyntheticChordEvent(
            index=index,
            degree=degree,
            pitches_midi=pitches,
            preferred=preferred,
            candidate_count=len(candidates),
            rule_id=f"synthetic-v1:{style}",
        ))
        previous = preferred

    return SyntheticFamily(
        family_id=family_id,
        key_pc=key_pc,
        style=style,
        progression=progression,
        tuning=STANDARD_TUNING,
        events=tuple(events),
    )


def _midi_pitch(midi: int) -> tuple[str, int, int]:
    if not 0 <= midi <= 127:
        raise ValueError("MIDI pitch outside 0..127")
    step, alter = _PC_TO_NAME[midi % 12]
    octave = midi // 12 - 1
    return step, alter, octave


def _append_pitch(parent: ET.Element, midi: int) -> None:
    step, alter, octave = _midi_pitch(midi)
    pitch = ET.SubElement(parent, "pitch")
    ET.SubElement(pitch, "step").text = step
    if alter:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = str(octave)


def family_to_musicxml(family: SyntheticFamily) -> str:
    root = ET.Element("score-partwise", version="3.1")
    identification = ET.SubElement(root, "identification")
    encoding = ET.SubElement(identification, "encoding")
    ET.SubElement(encoding, "software").text = "ST-Guitar-Synthetic-v1"
    misc = ET.SubElement(identification, "miscellaneous")
    ET.SubElement(misc, "miscellaneous-field", name="family-id").text = family.family_id
    ET.SubElement(misc, "miscellaneous-field", name="label-class").text = family.label_class
    ET.SubElement(misc, "miscellaneous-field", name="provenance").text = family.provenance
    ET.SubElement(misc, "miscellaneous-field", name="teacher-gold").text = "false"

    part_list = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Synthetic Guitar"
    part = ET.SubElement(root, "part", id="P1")

    for event in family.events:
        measure = ET.SubElement(part, "measure", number=str(event.index + 1))
        if event.index == 0:
            attributes = ET.SubElement(measure, "attributes")
            ET.SubElement(attributes, "divisions").text = "1"
            time = ET.SubElement(attributes, "time")
            ET.SubElement(time, "beats").text = "4"
            ET.SubElement(time, "beat-type").text = "4"
            ET.SubElement(attributes, "staves").text = "1"
            clef = ET.SubElement(attributes, "clef", number="1")
            ET.SubElement(clef, "sign").text = "TAB"
            ET.SubElement(clef, "line").text = "5"
            details = ET.SubElement(attributes, "staff-details", number="1")
            ET.SubElement(details, "staff-lines").text = "6"
            low_to_high = tuple(reversed(family.tuning))
            for line, midi in enumerate(low_to_high, start=1):
                step, alter, octave = _midi_pitch(midi)
                tuning = ET.SubElement(details, "staff-tuning", line=str(line))
                ET.SubElement(tuning, "tuning-step").text = step
                if alter:
                    ET.SubElement(tuning, "tuning-alter").text = str(alter)
                ET.SubElement(tuning, "tuning-octave").text = str(octave)

        for note_index, (pitch_midi, string, fret) in enumerate(event.preferred):
            note = ET.SubElement(measure, "note")
            if note_index:
                ET.SubElement(note, "chord")
            _append_pitch(note, pitch_midi)
            ET.SubElement(note, "duration").text = "4"
            ET.SubElement(note, "voice").text = "1"
            ET.SubElement(note, "type").text = "whole"
            ET.SubElement(note, "staff").text = "1"
            notations = ET.SubElement(note, "notations")
            technical = ET.SubElement(notations, "technical")
            ET.SubElement(technical, "string").text = str(string)
            ET.SubElement(technical, "fret").text = str(fret)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def generate_synthetic_corpus(output_dir: str | Path, families: int = 100, events_per_family: int = 24) -> dict:
    if not 1 <= families <= 10000:
        raise ValueError("families must be within 1..10000")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    family_map: dict[str, str] = {}
    manifest_path = output / "synthetic_manifest.jsonl"
    candidate_counts: list[int] = []
    style_counts: dict[str, int] = {}

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for family_index in range(families):
            family = generate_synthetic_family(family_index, events_per_family=events_per_family)
            filename = f"{family.family_id}.xml"
            (output / filename).write_text(family_to_musicxml(family), encoding="utf-8")
            family_map[filename] = family.family_id
            style_counts[family.style] = style_counts.get(family.style, 0) + 1
            for event in family.events:
                candidate_counts.append(event.candidate_count)
                manifest.write(json.dumps({
                    "family_id": family.family_id,
                    "event_index": event.index,
                    "key_pc": family.key_pc,
                    "style": family.style,
                    "degree": event.degree,
                    "pitches_midi": event.pitches_midi,
                    "preferred": event.preferred,
                    "candidate_count": event.candidate_count,
                    "label_class": family.label_class,
                    "rule_id": event.rule_id,
                    "provenance": family.provenance,
                    "teacher_gold": False,
                }, sort_keys=True) + "\n")

    (output / "family_map.json").write_text(json.dumps(family_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema": "st-guitar-synthetic-corpus-v1",
        "families": families,
        "events_per_family": events_per_family,
        "events": families * events_per_family,
        "label_class": SYNTHETIC_LABEL,
        "teacher_gold": False,
        "provenance": PROVENANCE,
        "max_synthetic_fret": MAX_SYNTH_FRET,
        "styles": style_counts,
        "candidate_count_min": min(candidate_counts),
        "candidate_count_max": max(candidate_counts),
        "candidate_count_mean": sum(candidate_counts) / len(candidate_counts),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
