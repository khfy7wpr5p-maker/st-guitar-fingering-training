from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_voicing_numerical_hardening_v2 import (
    build_numerical_hardening_evidence_v2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build controlled GuitarSet v2 numerical-hardening evidence")
    parser.add_argument("archive")
    parser.add_argument("--model", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--source-code-sha", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    evidence = build_numerical_hardening_evidence_v2(
        archive_path=args.archive,
        model_path=args.model,
        request_path=args.request,
        source_code_sha=args.source_code_sha,
    )
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0 if evidence["status"].startswith("NUMERICAL_HARDENING_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
