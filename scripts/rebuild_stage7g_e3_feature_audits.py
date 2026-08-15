from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
import urllib.request

from st_guitar_fingering_training.curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    stage7g_e3_curriculum_level,
    stage7g_e3_feature_record,
)
from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.mxl_target_free import parse_target_free_mxl
from st_guitar_fingering_training.stage7g_e3_e_a2 import PITCH_MODE, STANDARD_TUNING_MIDI
from st_guitar_fingering_training.stage7g_e3_e_a3 import (
    _event_id,
    _winner,
    reconstruct_frozen_open_low_compact_specialists,
)
from st_guitar_fingering_training.stage7g_e3_e_b import (
    build_e3e_disagreement_pool,
    canonical_json_bytes,
    e3e_internal_audit,
    select_e3e_validation_batch,
)
from st_guitar_fingering_training.target_free_musicxml import parse_target_free_musicxml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "e3_feature_audits"
ANIMETAB_REPO = "amamiya-yuuko/AnimeTAB"
ANIMETAB_REF = "main"
EXPECTED_DEV_DISAGREEMENTS = 5626
EXPECTED_DEV_TASK_SET_SHA256 = "d7a45c08e5fd4bc2c4e8773f45ba1f54ab5d5794b7ca69877c8f8c7a2d4980f7"
EXPECTED_E3E_AUDIT_SHA256 = "75440e8e97c1ab80c27d93f8f37d1545a776e7fc8d9d0ddc6de5fdad9d98f7ee"


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "st-guitar-e3e-feature-audit-v1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def raw_github_url(repo: str, ref: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{quote(path, safe='/')}"


def feature_row(source, event, index: int, models: dict[str, object]) -> dict | None:
    if not event.is_chord:
        return None
    candidates = valid_chord_voicings(event.pitches_midi, event.tuning)
    if len(candidates) < 2:
        return None
    open_low = _winner(candidates, models["open_low"], "open_low")
    compact = _winner(candidates, models["compact"], "compact")
    if open_low == compact:
        return None
    record = stage7g_e3_feature_record(event.pitches_midi, event.tuning, open_low, compact)
    geometry_delta = {
        name: record[f"compact_minus_open__{name}"]
        for name in STAGE7G_E3_GEOMETRY_NAMES
    }
    level = stage7g_e3_curriculum_level(
        chord_size=len(event.pitches_midi),
        candidate_count=len(candidates),
        geometry_delta=geometry_delta,
    )
    return {
        "event_id": _event_id(source, event, index),
        "family_id": source.family_id,
        "source_sha256": source.source_sha256.lower(),
        "curriculum_level": level,
        "feature_values": [float(record[name]) for name in STAGE7G_E3_FEATURE_NAMES],
    }


def rebuild_development_all_disagreements(models: dict[str, object]) -> dict:
    manifest = json.loads((ROOT / "evidence" / "stage7g_c_r1_animetab_batch01_manifest.json").read_text())
    rows = []
    with TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for idx, item in enumerate(manifest["sources"], start=1):
            path = f"AnimeTAB/Entire songs/{item['filename']}"
            data = download(raw_github_url(ANIMETAB_REPO, ANIMETAB_REF, path))
            actual = sha256(data).hexdigest()
            if actual != item["sha256"]:
                raise AssertionError(f"AnimeTAB source SHA drift for {item['family_id']}: {actual}")
            local = tmp_root / f"{idx:02d}.xml"
            local.write_bytes(data)
            source = parse_target_free_musicxml(
                local,
                family_id=item["family_id"],
                tuning=manifest["tuning_midi"],
                pitch_mode=manifest["pitch_mode"],
                part_id=manifest["part_id"],
                staff_id=manifest["staff_id"],
            )
            for event_index, event in enumerate(source.events):
                row = feature_row(source, event, event_index, models)
                if row is not None:
                    rows.append(row)
    if len(rows) != EXPECTED_DEV_DISAGREEMENTS:
        raise AssertionError(f"development disagreement drift: {len(rows)}")
    ids = [row["event_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate development event id")
    return {
        "schema": "st-guitar-stage7g-e3-development-all-disagreement-features-v1",
        "teacher_labels_included": False,
        "source_sha_verified": True,
        "feature_count": len(STAGE7G_E3_FEATURE_NAMES),
        "feature_names": list(STAGE7G_E3_FEATURE_NAMES),
        "disagreement_events": len(rows),
        "rows": rows,
    }


def rebuild_e3e_internal_audit(models: dict[str, object]) -> dict:
    a1 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text())
    a2 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a2_family_selection_seal.json").read_text())
    corpus = a1["external_corpus"]
    by_family = {item["family_key"]: item for item in corpus["paths"]}
    sources = []
    origins = {}
    with TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for idx, selection in enumerate(a2["eligible_source_set"]["selections"], start=1):
            family = selection["family_key"]
            item = by_family[family]
            data = download(raw_github_url(corpus["repository"], corpus["repository_commit"], item["path"]))
            local = tmp_root / f"{idx:02d}.mxl"
            local.write_bytes(data)
            source = parse_target_free_mxl(
                local,
                family_id=family,
                tuning=STANDARD_TUNING_MIDI,
                pitch_mode=PITCH_MODE,
                part_id=selection["part_id"],
                staff_id=selection["staff_id"],
            )
            sources.append(source)
            origins[source.source_sha256.lower()] = (
                f"github:{corpus['repository']}@{corpus['repository_commit']}:{item['path']}"
            )
    pool = build_e3e_disagreement_pool(tuple(sources), source_origins=origins, specialist_models=models)
    batch = select_e3e_validation_batch(pool)
    audit = e3e_internal_audit(batch)
    actual = sha256(canonical_json_bytes(audit)).hexdigest()
    if actual != EXPECTED_E3E_AUDIT_SHA256:
        raise AssertionError(f"E3-E audit SHA drift: {actual}")
    return audit


def main() -> None:
    models, guard = reconstruct_frozen_open_low_compact_specialists()
    if guard["status"] != "PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION":
        raise AssertionError("specialist reconstruction failed")
    dev = rebuild_development_all_disagreements(models)
    e3e = rebuild_e3e_internal_audit(models)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "development_all_disagreement_features.json").write_bytes(canonical_json_bytes(dev))
    (OUT / "e3e_internal_audit_240.json").write_bytes(canonical_json_bytes(e3e))
    print(f"DEV_DISAGREEMENTS={dev['disagreement_events']}")
    print(f"E3E_SELECTED_EVENTS={e3e['selected_events']}")
    print(f"E3E_AUDIT_SHA256={sha256(canonical_json_bytes(e3e)).hexdigest()}")
    print("TEACHER_LABELS_INCLUDED=false")


if __name__ == "__main__":
    main()
