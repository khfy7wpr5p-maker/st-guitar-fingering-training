from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from defusedxml import ElementTree as ET

from .mxl_target_free import read_mxl_musicxml_bytes


STANDARD_TUNING_MIDI = (64, 59, 55, 50, 45, 40)
PITCH_MODE = "sounding_exact"


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _staff_text(note: ET.Element) -> str | None:
    for child in list(note):
        if _local_name(child.tag) == "staff" and child.text:
            value = child.text.strip()
            return value or None
    return None


@dataclass(frozen=True)
class PartStaffSelection:
    source_sha256: str
    part_id: str
    staff_id: str | None
    selected_part_pitched_notes: int
    selected_staff_pitched_notes: int
    part_pitched_note_counts: tuple[tuple[str, int], ...]
    selected_part_staff_pitched_note_counts: tuple[tuple[str, int], ...]
    selected_part_unstaffed_pitched_notes: int

    def as_dict(self) -> dict:
        return {
            "source_sha256": self.source_sha256,
            "part_id": self.part_id,
            "staff_id": self.staff_id,
            "selected_part_pitched_notes": self.selected_part_pitched_notes,
            "selected_staff_pitched_notes": self.selected_staff_pitched_notes,
            "part_pitched_note_counts": [
                {"part_id": part_id, "pitched_notes": count}
                for part_id, count in self.part_pitched_note_counts
            ],
            "selected_part_staff_pitched_note_counts": [
                {"staff_id": staff_id, "pitched_notes": count}
                for staff_id, count in self.selected_part_staff_pitched_note_counts
            ],
            "selected_part_unstaffed_pitched_notes": self.selected_part_unstaffed_pitched_notes,
        }


def select_target_free_part_staff(path: str | Path) -> PartStaffSelection:
    """Freeze E3-E part/staff choice from source structure only.

    The selector is deliberately independent of physical candidates, specialist
    scores, router outputs, Teacher-GOLD, and any evaluation target.

    Rules:
    1. Count non-grace pitched notes in each MusicXML part.
    2. Select the part with the highest count; break ties by lexical part id.
    3. Within that part, if pitched notes have explicit staff ids, require every
       counted pitched note to have one, then select the staff with the highest
       count; break ties by lexical staff id.
    4. If no counted pitched note has an explicit staff id, select staff_id=None.
    5. Mixed explicit/unstaffed pitched-note notation fails closed rather than
       silently dropping one group.
    """

    outer, xml_bytes, _ = read_mxl_musicxml_bytes(path)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        raise ValueError("E3-E-A2 MXL rootfile is not valid XML") from exc
    if _local_name(root.tag) != "score-partwise":
        raise ValueError("E3-E-A2 supports score-partwise MXL only")

    parts = _children(root, "part")
    if not parts:
        raise ValueError("E3-E-A2 source has no MusicXML parts")

    part_rows: list[tuple[str, int, dict[str, int], int]] = []
    seen_ids: set[str] = set()
    for part in parts:
        part_id = part.attrib.get("id") or ""
        if not part_id or part_id in seen_ids:
            raise ValueError("E3-E-A2 parts require unique non-empty ids")
        seen_ids.add(part_id)

        pitched = 0
        staff_counts: dict[str, int] = {}
        unstaffed = 0
        for measure in _children(part, "measure"):
            for note in _children(measure, "note"):
                if _first_child(note, "grace") is not None:
                    continue
                if _first_child(note, "pitch") is None:
                    continue
                pitched += 1
                staff_id = _staff_text(note)
                if staff_id is None:
                    unstaffed += 1
                else:
                    staff_counts[staff_id] = staff_counts.get(staff_id, 0) + 1
        part_rows.append((part_id, pitched, staff_counts, unstaffed))

    selectable = [row for row in part_rows if row[1] > 0]
    if not selectable:
        raise ValueError("E3-E-A2 source has no non-grace pitched content")
    selected_part_id, selected_count, staff_counts, unstaffed = sorted(
        selectable,
        key=lambda row: (-row[1], row[0]),
    )[0]

    if staff_counts and unstaffed:
        raise ValueError(
            "E3-E-A2 selected part mixes explicit and missing staff ids on pitched notes"
        )
    if staff_counts:
        selected_staff, selected_staff_count = sorted(
            staff_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
    else:
        selected_staff = None
        selected_staff_count = selected_count

    return PartStaffSelection(
        source_sha256=sha256(outer).hexdigest(),
        part_id=selected_part_id,
        staff_id=selected_staff,
        selected_part_pitched_notes=selected_count,
        selected_staff_pitched_notes=selected_staff_count,
        part_pitched_note_counts=tuple((row[0], row[1]) for row in part_rows),
        selected_part_staff_pitched_note_counts=tuple(sorted(staff_counts.items())),
        selected_part_unstaffed_pitched_notes=unstaffed,
    )
