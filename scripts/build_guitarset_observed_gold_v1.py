from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_observed_gold import (
    build_manifest,
    import_guitarset_comp_archive,
)


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    archive = Path(args.archive)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    notes, quarantined, voicings = import_guitarset_comp_archive(archive)
    manifest = build_manifest(archive, notes, quarantined, voicings)

    _write_jsonl(output / "guitarset_comp_note_gold_v1.jsonl", notes)
    _write_jsonl(output / "guitarset_comp_quarantine_v1.jsonl", quarantined)
    _write_jsonl(output / "guitarset_comp_voicing_gold_v1.jsonl", voicings)
    (output / "guitarset_comp_observed_gold_manifest_v1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
