from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.teacher_correction_manual_v1 import (
    build_manual_regression_manifest,
    build_manual_task,
    render_manual_regression_html,
    validate_manual_teacher_solution,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)

CASES = (
    ("Mi minör — açık pozisyon", (40, 47, 52, 55)),
    ("Do majör — açık pozisyon", (48, 52, 55, 60, 64)),
    ("La minör — açık pozisyon", (45, 52, 57, 60, 64)),
    ("Re majör — açık pozisyon", (50, 57, 62, 66)),
    ("Sol majör — açık pozisyon", (43, 47, 50, 55, 59, 67)),
    ("Fa majör — standart şekil", (41, 48, 53, 57, 60, 65)),
)

E_MINOR_EXPECTED = (
    {"pitch_midi": 40, "string": 6, "fret": 0, "finger": 0},
    {"pitch_midi": 47, "string": 5, "fret": 2, "finger": 2},
    {"pitch_midi": 52, "string": 4, "fret": 2, "finger": 3},
    {"pitch_midi": 55, "string": 3, "fret": 0, "finger": 0},
)


def build(output_dir: Path) -> dict:
    tasks = tuple(
        build_manual_task(task_name=name, pitches_midi=pitches, tuning=STANDARD_TUNING)
        for name, pitches in CASES
    )
    manifest = build_manual_regression_manifest(tasks)
    e_minor = validate_manual_teacher_solution(
        pitches_midi=CASES[0][1],
        tuning=STANDARD_TUNING,
        rows=E_MINOR_EXPECTED,
    )
    if e_minor["barres"]:
        raise RuntimeError("STOP: expected E minor separate-finger solution unexpectedly contains barre")
    expected_triplets = {(6, 0, 0), (5, 2, 2), (4, 2, 3), (3, 0, 0)}
    actual_triplets = {(row["string"], row["fret"], row["finger"]) for row in e_minor["placements"]}
    if actual_triplets != expected_triplets:
        raise RuntimeError("STOP: E minor manual validator drift")

    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "ST_Guitar_TeacherCorrectionV1_ManualRegression.html"
    manifest_path = output_dir / "ST_Guitar_TeacherCorrectionV1_ManualRegression_manifest.json"
    evidence_path = output_dir / "ST_Guitar_TeacherCorrectionV1_ManualRegression_evidence.json"
    html_path.write_text(render_manual_regression_html(manifest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = {
        "schema": "st-guitar-teacher-correction-v1-manual-regression-evidence",
        "status": "PASS",
        "manifest_sha256": manifest["manifest_sha256"],
        "task_count": manifest["task_count"],
        "training_authorized": False,
        "e_minor_validator_status": e_minor["status"],
        "e_minor_assignment_id": e_minor["assignment_id"],
        "e_minor_expected": list(E_MINOR_EXPECTED),
        "e_minor_barres": e_minor["barres"],
    }
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Build short Teacher Correction v1 manual regression")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
