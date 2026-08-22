from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_voicing_validation_v2 import run_validation_once_v2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one-shot GuitarSet v2 VALIDATION performer 03")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--development-evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = run_validation_once_v2(
        args.archive,
        sealed_model_path=args.model,
        development_evidence_path=args.development_evidence,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report["status"])
    print(f"evidence_sha256={report['evidence_sha256']}")
    print(f"event_top1_delta={report['metrics']['event_top1_delta']}")
    print(f"event_mrr_delta={report['metrics']['event_mrr_delta']}")
    print(f"bootstrap_lower={report['recording_block_bootstrap']['lower_bound']}")
    print(f"fret20_candidate_events={report['validation_source_counts']['fret20_candidate_event_count']}")
    return 0 if report["validation_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
