from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Iterable
import zipfile

from .intake import MAX_FRET

GUITARSET_OBSERVED_GOLD_VERSION = "GUITARSET-OBSERVED-GOLD.v1"
GUITARSET_STANDARD_TUNING_LOW_TO_HIGH = (40, 45, 50, 55, 59, 64)
STRUM_CLUSTER_WINDOW_SECONDS = 0.050

GS101_BAD_JAMS_SCHEMA = "GS101_BAD_JAMS_SCHEMA"
GS102_BAD_DATA_SOURCE = "GS102_BAD_DATA_SOURCE"
GS103_NONFINITE_NOTE = "GS103_NONFINITE_NOTE"
GS104_NEGATIVE_TIME_OR_DURATION = "GS104_NEGATIVE_TIME_OR_DURATION"
GS105_MIDI_OUT_OF_RANGE = "GS105_MIDI_OUT_OF_RANGE"
GS106_NEGATIVE_FRET = "GS106_NEGATIVE_FRET"
GS107_FRET_GT_MAX = "GS107_FRET_GT_MAX"


@dataclass(frozen=True)
class ObservedNoteGold:
    note_id: str
    source_member: str
    recording_id: str
    data_source: int
    string: int
    open_midi: int
    source_note_index: int
    onset_seconds: float
    duration_seconds: float
    raw_midi: float
    midi: int
    fret: int
    cents_error: float


@dataclass(frozen=True)
class QuarantinedNote:
    quarantine_id: str
    source_member: str
    recording_id: str
    data_source: int | None
    source_note_index: int | None
    reason_code: str
    raw: dict


@dataclass(frozen=True)
class DerivedStrumVoicingGold:
    voicing_id: str
    source_member: str
    recording_id: str
    anchor_onset_seconds: float
    onset_spread_seconds: float
    note_ids: tuple[str, ...]
    placements: tuple[tuple[int, int, int], ...]


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _recording_id(member: str) -> str:
    stem = Path(member).name
    if not stem.endswith("_comp.jams"):
        raise ValueError("GuitarSet observed-gold importer accepts *_comp.jams only")
    return stem[: -len("_comp.jams")]


def _data_source_to_string(data_source: int) -> tuple[int, int]:
    if data_source not in range(6):
        raise ValueError(GS102_BAD_DATA_SOURCE)
    open_midi = GUITARSET_STANDARD_TUNING_LOW_TO_HIGH[data_source]
    return 6 - data_source, open_midi


def _nearest_midi(value: float) -> int:
    return int(math.floor(value + 0.5))


def sanitize_note_row(
    *, source_member: str, data_source: int, source_note_index: int, row: dict
) -> ObservedNoteGold | QuarantinedNote:
    recording_id = _recording_id(source_member)
    raw_copy = dict(row) if isinstance(row, dict) else {"value": row}
    base = {
        "source_member": source_member,
        "data_source": data_source,
        "source_note_index": source_note_index,
        "raw": raw_copy,
    }
    try:
        string, open_midi = _data_source_to_string(int(data_source))
    except (TypeError, ValueError):
        return QuarantinedNote(
            f"guitarset-quarantine-sha256:{_canonical_sha256(base)}",
            source_member, recording_id, None, source_note_index,
            GS102_BAD_DATA_SOURCE, raw_copy,
        )
    try:
        onset = float(row["time"])
        duration = float(row["duration"])
        raw_midi = float(row["value"])
    except (KeyError, TypeError, ValueError):
        return QuarantinedNote(
            f"guitarset-quarantine-sha256:{_canonical_sha256(base)}",
            source_member, recording_id, data_source, source_note_index,
            GS101_BAD_JAMS_SCHEMA, raw_copy,
        )

    reason = None
    if not all(math.isfinite(value) for value in (onset, duration, raw_midi)):
        reason = GS103_NONFINITE_NOTE
    elif onset < 0 or duration < 0:
        reason = GS104_NEGATIVE_TIME_OR_DURATION
    elif raw_midi < 0 or raw_midi > 127:
        reason = GS105_MIDI_OUT_OF_RANGE
    else:
        midi = _nearest_midi(raw_midi)
        fret = midi - open_midi
        if fret < 0:
            reason = GS106_NEGATIVE_FRET
        elif fret > MAX_FRET:
            reason = GS107_FRET_GT_MAX
        else:
            identity = {
                "source_member": source_member,
                "data_source": data_source,
                "source_note_index": source_note_index,
                "time": onset,
                "duration": duration,
                "raw_midi": raw_midi,
            }
            return ObservedNoteGold(
                note_id=f"guitarset-note-sha256:{_canonical_sha256(identity)}",
                source_member=source_member,
                recording_id=recording_id,
                data_source=data_source,
                string=string,
                open_midi=open_midi,
                source_note_index=source_note_index,
                onset_seconds=onset,
                duration_seconds=duration,
                raw_midi=raw_midi,
                midi=midi,
                fret=fret,
                cents_error=abs(raw_midi - midi) * 100.0,
            )

    return QuarantinedNote(
        f"guitarset-quarantine-sha256:{_canonical_sha256(base)}",
        source_member, recording_id, data_source, source_note_index,
        reason, raw_copy,
    )


