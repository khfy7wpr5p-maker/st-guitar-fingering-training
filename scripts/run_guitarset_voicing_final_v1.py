from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_voicing_final import run_final_once

EXPECTED_FINAL_OPEN_REQUEST_SHA256 = (
    "6201314404578ba2c1d1c3dc1e43704b2cd401914583f025700319152edf5338"
)


def _verify_open_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("final-open request must be one JSON object")
    claimed = payload.get("request_sha256")
    if claimed != EXPECTED_FINAL_OPEN_REQUEST_SHA256:
        raise ValueError("final-open request identity drift")
    core = {key: value for key, value in payload.items() if key != "request_sha256"}
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if sha256(raw).hexdigest() != claimed:
        raise ValueError("final-open request SHA-256 mismatch")
    if payload.get("status") != "AUTHORIZED_TO_OPEN_UNTOUCHED_FINAL_ONCE":
        raise ValueError("final-open request status drift")
    if payload.get("untouched_final_performer") != "02":
        raise ValueError("final-open performer drift")
    if payload.get("model_refit_allowed") is not False or payload.get("hyperparameter_tuning_allowed") is not False:
        raise ValueError("final-open request must forbid refit and tuning")
    if payload.get("checkpoint_authorized") is not False:
        raise ValueError("final-open request must not authorize checkpoint retention")
    if payload.get("runtime_connection_authorized") is not False or payload.get("production_authorized") is not False:
        raise ValueError("final-open request must keep runtime/production closed")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen GuitarSet observed-voicing one-shot UNTOUCHED_FINAL performer 02"
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--validation-evidence", type=Path, required=True)
    parser.add_argument("--open-request", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    _verify_open_request(args.open_request)
    report = run_final_once(
        args.archive,
        sealed_model_path=args.model,
        validation_evidence_path=args.validation_evidence,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"status={report['status']}")
    print(f"ambiguous_events={report['final_source_counts']['ambiguous_voicings']}")
    print(f"event_top1_delta={report['metrics']['event_top1_delta']:.12f}")
    print(f"event_mrr_delta={report['metrics']['event_mrr_delta']:.12f}")
    print(f"recording_macro_top1_delta={report['metrics']['recording_macro_top1_delta']:.12f}")
    print(f"recording_macro_mrr_delta={report['metrics']['recording_macro_mrr_delta']:.12f}")
    print(f"bootstrap_lower={report['recording_block_bootstrap']['lower_bound']:.12f}")
    print(f"evidence_sha256={report['evidence_sha256']}")
    return 0 if report["final_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
