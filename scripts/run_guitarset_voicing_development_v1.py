from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_voicing_development import run_development_fit


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preregistered GuitarSet Observed Voicing DEVELOPMENT fit only")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()

    report, artifact = run_development_fit(args.archive, reproduction_runs=10)
    _write(args.report, report)
    if not report["development_pass"] or artifact is None:
        if args.model.exists():
            args.model.unlink()
        print("DEVELOPMENT_FAIL_STOP")
        return 2
    _write(args.model, artifact)
    print("DEVELOPMENT_PASS_MODEL_SEALED_VALIDATION_CLOSED")
    print(f"evidence_sha256={report['evidence_sha256']}")
    print(f"model_artifact_sha256={artifact['artifact_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
