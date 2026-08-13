from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.sequence_context import build_sequence_training_rows, evaluate_sequence_ranker_rollout
from st_guitar_fingering_training.training import deterministic_family_folds, filter_ambiguous_ranking_rows, train_logistic_ranker
from st_guitar_fingering_training.transition_model import (
    DEFAULT_TRANSITION_WEIGHT,
    build_transition_training_rows,
    evaluate_combined_transition_rollout,
    evaluate_transition_ranker_teacher_forced,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--family-map", required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--transition-weight", type=float, default=DEFAULT_TRANSITION_WEIGHT)
    parser.add_argument("--output")
    args = parser.parse_args()

    if not np.isfinite(args.transition_weight) or not 0.0 <= args.transition_weight <= 1.0:
        raise ValueError("transition weight must be within [0, 1]")

    data = Path(args.data_dir)
    family_map = json.loads(Path(args.family_map).read_text(encoding="utf-8"))
    paths = sorted(data.glob("*.xml"))
    sources = tuple(parse_guitar_musicxml(path, family_id=family_map[path.name]) for path in paths)
    folds = deterministic_family_folds({source.family_id for source in sources}, folds=args.folds)

    results = []
    for fold_number, validation_ids in enumerate(folds, 1):
        validation_set = set(validation_ids)
        train_sources = tuple(source for source in sources if source.family_id not in validation_set)
        validation_sources = tuple(source for source in sources if source.family_id in validation_set)

        sequence_rows = filter_ambiguous_ranking_rows(build_sequence_training_rows(train_sources))
        transition_rows = filter_ambiguous_ranking_rows(build_transition_training_rows(train_sources))
        sequence_model = train_logistic_ranker(sequence_rows)
        transition_model = train_logistic_ranker(transition_rows)

        sequence = evaluate_sequence_ranker_rollout(sequence_model, validation_sources)
        combined = evaluate_combined_transition_rollout(
            sequence_model,
            transition_model,
            validation_sources,
            transition_weight=args.transition_weight,
        )
        transition_diagnostic = evaluate_transition_ranker_teacher_forced(transition_model, validation_sources)

        if sequence.events != combined.events:
            raise AssertionError("sequence/combined validation event mismatch")

        results.append({
            "fold": fold_number,
            "events": combined.events,
            "sequence_top1": sequence.top1_accuracy,
            "combined_top1": combined.top1_accuracy,
            "top1_advantage": combined.top1_accuracy - sequence.top1_accuracy,
            "sequence_mrr": sequence.mean_reciprocal_rank,
            "combined_mrr": combined.mean_reciprocal_rank,
            "mrr_advantage": combined.mean_reciprocal_rank - sequence.mean_reciprocal_rank,
            "transition_teacher_forced_events": transition_diagnostic.events,
            "transition_teacher_forced_top1": transition_diagnostic.top1_accuracy,
            "transition_teacher_forced_mrr": transition_diagnostic.mean_reciprocal_rank,
        })

    weights = np.asarray([result["events"] for result in results], dtype=float)
    top1_advantages = [result["top1_advantage"] for result in results]
    mrr_advantages = [result["mrr_advantage"] for result in results]

    report = {
        "stage": "6G-transition-model-v1",
        "source_files": len(sources),
        "families": len({source.family_id for source in sources}),
        "folds": args.folds,
        "transition_weight": args.transition_weight,
        "checkpoint_retained": False,
        "fold_results": results,
        "macro": {
            "sequence_top1": float(np.mean([result["sequence_top1"] for result in results])),
            "combined_top1": float(np.mean([result["combined_top1"] for result in results])),
            "combined_vs_sequence_top1": float(np.mean(top1_advantages)),
            "sequence_mrr": float(np.mean([result["sequence_mrr"] for result in results])),
            "combined_mrr": float(np.mean([result["combined_mrr"] for result in results])),
            "combined_vs_sequence_mrr": float(np.mean(mrr_advantages)),
            "transition_teacher_forced_top1": float(np.mean([result["transition_teacher_forced_top1"] for result in results])),
            "transition_teacher_forced_mrr": float(np.mean([result["transition_teacher_forced_mrr"] for result in results])),
        },
        "event_weighted": {
            "sequence_top1": float(np.average([result["sequence_top1"] for result in results], weights=weights)),
            "combined_top1": float(np.average([result["combined_top1"] for result in results], weights=weights)),
            "combined_vs_sequence_top1": float(np.average(top1_advantages, weights=weights)),
            "sequence_mrr": float(np.average([result["sequence_mrr"] for result in results], weights=weights)),
            "combined_mrr": float(np.average([result["combined_mrr"] for result in results], weights=weights)),
            "combined_vs_sequence_mrr": float(np.average(mrr_advantages, weights=weights)),
        },
        "fold_outcomes": {
            "wins_vs_sequence": sum(value > 0 for value in top1_advantages),
            "losses_vs_sequence": sum(value < 0 for value in top1_advantages),
            "ties_vs_sequence": sum(value == 0 for value in top1_advantages),
            "best_vs_sequence": max(top1_advantages),
            "worst_vs_sequence": min(top1_advantages),
        },
        "validation_policy": "combined rollout uses only prior model-selected voicing; no observed validation string/fret placement is fed back; future remains pitch-only",
        "interpretation": "separate transition-preference diagnostic on observed Guitar Pro behavior; not teacher-GOLD or production-ready",
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
