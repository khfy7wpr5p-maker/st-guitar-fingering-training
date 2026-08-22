from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.s2a_v3_consensus_tournament import execute_after_teacher_session


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
            "Run S2-A.v3 consensus quarantine + DEVELOPMENT CV/seal first, then open/evaluate FINAL."
        )
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--internal-audit", type=Path, required=True)
    parser.add_argument("--development-choices", type=Path, required=True)
    parser.add_argument("--final-choices", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = _read_json(args.manifest)
    audit = _read_json(args.internal_audit)
    development = _read_json(args.development_choices)

    # FINAL is intentionally not read until execute_after_teacher_session has
    # passed DEVELOPMENT and sealed the v3 model.
    def load_final() -> dict:
        return _read_json(args.final_choices)

    model_artifact, final_result, execution = execute_after_teacher_session(
        manifest=manifest,
        internal_audit=audit,
        development_export=development,
        final_loader=load_final,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "ST_Guitar_S2A_V3_development_model.json"
    final_path = args.output_dir / "ST_Guitar_S2A_V3_untouched_final_result.json"
    execution_path = args.output_dir / "ST_Guitar_S2A_V3_execution_evidence.json"
    model_path.write_text(json.dumps(model_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final_path.write_text(json.dumps(final_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": execution["status"],
        "development_model": str(model_path),
        "final_result": str(final_path),
        "execution_evidence": str(execution_path),
        "checkpoint_retention_authorized": False,
        "runtime_connection_authorized": False,
        "production_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
