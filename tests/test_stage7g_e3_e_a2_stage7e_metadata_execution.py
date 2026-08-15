from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import struct
import unittest
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPOSITORY = "robust-guitar-tabs/code"
EXPECTED_COMMIT = "f50309ad06dc734ddae5e3a0eda756fca221e2e7"
EXPECTED_VERSION = "FICHIER GUITAR PRO v3.00"
DUMMY_PREFIX = "GuitarProConversor/DummyTabs/"
FIELDS = (
    "title",
    "subtitle",
    "artist",
    "album",
    "words",
    "copyright",
    "tabbed_by",
    "instructions",
)


def _git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "st-guitar-stage7g-e3-e-a2-metadata-audit-v1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _download_json(url: str):
    return json.loads(_download(url).decode("utf-8"))


def _take(data: bytes, offset: int, count: int) -> tuple[bytes, int]:
    if count < 0 or offset < 0 or offset + count > len(data):
        raise ValueError("GP3 header is truncated")
    return data[offset : offset + count], offset + count


def _i32(data: bytes, offset: int) -> tuple[int, int]:
    raw, offset = _take(data, offset, 4)
    return struct.unpack("<i", raw)[0], offset


def _byte_size_string(data: bytes, offset: int, count: int) -> tuple[str, int]:
    if count < 0 or count > 255:
        raise ValueError("invalid GP3 byte-size-string bound")
    raw_size, offset = _take(data, offset, 1)
    size = raw_size[0]
    if size > count:
        raise ValueError("GP3 byte-size-string length exceeds fixed field")
    raw, offset = _take(data, offset, count)
    return raw[:size].decode("cp1252"), offset


def _int_byte_size_string(data: bytes, offset: int) -> tuple[str, int]:
    count, offset = _i32(data, offset)
    if count < 1 or count > 256:
        raise ValueError("invalid GP3 int-byte-size-string count")
    return _byte_size_string(data, offset, count - 1)


def _read_metadata_prefix(data: bytes) -> dict:
    version, offset = _byte_size_string(data, 0, 30)
    if version != EXPECTED_VERSION:
        raise ValueError(f"unexpected GP3 version: {version!r}")

    values = {}
    for field in FIELDS:
        values[field], offset = _int_byte_size_string(data, offset)

    notice_count, offset = _i32(data, offset)
    if notice_count < 0 or notice_count > 1000:
        raise ValueError("invalid GP3 notice-line count")
    for _ in range(notice_count):
        _, offset = _int_byte_size_string(data, offset)

    # Deliberately stop here. No triplet/tempo/key/MIDI/measure/track/note bytes
    # are interpreted by this semantic-quarantine audit.
    values["version"] = version
    values["metadata_prefix_bytes_read"] = offset
    values["musical_content_parsed"] = False
    return values


def _generator_source_path(path: str) -> bool:
    if not path.startswith(DUMMY_PREFIX):
        return False
    # Mirrors the effective MasterExtraction.ipynb predicate: the notebook's
    # .gp5 clause is unsatisfiable because file.split('.') is a list.
    return path.endswith((".gp", ".gp2", ".gp3", ".gp4"))


class Stage7GE3EA2Stage7EMetadataExecutionTests(unittest.TestCase):
    def test_stage7e_semantic_metadata_only(self) -> None:
        seal = json.loads(
            (ROOT / "evidence" / "stage7e_final_test_seal.json").read_text(encoding="utf-8")
        )
        corpus = seal["external_corpus"]
        self.assertEqual(corpus["repository"], EXPECTED_REPOSITORY)
        self.assertEqual(corpus["repository_commit"], EXPECTED_COMMIT)
        self.assertEqual(len(corpus["paths"]), 16)

        rows = []
        for item in corpus["paths"]:
            path = item["path"]
            url = f"https://raw.githubusercontent.com/{EXPECTED_REPOSITORY}/{EXPECTED_COMMIT}/{path}"
            data = _download(url)
            self.assertEqual(len(data), item["bytes"], path)
            self.assertEqual(_git_blob_sha1(data), item["git_blob_sha1"], path)
            metadata = _read_metadata_prefix(data)
            self.assertFalse(metadata["musical_content_parsed"])
            rows.append(
                {
                    "path": path,
                    "git_blob_sha1": item["git_blob_sha1"],
                    **metadata,
                }
            )

        print("STAGE7E_METADATA_AUDIT_BEGIN")
        print(json.dumps(rows, ensure_ascii=False, sort_keys=True))
        print("STAGE7E_METADATA_AUDIT_END")
        self.assertEqual(len(rows), 16)

    def test_generator_source_path_inventory_only(self) -> None:
        tree_url = (
            f"https://api.github.com/repos/{EXPECTED_REPOSITORY}/git/trees/"
            f"{EXPECTED_COMMIT}?recursive=1"
        )
        tree = _download_json(tree_url)
        self.assertEqual(tree["sha"], EXPECTED_COMMIT)
        self.assertFalse(tree.get("truncated", False))
        rows = tree.get("tree")
        self.assertIsInstance(rows, list)

        source_paths = sorted(
            item["path"]
            for item in rows
            if isinstance(item, dict)
            and item.get("type") == "blob"
            and isinstance(item.get("path"), str)
            and _generator_source_path(item["path"])
        )
        self.assertTrue(source_paths)
        self.assertEqual(len(source_paths), len(set(source_paths)))

        print("STAGE7E_GENERATOR_SOURCE_PATHS_BEGIN")
        print(json.dumps(source_paths, ensure_ascii=False))
        print("STAGE7E_GENERATOR_SOURCE_PATHS_END")


if __name__ == "__main__":
    unittest.main()
