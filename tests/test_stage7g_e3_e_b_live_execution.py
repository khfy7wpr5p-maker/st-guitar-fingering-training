from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
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


def _git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-e3e-b-seal-v1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


class Stage7GE3EBLiveExecutionTests(unittest.TestCase):
    def test_pinned_240_task_validation_seal(self) -> None:
        a1 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text())
        a2 = json.loads((ROOT / "evidence" / "stage7g_e3_e_a2_family_selection_seal.json").read_text())
        corpus = a1["external_corpus"]
        by_family = {item["family_key"]: item for item in corpus["paths"]}
        selections = a2["eligible_source_set"]["selections"]
        self.assertEqual(len(selections), 31)

        sources = []
        origins = {}
        with TemporaryDirectory() as tmp:
            for index, selection in enumerate(selections, start=1):
                family = selection["family_key"]
                item = by_family[family]
                data = _download(
                    f"https://raw.githubusercontent.com/{corpus['repository']}/{corpus['repository_commit']}/{item['path']}"
                )
                self.assertEqual(len(data), item["bytes"])
                self.assertEqual(_git_blob_sha1(data), item["git_blob_sha1"])
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
        pool = build_e3e_disagreement_pool(tuple(sources), source_origins=origins, specialist_models=models)
        batch = select_e3e_validation_batch(pool)
        manifest = e3e_teacher_manifest(batch)
        audit = e3e_internal_audit(batch)
        template = e3e_response_template(batch)
        package = e3e_teacher_package_bytes(batch)
        result = {
            "specialist_reconstruction_status": guard["status"],
            "pool_events": len(pool),
            "pool_families": len({item.task.family_id for item in pool}),
            "selected_tasks": len(batch),
            "selected_families": len({item.task.family_id for item in batch}),
            "selected_level_counts": audit["level_counts"],
            "selected_family_count_min": min(audit["family_counts"].values()),
            "selected_family_count_max": max(audit["family_counts"].values()),
            "selected_event_id_set_sha256": sha256(
                "\n".join(sorted(item.task.event_id for item in batch)).encode()
            ).hexdigest(),
            "teacher_manifest_sha256": sha256(canonical_json_bytes(manifest)).hexdigest(),
            "internal_audit_sha256": sha256(canonical_json_bytes(audit)).hexdigest(),
            "response_template_sha256": sha256(canonical_json_bytes(template)).hexdigest(),
            "teacher_package_sha256": sha256(package).hexdigest(),
            "teacher_package_bytes": len(package),
            "evaluation_gate": audit["evaluation_gate"],
            "teacher_answers_read": False,
            "e3e_model_fit": False,
            "threshold_search_on_e3e": False,
            "checkpoint_retained": False,
            "production_integration": False,
        }
        print("E3E_B_SEAL_RESULT_BEGIN")
        print(json.dumps(result, sort_keys=True))
        print("E3E_B_SEAL_RESULT_END")


if __name__ == "__main__":
    unittest.main()
