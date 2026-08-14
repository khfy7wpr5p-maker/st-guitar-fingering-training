from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.synthetic_balanced import generate_balanced_synthetic_corpus
from st_guitar_fingering_training.synthetic_behavior import STYLES
from st_guitar_fingering_training.synthetic_pairwise import compare_behavior_rankers


def _style_map_from_manifest(path: Path) -> dict[str, str]:
    style_by_family: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item["label_class"] != "RULE_PREFERRED" or item["teacher_gold"] is not False:
            raise AssertionError("C2 accepts only RULE_PREFERRED synthetic non-teacher labels")
        family_id = item["family_id"]
        style = item["style"]
        if style not in STYLES:
            raise AssertionError("unknown synthetic style in manifest")
        prior = style_by_family.setdefault(family_id, style)
        if prior != style:
            raise AssertionError("synthetic family cannot change style across events")
    return style_by_family


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--families", type=int, default=100)
    parser.add_argument("--events-per-family", type=int, default=24)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    with TemporaryDirectory(prefix="stage7b_c2_") as td:
        root = Path(td)
        corpus_summary = generate_balanced_synthetic_corpus(
            root,
            families=args.families,
            events_per_family=args.events_per_family,
        )
        family_map = json.loads((root / "family_map.json").read_text(encoding="utf-8"))
        style_by_family = _style_map_from_manifest(root / "synthetic_manifest.jsonl")

        sources_by_style = {style: [] for style in STYLES}
        parsed_events = 0
        for path in sorted(root.glob("*.xml")):
            family_id = family_map[path.name]
            parsed = parse_guitar_musicxml(path, family_id=family_id)
            if parsed.pitch_mode != "sounding_exact":
                raise AssertionError("C2 corpus must round-trip as sounding_exact")
            if len(parsed.events) != args.events_per_family:
                raise AssertionError("C2 family event-count mismatch")
            if not all(event.is_chord for event in parsed.events):
                raise AssertionError("C2 corpus must remain chord/polyphonic only")
            sources_by_style[style_by_family[family_id]].append(parsed)
            parsed_events += len(parsed.events)

        if len(family_map) != args.families or parsed_events != args.families * args.events_per_family:
            raise AssertionError("C2 corpus size mismatch")
        expected_per_style = args.families // len(STYLES)
        if any(len(sources_by_style[style]) != expected_per_style for style in STYLES):
            raise AssertionError("C2 specialists require balanced style family counts")

        comparisons = {}
        for style in STYLES:
            comparison = compare_behavior_rankers(
                tuple(sources_by_style[style]),
                style,
                folds=args.folds,
            )
            baseline = comparison["baseline"]
            pairwise = comparison["pairwise"]
            comparisons[style] = {
                "families": comparison["family_count"],
                "folds": comparison["fold_count"],
                "family_isolated": comparison["family_isolated"],
                "baseline_top1": baseline["macro_top1"],
                "baseline_mrr": baseline["macro_mrr"],
                "pairwise_top1": pairwise["macro_top1"],
                "pairwise_mrr": pairwise["macro_mrr"],
                "uniform_random_top1": pairwise["macro_uniform_random_top1"],
                "top1_delta": comparison["top1_delta"],
                "mrr_delta": comparison["mrr_delta"],
                "pairwise_top1_win": comparison["pairwise_top1_win"],
                "baseline_fold_top1": [fold["top1"] for fold in baseline["folds"]],
                "pairwise_fold_top1": [fold["top1"] for fold in pairwise["folds"]],
                "focus_feature": pairwise["focus_feature"],
                "focus_expected_sign": pairwise["focus_expected_sign"],
                "focus_direction_match_folds": pairwise["focus_direction_match_folds"],
                "pairwise_focus_direction_all_folds": comparison["pairwise_focus_direction_all_folds"],
                "pairwise_mean_coefficients": pairwise["mean_standardized_pairwise_coefficients"],
            }

    win_styles = sum(int(item["pairwise_top1_win"]) for item in comparisons.values())
    focus_pass_styles = sum(int(item["pairwise_focus_direction_all_folds"]) for item in comparisons.values())
    isolation_pass_styles = sum(int(item["family_isolated"]) for item in comparisons.values())

    if corpus_summary["label_class"] != "RULE_PREFERRED" or corpus_summary["teacher_gold"] is not False:
        raise AssertionError("C2 corpus admission boundary changed")
    if win_styles != len(STYLES):
        raise AssertionError("C2 gate requires pairwise Top-1 improvement in all five specialists")
    if focus_pass_styles != len(STYLES):
        raise AssertionError("C2 gate requires focal coefficient direction match in every fold for all specialists")
    if isolation_pass_styles != len(STYLES):
        raise AssertionError("C2 gate requires family isolation for every specialist")

    report = {
        "stage": "7B-C2",
        "corpus": {
            "families": args.families,
            "events_per_family": args.events_per_family,
            "events": args.families * args.events_per_family,
            "styles": corpus_summary["styles"],
            "progressions": corpus_summary["progressions"],
            "label_class": corpus_summary["label_class"],
            "teacher_gold": False,
        },
        "folds": args.folds,
        "comparison": comparisons,
        "pairwise_top1_win_styles": win_styles,
        "focus_direction_pass_styles": focus_pass_styles,
        "family_isolation_pass_styles": isolation_pass_styles,
        "checkpoint_retained": False,
        "production_integration": False,
        "status": "PASS",
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
