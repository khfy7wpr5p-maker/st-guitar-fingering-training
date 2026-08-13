from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from st_guitar_fingering_training.context import build_context_training_rows, evaluate_context_ranker_rollout
from st_guitar_fingering_training.dataset import build_voicing_candidate_rows
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.training import deterministic_family_folds, evaluate_low_total_fret_voicing_baseline, evaluate_ranker, filter_ambiguous_ranking_rows, train_logistic_ranker


def m(metrics):
    return {"events": metrics.events, "top1_accuracy": metrics.top1_accuracy, "mean_reciprocal_rank": metrics.mean_reciprocal_rank}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True)
    p.add_argument("--family-map", required=True)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--output")
    a = p.parse_args()

    data = Path(a.data_dir)
    fmap = json.loads(Path(a.family_map).read_text(encoding="utf-8"))
    paths = sorted(data.glob("*.xml"))
    if not paths:
        raise SystemExit("no XML files found")
    missing = [x.name for x in paths if x.name not in fmap]
    if missing:
        raise SystemExit(f"family map missing files: {missing[:5]}")

    sources = tuple(parse_guitar_musicxml(x, family_id=fmap[x.name]) for x in paths)
    families = {s.family_id for s in sources}
    folds = deterministic_family_folds(families, folds=a.folds)
    out = []

    for i, val_ids in enumerate(folds, 1):
        val_set = set(val_ids)
        train_sources = tuple(s for s in sources if s.family_id not in val_set)
        val_sources = tuple(s for s in sources if s.family_id in val_set)

        static_train = filter_ambiguous_ranking_rows(build_voicing_candidate_rows(train_sources))
        static_val = filter_ambiguous_ranking_rows(build_voicing_candidate_rows(val_sources))
        context_train = filter_ambiguous_ranking_rows(build_context_training_rows(train_sources))
        if not static_train or not static_val or not context_train:
            raise SystemExit(f"fold {i} has no ambiguous ranking rows")

        static_model = train_logistic_ranker(static_train)
        context_model = train_logistic_ranker(context_train)
        static_metrics = evaluate_ranker(static_model, static_val)
        baseline_metrics = evaluate_low_total_fret_voicing_baseline(static_val)
        context_metrics = evaluate_context_ranker_rollout(context_model, val_sources)
        if context_metrics.events != static_metrics.events:
            raise AssertionError("context/static validation event mismatch")

        out.append({
            "fold": i,
            "validation_families": list(val_ids),
            "validation_events": context_metrics.events,
            "context_rollout": m(context_metrics),
            "static_learned": m(static_metrics),
            "deterministic_baseline": m(baseline_metrics),
            "context_vs_static_top1": context_metrics.top1_accuracy - static_metrics.top1_accuracy,
            "context_vs_baseline_top1": context_metrics.top1_accuracy - baseline_metrics.top1_accuracy,
        })

    weights = np.asarray([f["validation_events"] for f in out], dtype=float)
    def macro(group, key):
        return float(np.mean([f[group][key] for f in out]))
    def weighted(group, key):
        return float(np.average([f[group][key] for f in out], weights=weights))

    mc, ms, mb = macro("context_rollout", "top1_accuracy"), macro("static_learned", "top1_accuracy"), macro("deterministic_baseline", "top1_accuracy")
    wc, ws, wb = weighted("context_rollout", "top1_accuracy"), weighted("static_learned", "top1_accuracy"), weighted("deterministic_baseline", "top1_accuracy")

    report = {
        "stage": "6D-transition-context-v1",
        "source_files": len(sources),
        "families": len(families),
        "folds": a.folds,
        "training_context_policy": "previous observed chord only",
        "validation_context_policy": "rollout previous model prediction; no oracle previous labels",
        "checkpoint_retained": False,
        "fold_results": out,
        "macro": {
            "context_top1_accuracy": mc,
            "static_top1_accuracy": ms,
            "baseline_top1_accuracy": mb,
            "context_vs_static_top1": mc - ms,
            "context_vs_baseline_top1": mc - mb,
            "context_mrr": macro("context_rollout", "mean_reciprocal_rank"),
            "static_mrr": macro("static_learned", "mean_reciprocal_rank"),
            "baseline_mrr": macro("deterministic_baseline", "mean_reciprocal_rank"),
        },
        "event_weighted": {
            "context_top1_accuracy": wc,
            "static_top1_accuracy": ws,
            "baseline_top1_accuracy": wb,
            "context_vs_static_top1": wc - ws,
            "context_vs_baseline_top1": wc - wb,
            "context_mrr": weighted("context_rollout", "mean_reciprocal_rank"),
            "static_mrr": weighted("static_learned", "mean_reciprocal_rank"),
            "baseline_mrr": weighted("deterministic_baseline", "mean_reciprocal_rank"),
        },
        "fold_outcomes": {
            "wins_vs_static": sum(f["context_vs_static_top1"] > 0 for f in out),
            "losses_vs_static": sum(f["context_vs_static_top1"] < 0 for f in out),
            "wins_vs_baseline": sum(f["context_vs_baseline_top1"] > 0 for f in out),
            "losses_vs_baseline": sum(f["context_vs_baseline_top1"] < 0 for f in out),
            "best_vs_static": max(f["context_vs_static_top1"] for f in out),
            "worst_vs_static": min(f["context_vs_static_top1"] for f in out),
        },
        "interpretation": "observed Guitar Pro behavior-cloning diagnostic only; not teacher-GOLD or production-ready",
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if a.output:
        Path(a.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
