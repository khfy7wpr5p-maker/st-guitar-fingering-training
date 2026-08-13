from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from st_guitar_fingering_training.context import build_context_training_rows, evaluate_context_ranker_rollout
from st_guitar_fingering_training.dataset import build_voicing_candidate_rows
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.sequence_context import build_sequence_training_rows, evaluate_sequence_ranker_rollout
from st_guitar_fingering_training.training import deterministic_family_folds, evaluate_low_total_fret_voicing_baseline, evaluate_ranker, filter_ambiguous_ranking_rows, train_logistic_ranker


def metrics_payload(metrics):
    return {"events": metrics.events, "top1_accuracy": metrics.top1_accuracy, "mean_reciprocal_rank": metrics.mean_reciprocal_rank}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 6E sequence-context voicing cross-validation")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--family-map", required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    family_map = json.loads(Path(args.family_map).read_text(encoding="utf-8"))
    paths = sorted(data_dir.glob("*.xml"))
    if not paths:
        raise SystemExit("no XML files found")
    missing = [path.name for path in paths if path.name not in family_map]
    if missing:
        raise SystemExit(f"family map missing files: {missing[:5]}")

    sources = tuple(parse_guitar_musicxml(path, family_id=family_map[path.name]) for path in paths)
    families = {source.family_id for source in sources}
    folds = deterministic_family_folds(families, folds=args.folds)
    fold_results = []

    for fold_number, validation_ids in enumerate(folds, 1):
        validation_set = set(validation_ids)
        train_sources = tuple(source for source in sources if source.family_id not in validation_set)
        validation_sources = tuple(source for source in sources if source.family_id in validation_set)

        static_train = filter_ambiguous_ranking_rows(build_voicing_candidate_rows(train_sources))
        static_validation = filter_ambiguous_ranking_rows(build_voicing_candidate_rows(validation_sources))
        context_train = filter_ambiguous_ranking_rows(build_context_training_rows(train_sources))
        sequence_train = filter_ambiguous_ranking_rows(build_sequence_training_rows(train_sources))
        if not static_train or not static_validation or not context_train or not sequence_train:
            raise SystemExit(f"fold {fold_number} has no ambiguous ranking rows")

        static_model = train_logistic_ranker(static_train)
        context_model = train_logistic_ranker(context_train)
        sequence_model = train_logistic_ranker(sequence_train)

        static_metrics = evaluate_ranker(static_model, static_validation)
        baseline_metrics = evaluate_low_total_fret_voicing_baseline(static_validation)
        context_metrics = evaluate_context_ranker_rollout(context_model, validation_sources)
        sequence_metrics = evaluate_sequence_ranker_rollout(sequence_model, validation_sources)
        if len({static_metrics.events, baseline_metrics.events, context_metrics.events, sequence_metrics.events}) != 1:
            raise AssertionError("validation event mismatch across Stage 6E comparators")

        fold_results.append({
            "fold": fold_number,
            "validation_families": list(validation_ids),
            "validation_events": sequence_metrics.events,
            "sequence_rollout": metrics_payload(sequence_metrics),
            "context_rollout": metrics_payload(context_metrics),
            "static_learned": metrics_payload(static_metrics),
            "deterministic_baseline": metrics_payload(baseline_metrics),
            "sequence_vs_context_top1": sequence_metrics.top1_accuracy - context_metrics.top1_accuracy,
            "sequence_vs_static_top1": sequence_metrics.top1_accuracy - static_metrics.top1_accuracy,
            "sequence_vs_baseline_top1": sequence_metrics.top1_accuracy - baseline_metrics.top1_accuracy,
        })

    weights = np.asarray([fold["validation_events"] for fold in fold_results], dtype=float)
    def macro(group, key):
        return float(np.mean([fold[group][key] for fold in fold_results]))
    def weighted(group, key):
        return float(np.average([fold[group][key] for fold in fold_results], weights=weights))

    groups = ("sequence_rollout", "context_rollout", "static_learned", "deterministic_baseline")
    macro_top1 = {group: macro(group, "top1_accuracy") for group in groups}
    weighted_top1 = {group: weighted(group, "top1_accuracy") for group in groups}

    report = {
        "stage": "6E-sequence-context-v2",
        "source_files": len(sources),
        "families": len(families),
        "folds": args.folds,
        "training_past_context_policy": "previous observed chord only",
        "validation_past_context_policy": "rollout previous model prediction; no oracle previous labels",
        "future_context_policy": "next chord sounding pitches+tuning+derived physical candidate geometry only; no future observed string/fret labels",
        "checkpoint_retained": False,
        "fold_results": fold_results,
        "macro": {
            "sequence_top1_accuracy": macro_top1["sequence_rollout"],
            "context_top1_accuracy": macro_top1["context_rollout"],
            "static_top1_accuracy": macro_top1["static_learned"],
            "baseline_top1_accuracy": macro_top1["deterministic_baseline"],
            "sequence_vs_context_top1": macro_top1["sequence_rollout"] - macro_top1["context_rollout"],
            "sequence_vs_static_top1": macro_top1["sequence_rollout"] - macro_top1["static_learned"],
            "sequence_vs_baseline_top1": macro_top1["sequence_rollout"] - macro_top1["deterministic_baseline"],
            "sequence_mrr": macro("sequence_rollout", "mean_reciprocal_rank"),
            "context_mrr": macro("context_rollout", "mean_reciprocal_rank"),
            "static_mrr": macro("static_learned", "mean_reciprocal_rank"),
            "baseline_mrr": macro("deterministic_baseline", "mean_reciprocal_rank"),
        },
        "event_weighted": {
            "sequence_top1_accuracy": weighted_top1["sequence_rollout"],
            "context_top1_accuracy": weighted_top1["context_rollout"],
            "static_top1_accuracy": weighted_top1["static_learned"],
            "baseline_top1_accuracy": weighted_top1["deterministic_baseline"],
            "sequence_vs_context_top1": weighted_top1["sequence_rollout"] - weighted_top1["context_rollout"],
            "sequence_vs_static_top1": weighted_top1["sequence_rollout"] - weighted_top1["static_learned"],
            "sequence_vs_baseline_top1": weighted_top1["sequence_rollout"] - weighted_top1["deterministic_baseline"],
            "sequence_mrr": weighted("sequence_rollout", "mean_reciprocal_rank"),
            "context_mrr": weighted("context_rollout", "mean_reciprocal_rank"),
            "static_mrr": weighted("static_learned", "mean_reciprocal_rank"),
            "baseline_mrr": weighted("deterministic_baseline", "mean_reciprocal_rank"),
        },
        "fold_outcomes": {
            "wins_vs_context": sum(fold["sequence_vs_context_top1"] > 0 for fold in fold_results),
            "ties_vs_context": sum(fold["sequence_vs_context_top1"] == 0 for fold in fold_results),
            "losses_vs_context": sum(fold["sequence_vs_context_top1"] < 0 for fold in fold_results),
            "wins_vs_static": sum(fold["sequence_vs_static_top1"] > 0 for fold in fold_results),
            "ties_vs_static": sum(fold["sequence_vs_static_top1"] == 0 for fold in fold_results),
            "losses_vs_static": sum(fold["sequence_vs_static_top1"] < 0 for fold in fold_results),
            "wins_vs_baseline": sum(fold["sequence_vs_baseline_top1"] > 0 for fold in fold_results),
            "ties_vs_baseline": sum(fold["sequence_vs_baseline_top1"] == 0 for fold in fold_results),
            "losses_vs_baseline": sum(fold["sequence_vs_baseline_top1"] < 0 for fold in fold_results),
            "best_vs_context": max(fold["sequence_vs_context_top1"] for fold in fold_results),
            "worst_vs_context": min(fold["sequence_vs_context_top1"] for fold in fold_results),
        },
        "interpretation": "observed Guitar Pro behavior-cloning diagnostic only; future labels are hidden; not teacher-GOLD or production-ready",
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
