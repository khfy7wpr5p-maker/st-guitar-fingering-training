from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import urllib.request

from st_guitar_fingering_training.mxl_target_free import parse_target_free_mxl
from st_guitar_fingering_training.stage7g_e3_e_a2 import PITCH_MODE, STANDARD_TUNING_MIDI
from st_guitar_fingering_training.stage7g_e3_e_a3 import (
    build_open_low_compact_disagreement_inventory,
    reconstruct_frozen_open_low_compact_specialists,
)


ROOT = Path(__file__).resolve().parents[1]


def _git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "st-guitar-stage7g-e3-e-a3-inventory-v1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


class Stage7GE3EA3LiveExecutionTests(unittest.TestCase):
    def test_pinned_31_family_disagreement_inventory(self) -> None:
        a1 = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text(encoding="utf-8")
        )
        a2 = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a2_family_selection_seal.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            a2["status"],
            "FAMILY_DISJOINTNESS_PASS_SELECTION_POLICY_FROZEN_31_ELIGIBLE",
        )
        self.assertEqual(a2["eligible_source_set"]["eligible_families"], 31)
        self.assertEqual(
            a2["next_gate"],
            "ELIGIBLE_FOR_FROZEN_SPECIALIST_RECONSTRUCTION_AND_OPEN_LOW_COMPACT_DISAGREEMENT_INVENTORY_NO_TEACHER_GOLD",
        )

        corpus = a1["external_corpus"]
        by_family = {item["family_key"]: item for item in corpus["paths"]}
        selections = a2["eligible_source_set"]["selections"]
        self.assertEqual(len(selections), 31)
        self.assertEqual(len({item["family_key"] for item in selections}), 31)
        self.assertNotIn(
            "chopin_ballade1_op23",
            {item["family_key"] for item in selections},
        )

        sources = []
        with TemporaryDirectory() as tmp:
            for index, selection in enumerate(selections, start=1):
                family_key = selection["family_key"]
                manifest_item = by_family[family_key]
                relative = manifest_item["path"]
                data = _download(
                    f"https://raw.githubusercontent.com/{corpus['repository']}/{corpus['repository_commit']}/{relative}"
                )
                self.assertEqual(len(data), manifest_item["bytes"], relative)
                self.assertEqual(_git_blob_sha1(data), manifest_item["git_blob_sha1"], relative)
                local = Path(tmp) / f"{index:03d}.mxl"
                local.write_bytes(data)
                source = parse_target_free_mxl(
                    local,
                    family_id=family_key,
                    tuning=STANDARD_TUNING_MIDI,
                    pitch_mode=PITCH_MODE,
                    part_id=selection["part_id"],
                    staff_id=selection["staff_id"],
                )
                sources.append(source)

        models, guard = reconstruct_frozen_open_low_compact_specialists()
        report = build_open_low_compact_disagreement_inventory(
            tuple(sources),
            specialist_models=models,
        )
        self.assertEqual(report["eligible_families"], 31)
        self.assertEqual(report["status"], "TARGET_BLIND_OPEN_LOW_COMPACT_INVENTORY_COMPLETE")
        self.assertFalse(report["teacher_gold_generated"])
        self.assertFalse(report["teacher_gold_answers_read"])
        self.assertFalse(report["e3e_model_fit"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])

        print("E3E_A3_RESULT_BEGIN")
        print(json.dumps({"reconstruction_guard": guard, "inventory": report}, sort_keys=True))
        print("E3E_A3_RESULT_END")


if __name__ == "__main__":
    unittest.main()
