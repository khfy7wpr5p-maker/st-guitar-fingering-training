from __future__ import annotations

import json
from pathlib import Path

from .synthetic import family_to_musicxml, generate_synthetic_family


def balanced_family_indices(families: int = 100) -> tuple[int, ...]:
    """Return a balanced plan across 5 styles × 5 progressions.

    The underlying v1 family mapping repeats every 60 indices: five 12-key
    style blocks inside one progression block. For 100 families we take four
    keys from each style/progression cell, yielding exactly 20 families per
    style and 20 per progression.
    """
    if families < 25 or families > 300 or families % 25:
        raise ValueError("balanced families must be a multiple of 25 within 25..300")
    per_cell = families // 25
    out = []
    for progression in range(5):
        for style in range(5):
            for k in range(per_cell):
                key_offset = (3 * k + progression + 2 * style) % 12
                out.append(progression * 60 + style * 12 + key_offset)
    if len(set(out)) != families:
        raise AssertionError("balanced synthetic family plan contains duplicates")
    return tuple(out)


def generate_balanced_synthetic_corpus(output_dir: str | Path, families: int = 100, events_per_family: int = 24) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    family_map = {}
    style_counts = {}
    progression_counts = {}
    candidate_counts = []

    with (output / "synthetic_manifest.jsonl").open("w", encoding="utf-8") as manifest:
        for family_index in balanced_family_indices(families):
            family = generate_synthetic_family(family_index, events_per_family=events_per_family)
            filename = f"{family.family_id}.xml"
            (output / filename).write_text(family_to_musicxml(family), encoding="utf-8")
            family_map[filename] = family.family_id
            style_counts[family.style] = style_counts.get(family.style, 0) + 1
            pkey = "-".join(map(str, family.progression))
            progression_counts[pkey] = progression_counts.get(pkey, 0) + 1
            for event in family.events:
                candidate_counts.append(event.candidate_count)
                manifest.write(json.dumps({
                    "family_id": family.family_id,
                    "event_index": event.index,
                    "key_pc": family.key_pc,
                    "style": family.style,
                    "progression": family.progression,
                    "degree": event.degree,
                    "pitches_midi": event.pitches_midi,
                    "preferred": event.preferred,
                    "candidate_count": event.candidate_count,
                    "label_class": family.label_class,
                    "rule_id": event.rule_id,
                    "provenance": family.provenance,
                    "teacher_gold": False,
                }, sort_keys=True) + "\n")

    (output / "family_map.json").write_text(json.dumps(family_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema": "st-guitar-synthetic-corpus-v1-balanced",
        "families": families,
        "events_per_family": events_per_family,
        "events": families * events_per_family,
        "styles": style_counts,
        "progressions": progression_counts,
        "label_class": "RULE_PREFERRED",
        "teacher_gold": False,
        "candidate_count_min": min(candidate_counts),
        "candidate_count_max": max(candidate_counts),
        "candidate_count_mean": sum(candidate_counts) / len(candidate_counts),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
