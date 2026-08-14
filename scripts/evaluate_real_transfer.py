from __future__ import annotations

import argparse
import json
from pathlib import Path

from st_guitar_fingering_training.intake import ParsedSource, parse_guitar_musicxml
from st_guitar_fingering_training.synthetic_behavior import STYLES
from st_guitar_fingering_training.transfer_validation import (
    real_transfer_report,
    train_frozen_synthetic_specialists,
)


def _load_family_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("family map must be a non-empty JSON object")
    if any(not isinstance(name, str) or not isinstance(family_id, str) for name, family_id in data.items()):
        raise ValueError("family map keys and values must be strings")
    return data


def _load_sources(data_dir: Path, family_map_path: Path) -> tuple[ParsedSource, ...]:
    family_map = _load_family_map(family_map_path)
    paths = tuple(sorted(data_dir.glob("*.xml")))
    if not paths:
        raise ValueError(f"no XML files found in {data_dir}")
    missing = [path.name for path in paths if path.name not in family_map]
    if missing:
        raise ValueError(f"family map missing {len(missing)} XML files")
    return tuple(parse_guitar_musicxml(path, family_id=family_map[path.name]) for path in paths)


def _synthetic_style_map(manifest_path: Path) -> dict[str, str]:
    style_by_family: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("label_class") != "RULE_PREFERRED" or item.get("teacher_gold") is not False:
            raise ValueError("Stage 7C accepts only RULE_PREFERRED synthetic non-teacher labels")
        family_id = item.get("family_id")
        style = item.get("style")
        if not isinstance(family_id, str) or style not in STYLES:
            raise ValueError("invalid synthetic manifest family/style")
        prior = style_by_family.setdefault(family_id, style)
        if prior != style:
            raise ValueError("synthetic family cannot change specialist style")
    if not style_by_family:
        raise ValueError("empty synthetic manifest")
    return style_by_family


def _group_synthetic_sources(
    sources: tuple[ParsedSource, ...],
    style_by_family: dict[str, str],
) -> dict[str, tuple[ParsedSource, ...]]:
    groups = {style: [] for style in STYLES}
    for source in sources:
        if source.family_id not in style_by_family:
            raise ValueError(f"synthetic manifest missing family: {source.family_id}")
        groups[style_by_family[source.family_id]].append(source)
    if any(not groups[style] for style in STYLES):
        raise ValueError("synthetic corpus must contain all five specialist styles")
    return {style: tuple(groups[style]) for style in STYLES}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate frozen Stage 7 synthetic specialists on an independent real Guitar Pro/MusicXML corpus"
    )
    parser.add_argument("--synthetic-dir", required=True)
    parser.add_argument("--synthetic-family-map", required=True)
    parser.add_argument("--synthetic-manifest", required=True)
    parser.add_argument("--real-dir", required=True)
    parser.add_argument("--real-family-map", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    synthetic_sources = _load_sources(Path(args.synthetic_dir), Path(args.synthetic_family_map))
    style_by_family = _synthetic_style_map(Path(args.synthetic_manifest))
    synthetic_groups = _group_synthetic_sources(synthetic_sources, style_by_family)
    real_sources = _load_sources(Path(args.real_dir), Path(args.real_family_map))

    models = train_frozen_synthetic_specialists(synthetic_groups)
    report = real_transfer_report(models, synthetic_groups, real_sources)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
