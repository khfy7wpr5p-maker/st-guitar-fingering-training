from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.synthetic import generate_synthetic_corpus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--families", type=int, default=100)
    parser.add_argument("--events-per-family", type=int, default=24)
    args = parser.parse_args()

    output = Path(args.output_dir)
    if output.exists() and any(output.glob("*.xml")):
        raise ValueError("output directory already contains XML; use a new/empty directory")

    summary = generate_synthetic_corpus(
        output,
        families=args.families,
        events_per_family=args.events_per_family,
    )
    family_map = json.loads((output / "family_map.json").read_text(encoding="utf-8"))

    parsed_events = 0
    for path in sorted(output.glob("*.xml")):
        parsed = parse_guitar_musicxml(path, family_id=family_map[path.name])
        if parsed.pitch_mode != "sounding_exact":
            raise AssertionError("synthetic corpus must round-trip as sounding_exact")
        if len(parsed.events) != args.events_per_family:
            raise AssertionError("synthetic family event-count mismatch")
        if not all(event.is_chord for event in parsed.events):
            raise AssertionError("synthetic corpus v1 must contain chord/polyphonic events only")
        parsed_events += len(parsed.events)

    if parsed_events != args.families * args.events_per_family:
        raise AssertionError("synthetic corpus total event-count mismatch")

    report = dict(summary)
    report.update({
        "roundtrip_xml_files": len(family_map),
        "roundtrip_events": parsed_events,
        "roundtrip_status": "PASS",
        "admission": "SYNTHETIC_RULE_PREFERRED_ONLY",
        "teacher_gold": False,
    })
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
