from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile, ZipInfo

from defusedxml import ElementTree as ET

from .intake import MAX_SOURCE_BYTES
from .target_free_musicxml import TargetFreeSource, parse_target_free_musicxml


MXL_CONTAINER_PATH = "META-INF/container.xml"
MAX_MXL_MEMBERS = 128
MAX_MXL_CONTAINER_BYTES = 256 * 1024
MAX_MXL_TOTAL_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_MXL_COMPRESSION_RATIO = 200.0


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _read_outer_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"MXL source byte size outside allowed range: {size}")
    return path.read_bytes()


def _validate_member_name(name: str) -> str:
    if not name or "\x00" in name or "\\" in name:
        raise ValueError("MXL archive member name is invalid")
    value = PurePosixPath(name)
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("MXL archive member path traversal is forbidden")
    normalized = str(value)
    if normalized in ("", ".") or normalized != name.rstrip("/"):
        raise ValueError("MXL archive member path must be normalized POSIX relative path")
    return normalized


def _validate_member(info: ZipInfo) -> None:
    _validate_member_name(info.filename)
    if info.flag_bits & 0x1:
        raise ValueError("encrypted MXL archive members are forbidden")
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and stat.S_ISLNK(mode):
        raise ValueError("symlink MXL archive members are forbidden")
    if info.file_size < 0 or info.file_size > MAX_SOURCE_BYTES:
        raise ValueError("MXL archive member size is outside the allowed bound")
    if info.file_size > 0:
        if info.compress_size <= 0:
            raise ValueError("MXL archive member has invalid compressed size")
        if info.file_size / info.compress_size > MAX_MXL_COMPRESSION_RATIO:
            raise ValueError("MXL archive member compression ratio exceeds the safety bound")


def _container_rootfile(container_bytes: bytes) -> str:
    if not container_bytes or len(container_bytes) > MAX_MXL_CONTAINER_BYTES:
        raise ValueError("MXL container.xml size is outside the allowed bound")
    try:
        root = ET.fromstring(container_bytes)
    except Exception as exc:
        raise ValueError("MXL container.xml is not valid XML") from exc
    rootfiles = []
    for element in root.iter():
        if _local_name(element.tag) != "rootfile":
            continue
        full_path = element.attrib.get("full-path")
        if full_path:
            rootfiles.append(_validate_member_name(full_path))
    if len(rootfiles) != 1:
        raise ValueError("MXL container.xml must declare exactly one rootfile")
    return rootfiles[0]


