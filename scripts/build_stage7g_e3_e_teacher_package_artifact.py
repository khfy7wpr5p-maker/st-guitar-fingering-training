from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.request

from st_guitar_fingering_training.mxl_target_free import parse_target_free_mxl
from st_guitar_fingering_training.stage7g_e3_e_a2 import PITCH_MODE, STANDARD_TUNING_MIDI
from st_guitar_fingering_training.stage7g_e3_e_a3 import reconstruct_frozen_open_low_compact_specialists
from st_guitar_fingering_training.stage7g_e3_e_b import (
    build_e3e_disagreement_pool,
    canonical_json_bytes,
    e3e_internal_audit,
    e3e_response_template,
    e3e_teacher_manifest,
    e3e_teacher_package_bytes,
    select_e3e_validation_batch,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "ST_Guitar_E3E_Teacher_GOLD_240.zip"


def git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-e3e-b-artifact-v1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> None:
    a1 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text())
    a2 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a2_family_selection_seal.json").read_text())
    seal = json.loads((ROOT / "evidence" / "stage7g_e3_e_b_validation_batch_seal.json").read_text())
    corpus = a1["external_corpus"]
    by_family = {item["family_key"]: item for item in corpus["paths"]}
    selections = a2["eligible_source_set"]["selections"]
    if len(selections) != 31:
        raise AssertionError("E3-E package builder requires exact A2 31-family eligible set")

    sources = []
    origins = {}
    with TemporaryDirectory() as tmp:
        for index, selection in enumerate(selections, start=1):
            family = selection["family_key"]
            item = by_family[family]
            url = (
                f"https://raw.githubusercontent.com/{corpus['repository']}/"
                f"{corpus['repository_commit']}/{item['path']}"
            )
            data = download(url)
            if len(data) != item["bytes"]:
                raise AssertionError(f"byte-size drift for {family}")
            if git_blob_sha1(data) != item["git_blob_sha1"]:
                raise AssertionError(f"Git blob drift for {family}")
            local = Path(tmp) / f"{index:03d}.mxl"
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

    models, guard = reconstruct_frozen_open_low_compact_specialists()
    if guard["status"] != "PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION":
        raise AssertionError("frozen specialist reconstruction guard failed")

    pool = build_e3e_disagreement_pool(
        tuple(sources), source_origins=origins, specialist_models=models
    )
    batch = select_e3e_validation_batch(pool)
    manifest = e3e_teacher_manifest(batch)
    audit = e3e_internal_audit(batch)
    template = e3e_response_template(batch)
    package = e3e_teacher_package_bytes(batch)

    expected = seal["sealed_artifacts"]
    checks = {
        "teacher_manifest": sha256(canonical_json_bytes(manifest)).hexdigest(),
        "internal_audit": sha256(canonical_json_bytes(audit)).hexdigest(),
        "response_template": sha256(canonical_json_bytes(template)).hexdigest(),
    }
    for key, actual in checks.items():
        wanted = expected[key]["sha256"]
        if actual != wanted:
            raise AssertionError(f"{key} SHA-256 drift: {actual} != {wanted}")

    package_spec = expected["teacher_package"]
    package_sha = sha256(package).hexdigest()
    if len(package) != package_spec["bytes"]:
        raise AssertionError("Teacher package byte-size drift")
    if package_sha != package_spec["sha256"]:
        raise AssertionError(f"Teacher package SHA-256 drift: {package_sha}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(package)
    print(f"E3E_TEACHER_PACKAGE={OUTPUT}")
    print(f"E3E_TEACHER_PACKAGE_BYTES={len(package)}")
    print(f"E3E_TEACHER_PACKAGE_SHA256={package_sha}")


if __name__ == "__main__":
    main()
