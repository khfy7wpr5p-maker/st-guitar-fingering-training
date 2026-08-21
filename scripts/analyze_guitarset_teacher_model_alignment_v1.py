from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_teacher_model_alignment import (
    analyze_teacher_model_alignment,
)


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"STOP: cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"STOP: expected JSON object in {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare blinded Teacher choices with GuitarSet observed DEVELOPMENT voicings "
            "and the sealed DEVELOPMENT model without opening validation/final data."
        )
    )
    parser.add_argument("--choices", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--internal-audit", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    choices_bytes = args.choices.read_bytes()
    report = analyze_teacher_model_alignment(
        choices=_read_json(args.choices),
        choices_sha256=sha256(choices_bytes).hexdigest(),
        manifest=_read_json(args.manifest),
        internal_audit=_read_json(args.internal_audit),
        model_artifact=_read_json(args.model_artifact),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
