from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.s2a_v21_recovery import fit_and_seal_development_recovery


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
        description="Fit and seal S2-A.v2.1 from DEVELOPMENT only. This command never reads FINAL."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--internal-audit", type=Path, required=True)
    parser.add_argument("--development-choices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact = fit_and_seal_development_recovery(
        _read_json(args.manifest),
        _read_json(args.internal_audit),
        _read_json(args.development_choices),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": artifact["status"],
        "artifact_sha256": artifact["artifact_sha256"],
        "training_task_count": artifact["training_task_count"],
        "training_constraint_count": artifact["training_constraint_count"],
        "final_access_authorized": artifact["final_access_authorized"],
        "final_access_count_authorized": artifact["final_access_count_authorized"],
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