def extract_comp_jams(
    source_member: str, raw_jams: bytes
) -> tuple[tuple[ObservedNoteGold, ...], tuple[QuarantinedNote, ...]]:
    try:
        payload = json.loads(raw_jams.decode("utf-8"))
        annotations = payload["annotations"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        raise ValueError(GS101_BAD_JAMS_SCHEMA)
    if not isinstance(annotations, list):
        raise ValueError(GS101_BAD_JAMS_SCHEMA)

    by_source: dict[int, dict] = {}
    for annotation in annotations:
        if not isinstance(annotation, dict) or annotation.get("namespace") != "note_midi":
            continue
        try:
            data_source = int(annotation["annotation_metadata"]["data_source"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(GS102_BAD_DATA_SOURCE)
        if data_source in by_source:
            raise ValueError(f"{GS102_BAD_DATA_SOURCE}: duplicate data_source={data_source}")
        by_source[data_source] = annotation
    if set(by_source) != set(range(6)):
        raise ValueError(f"{GS102_BAD_DATA_SOURCE}: expected data_source 0..5, got {sorted(by_source)}")

    accepted: list[ObservedNoteGold] = []
    quarantined: list[QuarantinedNote] = []
    for data_source in range(6):
        rows = by_source[data_source].get("data")
        if not isinstance(rows, list):
            raise ValueError(GS101_BAD_JAMS_SCHEMA)
        for index, row in enumerate(rows):
            result = sanitize_note_row(
                source_member=source_member,
                data_source=data_source,
                source_note_index=index,
                row=row,
            )
            (accepted if isinstance(result, ObservedNoteGold) else quarantined).append(result)
    accepted.sort(key=lambda x: (x.onset_seconds, x.string, x.source_note_index, x.note_id))
    quarantined.sort(key=lambda x: (x.data_source if x.data_source is not None else 99, x.source_note_index or -1, x.quarantine_id))
    return tuple(accepted), tuple(quarantined)


def derive_strum_voicings(
    notes: Iterable[ObservedNoteGold], *, window_seconds: float = STRUM_CLUSTER_WINDOW_SECONDS
) -> tuple[DerivedStrumVoicingGold, ...]:
    if not 0 < window_seconds <= 0.250:
        raise ValueError("strum window must be in (0, 0.250] seconds")
    ordered = tuple(sorted(notes, key=lambda x: (x.source_member, x.onset_seconds, x.string, x.note_id)))
    by_source: dict[str, list[ObservedNoteGold]] = {}
    for note in ordered:
        by_source.setdefault(note.source_member, []).append(note)

    out: list[DerivedStrumVoicingGold] = []
    for source_member, source_notes in sorted(by_source.items()):
        used: set[int] = set()
        for i, anchor in enumerate(source_notes):
            if i in used:
                continue
            candidates: list[tuple[int, ObservedNoteGold]] = []
            window_indices: list[int] = []
            seen_strings: set[int] = set()
            duplicate_string = False
            j = i
            while j < len(source_notes) and source_notes[j].onset_seconds - anchor.onset_seconds <= window_seconds + 1e-12:
                if j not in used:
                    window_indices.append(j)
                    note = source_notes[j]
                    if note.string in seen_strings:
                        duplicate_string = True
                    else:
                        seen_strings.add(note.string)
                        candidates.append((j, note))
                j += 1
            if duplicate_string:
                used.update(window_indices)
                continue
            if len(candidates) < 2:
                used.add(i)
                continue
            for index, _ in candidates:
                used.add(index)
            cluster = tuple(note for _, note in candidates)
            placements = tuple(sorted((note.midi, note.string, note.fret) for note in cluster))
            if len({string for _, string, _ in placements}) != len(placements):
                raise AssertionError("derived strum voicing reuses a string")
            for midi, string, fret in placements:
                open_midi = GUITARSET_STANDARD_TUNING_LOW_TO_HIGH[6 - string]
                if midi != open_midi + fret:
                    raise AssertionError("derived strum voicing violates physical pitch/string/fret relation")
            note_ids = tuple(sorted(note.note_id for note in cluster))
            identity = {
                "source_member": source_member,
                "note_ids": note_ids,
                "placements": placements,
                "window_seconds": window_seconds,
            }
            out.append(DerivedStrumVoicingGold(
                voicing_id=f"guitarset-voicing-sha256:{_canonical_sha256(identity)}",
                source_member=source_member,
                recording_id=anchor.recording_id,
                anchor_onset_seconds=min(note.onset_seconds for note in cluster),
                onset_spread_seconds=max(note.onset_seconds for note in cluster) - min(note.onset_seconds for note in cluster),
                note_ids=note_ids,
                placements=placements,
            ))
    out.sort(key=lambda x: (x.source_member, x.anchor_onset_seconds, x.voicing_id))
    if len({x.voicing_id for x in out}) != len(out):
        raise AssertionError("duplicate GuitarSet derived voicing IDs")
    return tuple(out)


def archive_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_guitarset_comp_archive(path: str | Path):
    path = Path(path)
    accepted: list[ObservedNoteGold] = []
    quarantined: list[QuarantinedNote] = []
    with zipfile.ZipFile(path) as archive:
        members = sorted(
            name for name in archive.namelist()
            if name.startswith("annotation/") and name.endswith("_comp.jams") and "/._" not in name
        )
        if not members:
            raise ValueError("archive contains no annotation/*_comp.jams members")
        if len(members) != len(set(members)):
            raise ValueError("duplicate comp member names")
        for member in members:
            notes, rejects = extract_comp_jams(member, archive.read(member))
            accepted.extend(notes)
            quarantined.extend(rejects)
    return tuple(accepted), tuple(quarantined), derive_strum_voicings(accepted)


def build_manifest(path: str | Path, notes, quarantined, voicings) -> dict:
    from collections import Counter

    reasons = Counter(item.reason_code for item in quarantined)
    members = sorted({x.source_member for x in notes} | {x.source_member for x in quarantined})
    performers = sorted({Path(x).name.split("_", 1)[0] for x in members})
    styles = sorted({Path(x).name.split("_", 2)[1].split("-", 1)[0] for x in members})
    frets = [x.fret for x in notes]
    cents = [x.cents_error for x in notes]
    return {
        "schema": "st-guitar-guitarset-observed-gold-manifest-v1",
        "version": GUITARSET_OBSERVED_GOLD_VERSION,
        "source_archive_sha256": archive_sha256(path),
        "source_archive_name": Path(path).name,
        "source_role": "OBSERVED_GUITARIST_GOLD",
        "comp_recording_count": len(members),
        "performer_count": len(performers),
        "style_count": len(styles),
        "accepted_note_count": len(notes),
        "quarantined_note_count": len(quarantined),
        "quarantine_reason_counts": dict(sorted(reasons.items())),
        "accepted_fret_min": min(frets) if frets else None,
        "accepted_fret_max": max(frets) if frets else None,
        "accepted_cents_error_max": max(cents) if cents else None,
        "derived_strum_voicing_count": len(voicings),
        "strum_cluster_window_seconds": STRUM_CLUSTER_WINDOW_SECONDS,
        "note_gold_semantics": "DIRECT_STRING_SPECIFIC_NOTE_OBSERVATION_AFTER_DETERMINISTIC_SANITIZATION",
        "voicing_gold_semantics": "DERIVED_DISTINCT_STRING_ONSET_CLUSTER_FROM_ACCEPTED_NOTE_GOLD",
        "left_hand_finger_labels_present": False,
        "barre_labels_present": False,
        "training_authorized": False,
        "next_gate": "SPLIT_AND_LEAKAGE_CONTRACT",
    }
