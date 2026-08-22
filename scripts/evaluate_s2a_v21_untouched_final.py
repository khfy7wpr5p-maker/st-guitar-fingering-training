from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.s2a_v21_recovery import evaluate_untouched_final_recovery


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
        description="Evaluate the once-opened S2-A.v2 FINAL export against an already sealed v2.1 model."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--internal-audit", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--final-choices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = evaluate_untouched_final_recovery(
        _read_json(args.manifest),
        _read_json(args.internal_audit),
        _read_json(args.final_choices),
        _read_json(args.model_artifact),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "result_sha256": result["result_sha256"],
        "checkpoint_retention_eligibility": result["checkpoint_retention_eligibility"],
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
