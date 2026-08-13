from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.dataset import build_candidate_rows, split_families
from st_guitar_fingering_training.training import train_logistic_ranker, evaluate_ranker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--family-map", required=True, help="JSON object mapping exact filename to broad family_id")
    args = parser.parse_args()
    family_map = json.loads(Path(args.family_map).read_text())
    sources = tuple(parse_guitar_musicxml(p, family_id=family_map[Path(p).name]) for p in args.paths)
    train_sources, val_sources = split_families(sources, validation_count=2)
    train_rows = build_candidate_rows(train_sources)
    val_rows = build_candidate_rows(val_sources)
    model = train_logistic_ranker(train_rows)
    metrics = evaluate_ranker(model, val_rows)
    payload = {
        "source_files": len(sources),
        "train_families": sorted({s.family_id for s in train_sources}),
        "validation_families": sorted({s.family_id for s in val_sources}),
        "train_rows": len(train_rows),
        "validation_rows": len(val_rows),
        "train_single_note_events": len({r.event_id for r in train_rows}),
        "validation_single_note_events": len({r.event_id for r in val_rows}),
        "validated_events_total": sum(len(s.events) for s in sources),
        "validated_chord_events_total": sum(sum(e.is_chord for e in s.events) for s in sources),
        "pitch_modes": {s.family_id: s.pitch_mode for s in sources},
        "metrics": {
            "events": metrics.events,
            "top1_accuracy": metrics.top1_accuracy,
            "mean_reciprocal_rank": metrics.mean_reciprocal_rank,
        },
        "interpretation": "bounded observed-placement ranking pilot; not teacher-GOLD and not a production model",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
