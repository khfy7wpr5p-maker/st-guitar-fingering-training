from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import urllib.request

from st_guitar_fingering_training.mxl_target_free import inspect_target_free_mxl
from st_guitar_fingering_training.stage7g_e3_d_execution import (
    STAGE7G_E3_D_EXPECTED_AUDIT_SHA256,
    STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256,
    read_stage7g_e3_package_json,
)


EXPECTED_SCHEMA = "st-guitar-stage7g-e3-e-a1-source-manifest-v1"
EXPECTED_STAGE = "7G-E3-E-A1"
EXPECTED_STATUS = "SOURCE_STRUCTURE_AUDIT_PENDING"


def git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-stage7g-e3-e-a1-v1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _load_json(path: str | Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected one JSON object")
    return value


def _development_quarantine(package_path: str | Path) -> tuple[set[str], set[str], set[str]]:
    audit, _ = read_stage7g_e3_package_json(package_path)
    rows = audit.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("sealed E3 development audit has no rows")
    source_hashes: set[str] = set()
    family_ids: set[str] = set()
    source_origins: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("sealed E3 development audit row must be an object")
        digest = row.get("source_sha256")
        family_id = row.get("family_id")
        origin = row.get("source_origin")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("sealed E3 development source SHA-256 is invalid")
        if not isinstance(family_id, str) or not family_id:
            raise ValueError("sealed E3 development family id is invalid")
        if not isinstance(origin, str) or not origin:
            raise ValueError("sealed E3 development source origin is invalid")
        source_hashes.add(digest.lower())
        family_ids.add(family_id)
        source_origins.add(origin)
    if len(family_ids) != 40 or len(source_hashes) != 40:
        raise ValueError("E3 development quarantine must reconstruct exactly 40 source families")
    return source_hashes, family_ids, source_origins


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Stage 7G-E3-E-A1 pinned MXL sources before any Teacher-GOLD or model scoring"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--development-package", required=True)
    parser.add_argument("--stage7e-seal", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    manifest = _load_json(args.manifest)
    if manifest.get("schema") != EXPECTED_SCHEMA or manifest.get("stage") != EXPECTED_STAGE:
        raise ValueError("unexpected E3-E-A1 source manifest schema/stage")
    if manifest.get("status") != EXPECTED_STATUS:
        raise ValueError("E3-E-A1 source manifest must remain result-pending")

    quarantine = manifest.get("quarantine_inputs")
    if not isinstance(quarantine, dict):
        raise ValueError("E3-E-A1 manifest is missing quarantine inputs")
    if quarantine.get("development_package_sha256") != STAGE7G_E3_D_EXPECTED_PACKAGE_SHA256:
        raise ValueError("E3-E-A1 manifest references the wrong E3 development package")
    if quarantine.get("development_audit_sha256") != STAGE7G_E3_D_EXPECTED_AUDIT_SHA256:
        raise ValueError("E3-E-A1 manifest references the wrong E3 development audit")
    development_hashes, development_family_ids, development_origins = _development_quarantine(
        args.development_package
    )

    stage7e = _load_json(args.stage7e_seal)
    final_corpus = stage7e.get("external_corpus")
    if not isinstance(final_corpus, dict):
        raise ValueError("Stage 7E seal has no external corpus")
    final_blob_hashes = {
        str(item.get("git_blob_sha1"))
        for item in final_corpus.get("paths", [])
        if isinstance(item, dict)
    }
    if len(final_blob_hashes) != 16:
        raise ValueError("Stage 7E quarantine must contain exactly 16 sealed source blobs")

    corpus = manifest.get("external_corpus")
    if not isinstance(corpus, dict):
        raise ValueError("E3-E-A1 manifest has no external corpus")
    repository = str(corpus.get("repository") or "")
    commit = str(corpus.get("repository_commit") or "")
    prefix = str(corpus.get("path_prefix") or "")
    provenance = corpus.get("provenance")
    paths = corpus.get("paths")
    if not repository or len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        raise ValueError("E3-E-A1 external corpus must pin a repository and full commit SHA")
    if repository == final_corpus.get("repository"):
        raise ValueError("E3-E-A1 repository reuses the Stage 7E source repository")
    if not isinstance(provenance, dict) or provenance.get("commercial_or_production_clearance") is not False:
        raise ValueError("E3-E-A1 provenance must explicitly remain non-production")
    if provenance.get("research_use_status") != "RESEARCH_ONLY_FROM_REPOSITORY_PUBLIC_DOMAIN_CLAIM":
        raise ValueError("E3-E-A1 source provenance status is not the frozen research-only claim")
    if not isinstance(paths, list) or len(paths) < 30:
        raise ValueError("E3-E-A1 requires at least 30 pinned candidate source families")

    path_names = [row.get("path") for row in paths if isinstance(row, dict)]
    family_keys = [row.get("family_key") for row in paths if isinstance(row, dict)]
    blob_hashes = [row.get("git_blob_sha1") for row in paths if isinstance(row, dict)]
    if len(path_names) != len(paths) or len(set(path_names)) != len(paths):
        raise ValueError("E3-E-A1 source paths must be unique and complete")
    if len(family_keys) != len(paths) or any(not isinstance(key, str) or not key for key in family_keys):
        raise ValueError("E3-E-A1 family keys must be non-empty strings")
    if len(set(family_keys)) != len(paths):
        raise ValueError("E3-E-A1 manifest contains duplicate family keys")
    if len(blob_hashes) != len(paths) or len(set(blob_hashes)) != len(paths):
        raise ValueError("E3-E-A1 source Git blobs must be unique")
    if any(not isinstance(path, str) or not path.startswith(prefix) or not path.endswith(".mxl") for path in path_names):
        raise ValueError("E3-E-A1 sources must be pinned MXL files under the frozen prefix")

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    source_rows = []
    seen_sha256: set[str] = set()
    development_source_overlap = 0
    stage7e_blob_overlap = 0

    for index, item in enumerate(paths, start=1):
        relative = str(item["path"])
        expected_blob = str(item["git_blob_sha1"])
        expected_bytes = int(item["bytes"])
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{relative}"
        data = _download(url)
        if len(data) != expected_bytes:
            raise ValueError(f"byte-size mismatch for {relative}")
        actual_blob = git_blob_sha1(data)
        if actual_blob != expected_blob:
            raise ValueError(f"Git blob SHA-1 mismatch for {relative}")
        if actual_blob in final_blob_hashes:
            stage7e_blob_overlap += 1
            raise ValueError(f"source blob overlaps Stage 7E: {relative}")
        digest = sha256(data).hexdigest()
        if digest in seen_sha256:
            raise ValueError(f"duplicate E3-E-A1 source SHA-256: {relative}")
        seen_sha256.add(digest)
        if digest in development_hashes:
            development_source_overlap += 1
            raise ValueError(f"source SHA-256 overlaps E3 development: {relative}")

        local = work / f"{index:03d}.mxl"
        local.write_bytes(data)
        structure = inspect_target_free_mxl(local)
        if structure.source_sha256 != digest:
            raise AssertionError("MXL structure audit source identity drift")
        source_rows.append({
            "family_id": f"e3e_musetrainer_{index:03d}",
            "family_key": item["family_key"],
            "source_path": relative,
            "source_origin": f"github:{repository}@{commit}:{relative}",
            "git_blob_sha1": actual_blob,
            "source_sha256": digest,
            "bytes": len(data),
            "structure": structure.as_dict(),
        })

    single_part = sum(len(row["structure"]["part_ids"]) == 1 for row in source_rows)
    multi_part = len(source_rows) - single_part
    multi_staff_parts = sum(
        any(len(part["staff_ids"]) > 1 for part in row["structure"]["staff_ids_by_part"])
        for row in source_rows
    )
    report = {
        "schema": "st-guitar-stage7g-e3-e-a1-source-structure-report-v1",
        "stage": EXPECTED_STAGE,
        "status": "STRUCTURE_AUDIT_PASS_FAMILY_DISJOINTNESS_NOT_YET_SEALED",
        "repository": repository,
        "repository_commit": commit,
        "provenance": provenance,
        "source_file_count": len(source_rows),
        "candidate_family_count": len(source_rows),
        "single_part_sources": single_part,
        "multi_part_sources": multi_part,
        "sources_with_multi_staff_part": multi_staff_parts,
        "development_quarantine": {
            "sealed_source_hashes": len(development_hashes),
            "sealed_family_ids": len(development_family_ids),
            "sealed_source_origins": len(development_origins),
            "exact_source_sha256_overlap": development_source_overlap,
        },
        "stage7e_quarantine": {
            "sealed_git_blobs": len(final_blob_hashes),
            "exact_git_blob_overlap": stage7e_blob_overlap,
            "semantic_family_overlap_status": "PENDING_RECONSTRUCTION_FROM_PINNED_STAGE7E_SOURCES"
        },
        "family_identity_gate": "PENDING_CONSERVATIVE_SEMANTIC_FAMILY_AUDIT",
        "part_staff_selection_policy": "NOT_YET_FROZEN",
        "sources": source_rows,
        "safety": {
            "contains_teacher_gold_labels": False,
            "teacher_gold_answers_read": False,
            "specialist_scored": False,
            "router_scored": False,
            "model_fit": False,
            "threshold_selected": False,
            "checkpoint_retained": False,
            "production_integration": False,
            "stage7e_used_for_modeling": False,
            "raw_external_mxl_committed_to_training_repo": False,
        },
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "source_file_count": report["source_file_count"],
        "single_part_sources": single_part,
        "multi_part_sources": multi_part,
        "sources_with_multi_staff_part": multi_staff_parts,
        "development_source_sha256_overlap": development_source_overlap,
        "stage7e_exact_git_blob_overlap": stage7e_blob_overlap,
        "family_identity_gate": report["family_identity_gate"],
        "contains_teacher_gold_labels": False,
        "specialist_scored": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