def read_mxl_musicxml_bytes(path: str | Path) -> tuple[bytes, bytes, str]:
    """Read one compressed MusicXML document without extracting archive paths.

    The returned source bytes are the exact outer MXL bytes used for source SHA-256
    identity. Only the declared container rootfile is returned as MusicXML payload.
    """

    source_path = Path(path)
    outer = _read_outer_bytes(source_path)
    try:
        with ZipFile(BytesIO(outer), "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_MXL_MEMBERS:
                raise ValueError("MXL archive member count is outside the allowed bound")

            by_name: dict[str, ZipInfo] = {}
            total_uncompressed = 0
            for info in infos:
                _validate_member(info)
                normalized = _validate_member_name(info.filename)
                if normalized in by_name:
                    raise ValueError("duplicate normalized MXL archive member name")
                by_name[normalized] = info
                if not info.is_dir():
                    total_uncompressed += info.file_size
                    if total_uncompressed > MAX_MXL_TOTAL_UNCOMPRESSED_BYTES:
                        raise ValueError("MXL archive total uncompressed payload exceeds the safety bound")

            container_info = by_name.get(MXL_CONTAINER_PATH)
            if container_info is None or container_info.is_dir():
                raise ValueError("MXL archive is missing META-INF/container.xml")
            if container_info.file_size > MAX_MXL_CONTAINER_BYTES:
                raise ValueError("MXL container.xml exceeds the safety bound")
            container_bytes = archive.read(container_info)
            if len(container_bytes) != container_info.file_size:
                raise ValueError("MXL container.xml byte-size mismatch")

            rootfile_path = _container_rootfile(container_bytes)
            rootfile_info = by_name.get(rootfile_path)
            if rootfile_info is None or rootfile_info.is_dir():
                raise ValueError("MXL declared rootfile is missing from the archive")
            if rootfile_info.file_size <= 0 or rootfile_info.file_size > MAX_SOURCE_BYTES:
                raise ValueError("MXL MusicXML rootfile size is outside the allowed bound")
            xml_bytes = archive.read(rootfile_info)
            if len(xml_bytes) != rootfile_info.file_size:
                raise ValueError("MXL MusicXML rootfile byte-size mismatch")
    except (BadZipFile, RuntimeError) as exc:
        raise ValueError("source is not a readable MXL ZIP archive") from exc

    return outer, xml_bytes, rootfile_path


@dataclass(frozen=True)
class MxlStructureAudit:
    source_sha256: str
    rootfile_path: str
    musicxml_version: str
    software: str
    part_ids: tuple[str, ...]
    staff_ids_by_part: tuple[tuple[str, tuple[str, ...]], ...]
    pitched_notes_by_part: tuple[tuple[str, int], ...]
    technical_string_or_fret_elements: int

    def as_dict(self) -> dict:
        return {
            "source_sha256": self.source_sha256,
            "rootfile_path": self.rootfile_path,
            "musicxml_version": self.musicxml_version,
            "software": self.software,
            "part_ids": list(self.part_ids),
            "staff_ids_by_part": [
                {"part_id": part_id, "staff_ids": list(staff_ids)}
                for part_id, staff_ids in self.staff_ids_by_part
            ],
            "pitched_notes_by_part": [
                {"part_id": part_id, "pitched_notes": count}
                for part_id, count in self.pitched_notes_by_part
            ],
            "technical_string_or_fret_elements": self.technical_string_or_fret_elements,
        }


def inspect_target_free_mxl(path: str | Path) -> MxlStructureAudit:
    """Inspect only source structure/provenance-relevant metadata, never preferences."""

    outer, xml_bytes, rootfile_path = read_mxl_musicxml_bytes(path)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        raise ValueError("MXL rootfile is not valid MusicXML XML") from exc
    if _local_name(root.tag) != "score-partwise":
        raise ValueError("Stage 7G-E3-E A1 supports score-partwise MXL only")

    part_rows: list[tuple[str, tuple[str, ...]]] = []
    note_rows: list[tuple[str, int]] = []
    part_ids: list[str] = []
    for part in (element for element in list(root) if _local_name(element.tag) == "part"):
        part_id = part.attrib.get("id") or ""
        if not part_id or part_id in part_ids:
            raise ValueError("MXL MusicXML parts require unique non-empty ids")
        part_ids.append(part_id)
        staffs: set[str] = set()
        pitched = 0
        for element in part.iter():
            if _local_name(element.tag) != "note":
                continue
            has_pitch = any(_local_name(child.tag) == "pitch" for child in list(element))
            if not has_pitch:
                continue
            pitched += 1
            for child in list(element):
                if _local_name(child.tag) == "staff" and child.text:
                    staffs.add(child.text.strip())
        part_rows.append((part_id, tuple(sorted(staffs))))
        note_rows.append((part_id, pitched))
    if not part_ids or not any(count > 0 for _, count in note_rows):
        raise ValueError("MXL MusicXML contains no pitched part content")

    software = "unknown"
    for element in root.iter():
        if _local_name(element.tag) == "software" and element.text:
            software = element.text.strip() or "unknown"
            break
    technical_count = sum(
        1 for element in root.iter() if _local_name(element.tag) in ("string", "fret")
    )
    return MxlStructureAudit(
        source_sha256=sha256(outer).hexdigest(),
        rootfile_path=rootfile_path,
        musicxml_version=root.attrib.get("version") or "1.0-unspecified",
        software=software,
        part_ids=tuple(part_ids),
        staff_ids_by_part=tuple(part_rows),
        pitched_notes_by_part=tuple(note_rows),
        technical_string_or_fret_elements=technical_count,
    )


def parse_target_free_mxl(
    path: str | Path,
    *,
    family_id: str,
    tuning,
    pitch_mode: str,
    part_id: str | None = None,
    staff_id: str | None = None,
) -> TargetFreeSource:
    """Parse compressed MusicXML through the existing target-free MusicXML contract.

    The inner XML is written to a fixed temporary filename, never to an archive path.
    Source identity remains the exact outer MXL SHA-256. Technical string/fret values
    are still ignored by `parse_target_free_musicxml`.
    """

    outer, xml_bytes, _ = read_mxl_musicxml_bytes(path)
    source_digest = sha256(outer).hexdigest()
    with TemporaryDirectory() as tmp:
        inner_path = Path(tmp) / "score.musicxml"
        inner_path.write_bytes(xml_bytes)
        parsed = parse_target_free_musicxml(
            inner_path,
            family_id=family_id,
            tuning=tuning,
            pitch_mode=pitch_mode,
            part_id=part_id,
            staff_id=staff_id,
        )
    events = tuple(replace(event, source_sha256=source_digest) for event in parsed.events)
    return replace(parsed, source_sha256=source_digest, events=events)
