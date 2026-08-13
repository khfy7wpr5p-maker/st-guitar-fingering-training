from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from st_guitar_fingering_training.dataset import build_voicing_candidate_rows
from st_guitar_fingering_training.intake import parse_guitar_musicxml


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit physically valid chord/voicing ranking candidates")
    parser.add_argument("--data-dir", required=True, help="Directory containing MusicXML .xml files")
    parser.add_argument("--family-map", required=True, help="JSON mapping exact filename to safe family_id")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    family_map = json.loads(Path(args.family_map).read_text(encoding="utf-8"))
    paths = sorted(data_dir.glob("*.xml"))
    if not paths:
        raise SystemExit("no XML files found")

    missing = [path.name for path in paths if path.name not in family_map]
    if missing:
        raise SystemExit(f"family map missing {len(missing)} files: {missing[:5]}")

    sources = tuple(
        parse_guitar_musicxml(path, family_id=family_map[path.name])
        for path in paths
    )
    rows = build_voicing_candidate_rows(sources)

    by_event = defaultdict(list)
    for row in rows:
        by_event[row.event_id].append(row)

    candidate_counts = [len(group) for group in by_event.values()]
    observed_counts = [sum(row.observed for row in group) for group in by_event.values()]
    if any(count != 1 for count in observed_counts):
        raise SystemExit("one or more chord events do not have exactly one observed candidate")

    chord_events_by_family = Counter()
    for source in sources:
        chord_events_by_family[source.family_id] += sum(event.is_chord for event in source.events)

    note_count_histogram = Counter()
    for group in by_event.values():
        note_count_histogram[len(group[0].pitches_midi)] += 1

    report = {
        "source_files": len(sources),
        "families": len({source.family_id for source in sources}),
        "validated_events": sum(len(source.events) for source in sources),
        "chord_events": len(by_event),
        "candidate_rows": len(rows),
        "ambiguous_chord_events": sum(count > 1 for count in candidate_counts),
        "single_candidate_chord_events": sum(count == 1 for count in candidate_counts),
        "candidate_count": {
            "min": min(candidate_counts),
            "median": median(candidate_counts),
            "mean": mean(candidate_counts),
            "max": max(candidate_counts),
        },
        "note_count_histogram": dict(sorted(note_count_histogram.items())),
        "chord_events_by_family": dict(sorted(chord_events_by_family.items())),
        "interpretation": "physical chord/voicing candidate audit only; observed Guitar Pro choices are not teacher-GOLD preferences",
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
