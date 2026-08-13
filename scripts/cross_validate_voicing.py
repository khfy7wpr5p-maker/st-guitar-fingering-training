from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from st_guitar_fingering_training.dataset import build_voicing_candidate_rows
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.training import (
    deterministic_family_folds,
    evaluate_low_total_fret_voicing_baseline,
    evaluate_ranker,
    filter_ambiguous_ranking_rows,
    train_logistic_ranker,
)


def _event_count(rows):
    return len({row.event_id for row in rows})


def _metrics_payload(metrics):
    return {
        "events": metrics.events,
        "top1_accuracy": metrics.top1_accuracy,
        "mean_reciprocal_rank": metrics.mean_reciprocal_rank,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Family-level cross validation for chord/voicing ranking")
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
        raise SystemExit(f"family map missing {len(missing)} files: {missing[:5]}")

    sources = tuple(parse_guitar_musicxml(path, family_id=family_map[path.name]) for path in paths)
    all_family_ids = sorted({source.family_id for source in sources})
    folds = deterministic_family_folds(all_family_ids, folds=args.folds)

    fold_results = []
    validation_coverage = []

    for fold_index, validation_ids_tuple in enumerate(folds, start=1):
        validation_ids = set(validation_ids_tuple)
        train_sources = tuple(source for source in sources if source.family_id not in validation_ids)
        validation_sources = tuple(source for source in sources if source.family_id in validation_ids)

        train_family_ids = {source.family_id for source in train_sources}
        validation_family_ids = {source.family_id for source in validation_sources}
        if train_family_ids & validation_family_ids:
            raise AssertionError("family leakage across cross-validation fold")
        if validation_family_ids != validation_ids:
            raise AssertionError("validation fold contains missing or unexpected families")

        raw_train_rows = build_voicing_candidate_rows(train_sources)
        raw_validation_rows = build_voicing_candidate_rows(validation_sources)
        train_rows = filter_ambiguous_ranking_rows(raw_train_rows)
        validation_rows = filter_ambiguous_ranking_rows(raw_validation_rows)
        if not train_rows or not validation_rows:
            raise SystemExit(f"fold {fold_index}: no ambiguous ranking events")

        model = train_logistic_ranker(train_rows)
        learned = evaluate_ranker(model, validation_rows)
        deterministic = evaluate_low_total_fret_voicing_baseline(validation_rows)
        top1_advantage = learned.top1_accuracy - deterministic.top1_accuracy
        mrr_advantage = learned.mean_reciprocal_rank - deterministic.mean_reciprocal_rank

        fold_results.append({
            "fold": fold_index,
            "validation_families": sorted(validation_family_ids),
            "train_families": len(train_family_ids),
            "raw_train_chord_events": _event_count(raw_train_rows),
            "raw_validation_chord_events": _event_count(raw_validation_rows),
            "excluded_single_candidate_train_events": _event_count(raw_train_rows) - _event_count(train_rows),
            "excluded_single_candidate_validation_events": _event_count(raw_validation_rows) - _event_count(validation_rows),
            "train_candidate_rows": len(train_rows),
            "validation_candidate_rows": len(validation_rows),
            "train_chord_events": _event_count(train_rows),
            "validation_chord_events": _event_count(validation_rows),
            "learned_model": _metrics_payload(learned),
            "deterministic_low_total_fret_baseline": _metrics_payload(deterministic),
            "top1_advantage": top1_advantage,
            "mrr_advantage": mrr_advantage,
        })
        validation_coverage.extend(validation_family_ids)

    if sorted(validation_coverage) != sorted(all_family_ids):
        raise AssertionError("each family must appear in validation exactly once")

    learned_top1 = [fold["learned_model"]["top1_accuracy"] for fold in fold_results]
    baseline_top1 = [fold["deterministic_low_total_fret_baseline"]["top1_accuracy"] for fold in fold_results]
    learned_mrr = [fold["learned_model"]["mean_reciprocal_rank"] for fold in fold_results]
    baseline_mrr = [fold["deterministic_low_total_fret_baseline"]["mean_reciprocal_rank"] for fold in fold_results]
    top1_advantages = [fold["top1_advantage"] for fold in fold_results]
    mrr_advantages = [fold["mrr_advantage"] for fold in fold_results]

    total_events = sum(fold["validation_chord_events"] for fold in fold_results)
    learned_weighted_top1 = sum(fold["learned_model"]["top1_accuracy"] * fold["validation_chord_events"] for fold in fold_results) / total_events
    baseline_weighted_top1 = sum(fold["deterministic_low_total_fret_baseline"]["top1_accuracy"] * fold["validation_chord_events"] for fold in fold_results) / total_events
    learned_weighted_mrr = sum(fold["learned_model"]["mean_reciprocal_rank"] * fold["validation_chord_events"] for fold in fold_results) / total_events
    baseline_weighted_mrr = sum(fold["deterministic_low_total_fret_baseline"]["mean_reciprocal_rank"] * fold["validation_chord_events"] for fold in fold_results) / total_events

    eps = 1e-12
    wins = sum(value > eps for value in top1_advantages)
    losses = sum(value < -eps for value in top1_advantages)
    ties = len(top1_advantages) - wins - losses
    best_fold = max(fold_results, key=lambda fold: fold["top1_advantage"])
    worst_fold = min(fold_results, key=lambda fold: fold["top1_advantage"])

    payload = {
        "task": "family-level cross validation of observed chord/voicing choice ranking",
        "source_files": len(sources),
        "families": len(all_family_ids),
        "folds": args.folds,
        "ambiguous_validation_events_total": total_events,
        "fold_results": fold_results,
        "macro": {
            "learned_top1_accuracy": mean(learned_top1),
            "baseline_top1_accuracy": mean(baseline_top1),
            "top1_advantage": mean(top1_advantages),
            "learned_mrr": mean(learned_mrr),
            "baseline_mrr": mean(baseline_mrr),
            "mrr_advantage": mean(mrr_advantages),
        },
        "event_weighted": {
            "learned_top1_accuracy": learned_weighted_top1,
            "baseline_top1_accuracy": baseline_weighted_top1,
            "top1_advantage": learned_weighted_top1 - baseline_weighted_top1,
            "learned_mrr": learned_weighted_mrr,
            "baseline_mrr": baseline_weighted_mrr,
            "mrr_advantage": learned_weighted_mrr - baseline_weighted_mrr,
        },
        "fold_outcomes": {
            "learned_top1_wins": wins,
            "ties": ties,
            "losses": losses,
            "best_fold": best_fold["fold"],
            "best_top1_advantage": best_fold["top1_advantage"],
            "worst_fold": worst_fold["fold"],
            "worst_top1_advantage": worst_fold["top1_advantage"],
        },
        "checkpoint_retained": False,
        "interpretation": "cross-family robustness evidence for observed Guitar Pro behavior cloning only; not teacher-GOLD or production-ready",
    }

    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
