from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import urllib.request

from st_guitar_fingering_training.mxl_target_free import parse_target_free_mxl
from st_guitar_fingering_training.stage7g_e3_e_a2 import (
    PITCH_MODE,
    STANDARD_TUNING_MIDI,
    select_target_free_part_staff,
)


ROOT = Path(__file__).resolve().parents[1]


def _git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "st-guitar-stage7g-e3-e-a2-selection-v1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


class Stage7GE3EA2LiveSelectionExecutionTests(unittest.TestCase):
    def test_live_selection_on_all_pinned_musetrainer_sources(self) -> None:
        manifest = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text(encoding="utf-8")
        )
        corpus = manifest["external_corpus"]
        repository = corpus["repository"]
        commit = corpus["repository_commit"]
        rows = []
        with TemporaryDirectory() as tmp:
            for index, item in enumerate(corpus["paths"], start=1):
                relative = item["path"]
                data = _download(
                    f"https://raw.githubusercontent.com/{repository}/{commit}/{relative}"
                )
                self.assertEqual(len(data), item["bytes"], relative)
                self.assertEqual(_git_blob_sha1(data), item["git_blob_sha1"], relative)
                local = Path(tmp) / f"{index:03d}.mxl"
                local.write_bytes(data)
                selection = select_target_free_part_staff(local)
                parsed = parse_target_free_mxl(
                    local,
                    family_id=f"e3e_musetrainer_{index:03d}",
                    tuning=STANDARD_TUNING_MIDI,
                    pitch_mode=PITCH_MODE,
                    part_id=selection.part_id,
                    staff_id=selection.staff_id,
                )
                self.assertEqual(parsed.source_sha256, selection.source_sha256)
                self.assertEqual(parsed.part_id, selection.part_id)
                self.assertEqual(parsed.selected_staff, selection.staff_id)
                self.assertTrue(parsed.events)
                rows.append(
                    {
                        "family_key": item["family_key"],
                        "source_path": relative,
                        "target_free_parse": "PASS",
                        **selection.as_dict(),
                    }
                )

        self.assertEqual(len(rows), 32)
        self.assertEqual(len({row["source_sha256"] for row in rows}), 32)
        self.assertTrue(all(row["target_free_parse"] == "PASS" for row in rows))
        print("E3E_A2_SELECTIONS_BEGIN")
        print(json.dumps(rows, ensure_ascii=False, sort_keys=True))
        print("E3E_A2_SELECTIONS_END")


if __name__ == "__main__":
    unittest.main()
