from __future__ import annotations

import argparse, json
from pathlib import Path
import numpy as np

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.path_optimizer import evaluate_sequence_path_decoder
from st_guitar_fingering_training.sequence_context import build_sequence_training_rows, evaluate_sequence_ranker_rollout
from st_guitar_fingering_training.training import deterministic_family_folds, filter_ambiguous_ranking_rows, train_logistic_ranker


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
    sources = tuple(parse_guitar_musicxml(x, family_id=fmap[x.name]) for x in paths)
    folds = deterministic_family_folds({s.family_id for s in sources}, folds=a.folds)
    results = []
    for number, validation_ids in enumerate(folds, 1):
        val = set(validation_ids)
        train_sources = tuple(s for s in sources if s.family_id not in val)
        val_sources = tuple(s for s in sources if s.family_id in val)
        rows = filter_ambiguous_ranking_rows(build_sequence_training_rows(train_sources))
        model = train_logistic_ranker(rows)
        greedy = evaluate_sequence_ranker_rollout(model, val_sources)
        path = evaluate_sequence_path_decoder(model, val_sources)
        if greedy.events != path.events:
            raise AssertionError("greedy/path event mismatch")
        results.append({"fold": number, "events": path.events, "greedy_top1": greedy.top1_accuracy, "path_top1": path.top1_accuracy, "advantage": path.top1_accuracy-greedy.top1_accuracy, "path_exact_source_rate": path.exact_source_rate})
    weights = np.asarray([x["events"] for x in results], dtype=float)
    advantages = [x["advantage"] for x in results]
    report = {
        "stage": "6F-sequence-path-v1",
        "source_files": len(sources),
        "families": len({s.family_id for s in sources}),
        "folds": a.folds,
        "checkpoint_retained": False,
        "fold_results": results,
        "macro": {"path_top1": float(np.mean([x["path_top1"] for x in results])), "greedy_top1": float(np.mean([x["greedy_top1"] for x in results])), "path_vs_greedy": float(np.mean(advantages)), "path_exact_source_rate": float(np.mean([x["path_exact_source_rate"] for x in results]))},
        "event_weighted": {"path_top1": float(np.average([x["path_top1"] for x in results], weights=weights)), "greedy_top1": float(np.average([x["greedy_top1"] for x in results], weights=weights)), "path_vs_greedy": float(np.average(advantages, weights=weights))},
        "fold_outcomes": {"wins_vs_greedy": sum(x>0 for x in advantages), "losses_vs_greedy": sum(x<0 for x in advantages), "ties_vs_greedy": sum(x==0 for x in advantages), "best_vs_greedy": max(advantages), "worst_vs_greedy": min(advantages)},
        "validation_policy": "bounded DP over physical voicing states; no observed validation string/fret labels are used for decoding",
        "interpretation": "observed Guitar Pro behavior-cloning diagnostic only; not teacher-GOLD or production-ready"
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if a.output:
        Path(a.output).write_text(text+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
