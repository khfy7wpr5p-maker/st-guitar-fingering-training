from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request

from st_guitar_fingering_training.s2a_batch import (
    batch_summary,
    build_event_packages,
    render_teacher_html,
    select_balanced_batch,
    split_sessions,
)
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml


ANIMETAB_COMMIT = "18c0993cbe0a0948cbf0b7768bcb09ff81c23a9a"
EXPECTED_MANIFEST_SCHEMA = "st-guitar-stage7g-c-r1-animetab-batch01-manifest-v1"


def _download_source(item: dict, destination: Path) -> None:
    filename = str(item["filename"])
    encoded = urllib.parse.quote(filename, safe="")
    url = (
        "https://raw.githubusercontent.com/amamiya-yuuko/AnimeTAB/"
        + ANIMETAB_COMMIT
        + "/AnimeTAB/Entire%20songs/"
        + encoded
    )
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-s2a-batch01-v1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    digest = sha256(data).hexdigest()
    if digest != item["sha256"]:
        raise RuntimeError(f"STOP: pinned AnimeTAB source SHA drift: {filename}")
    destination.write_bytes(data)


def build(manifest_path: Path, output_dir: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != EXPECTED_MANIFEST_SCHEMA:
        raise RuntimeError("STOP: unexpected pinned AnimeTAB manifest schema")
    if manifest.get("family_count") != 40 or len(manifest.get("sources", [])) != 40:
        raise RuntimeError("STOP: S2-A Batch01 requires the exact pinned 40-family source set")
    if manifest.get("part_id") != "P1" or manifest.get("staff_id") != "2":
        raise RuntimeError("STOP: pinned AnimeTAB part/staff selection drift")
    if manifest.get("pitch_mode") != "sounding_exact":
        raise RuntimeError("STOP: pinned AnimeTAB pitch mode drift")
    if manifest.get("tuning_midi") != [64, 59, 55, 50, 45, 40]:
        raise RuntimeError("STOP: pinned AnimeTAB tuning drift")

    sources = []
    with TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for index, item in enumerate(manifest["sources"], start=1):
            local = temp_root / f"{index:03d}.xml"
            _download_source(item, local)
            source = parse_target_free_musicxml(
                local,
                family_id=item["family_id"],
                tuning=manifest["tuning_midi"],
                pitch_mode=manifest["pitch_mode"],
                part_id=manifest["part_id"],
                staff_id=manifest["staff_id"],
            )
            if source.source_sha256 != item["sha256"]:
                raise RuntimeError("STOP: parsed source identity drift")
            sources.append(source)

    event_packages = build_event_packages(sources)
    selected = select_balanced_batch(event_packages)
    sessions = split_sessions(selected)
    summary = batch_summary(selected, sessions)
    summary.update(
        {
            "source_dataset": "AnimeTAB",
            "source_commit": ANIMETAB_COMMIT,
            "source_manifest_path": str(manifest_path),
            "source_manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
            "raw_source_bytes_retained": False,
            "license_claim_from_pinned_manifest": manifest.get("license_claim_from_supplied_readme"),
            "commercial_or_production_rights_verified": manifest.get("commercial_or_production_rights_verified"),
            "research_only_until_rights_review": True,
            "eligible_event_package_count": len(event_packages),
        }
    )

    teacher_dir = output_dir / "teacher"
    internal_dir = output_dir / "internal"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

    for index, (teacher_manifest, audit) in enumerate(sessions, start=1):
        stem = f"ST_Guitar_S2A_Batch01_Session{index:02d}"
        (teacher_dir / f"{stem}.html").write_text(
            render_teacher_html(teacher_manifest), encoding="utf-8"
        )
        (teacher_dir / f"{stem}_manifest.json").write_text(
            json.dumps(teacher_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (internal_dir / f"{stem}_audit.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    (internal_dir / "ST_Guitar_S2A_Batch01_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the pinned S2-A Batch01 blind Teacher package")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evidence/stage7g_c_r1_animetab_batch01_manifest.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build(args.manifest, args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
