from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.dataset import build_voicing_candidate_rows, split_families
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.training import (
    evaluate_low_total_fret_voicing_baseline,
    evaluate_ranker,
    train_logistic_ranker,
)


def _metrics_payload(metrics):
    return {
        "events": metrics.events,
        "top1_accuracy": metrics.top1_accuracy,
        "mean_reciprocal_rank": metrics.mean_reciprocal_rank,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded chord/voicing observed-choice ranking pilot")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--family-map", required=True)
    parser.add_argument("--validation-count", type=int, default=3)
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
    train_sources, val_sources = split_families(sources, validation_count=args.validation_count)
    train_rows = build_voicing_candidate_rows(train_sources)
    val_rows = build_voicing_candidate_rows(val_sources)

    model = train_logistic_ranker(train_rows)
    learned = evaluate_ranker(model, val_rows)
    deterministic = evaluate_low_total_fret_voicing_baseline(val_rows)

    payload = {
        "task": "observed chord/voicing choice ranking among physically valid candidates",
        "source_files": len(sources),
        "families": len({s.family_id for s in sources}),
        "train_families": sorted({s.family_id for s in train_sources}),
        "validation_families": sorted({s.family_id for s in val_sources}),
        "train_candidate_rows": len(train_rows),
        "validation_candidate_rows": len(val_rows),
        "train_chord_events": len({r.event_id for r in train_rows}),
        "validation_chord_events": len({r.event_id for r in val_rows}),
        "learned_model": _metrics_payload(learned),
        "deterministic_low_total_fret_baseline": _metrics_payload(deterministic),
        "top1_advantage": learned.top1_accuracy - deterministic.top1_accuracy,
        "mrr_advantage": learned.mean_reciprocal_rank - deterministic.mean_reciprocal_rank,
        "checkpoint_retained": False,
        "interpretation": (
            "bounded observed-Guitar-Pro-choice behavior cloning only; not teacher-GOLD, "
            "not left-hand fingering, not production-ready"
        ),
    }

    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
