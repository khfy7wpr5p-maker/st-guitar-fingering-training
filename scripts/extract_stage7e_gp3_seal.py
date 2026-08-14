from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import urllib.request

import guitarpro


def git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-stage7e-seal-v1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _track_tuning(track) -> dict[int, int] | None:
    strings = tuple(track.strings)
    numbers = sorted(int(item.number) for item in strings)
    if numbers != [1, 2, 3, 4, 5, 6]:
        return None
    tuning = {int(item.number): int(item.value) for item in strings}
    if any(not 0 <= value <= 127 for value in tuning.values()):
        return None
    return tuning


def extract_song(path: Path, family_id: str) -> dict:
    song = guitarpro.parse(str(path))
    events = []
    eligible_tracks = 0
    unsupported_chord_beats = 0

    for track_index, track in enumerate(song.tracks):
        if bool(getattr(track, "isPercussionTrack", False)):
            continue
        tuning = _track_tuning(track)
        if tuning is None:
            continue
        eligible_tracks += 1

        for measure_index, measure in enumerate(track.measures):
            for voice_index, voice in enumerate(measure.voices):
                for beat_index, beat in enumerate(voice.beats):
                    notes = tuple(beat.notes)
                    if len(notes) < 2:
                        continue
                    try:
                        placements = tuple(sorted(
                            (
                                tuning[int(note.string)] + int(note.value),
                                int(note.string),
                                int(note.value),
                            )
                            for note in notes
                        ))
                    except (KeyError, TypeError, ValueError):
                        unsupported_chord_beats += 1
                        continue
                    strings = [string for _, string, _ in placements]
                    frets = [fret for _, _, fret in placements]
                    if len(set(strings)) != len(strings) or any(not 0 <= fret <= 24 for fret in frets):
                        unsupported_chord_beats += 1
                        continue
                    events.append({
                        "event_id": f"{family_id}:t{track_index}:m{measure_index}:v{voice_index}:b{beat_index}",
                        "track_index": track_index,
                        "measure_index": measure_index,
                        "voice_index": voice_index,
                        "beat_index": beat_index,
                        "tuning": [tuning[index] for index in range(1, 7)],
                        "placements": [list(item) for item in placements],
                    })

    return {
        "family_id": family_id,
        "title": str(getattr(song, "title", "") or ""),
        "artist": str(getattr(song, "artist", "") or ""),
        "eligible_tracks": eligible_tracks,
        "unsupported_chord_beats": unsupported_chord_beats,
        "eligible_chord_events": len(events),
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract the sealed Stage 7E GP3 corpus without model scoring")
    parser.add_argument("--seal", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    seal = json.loads(Path(args.seal).read_text(encoding="utf-8"))
    if seal.get("status") != "SEALED_RESULT_PENDING":
        raise ValueError("Stage 7E extraction requires a sealed, result-pending manifest")
    corpus = seal["external_corpus"]
    if corpus["repository"] != "robust-guitar-tabs/code":
        raise ValueError("unexpected final-test repository")
    commit = corpus["repository_commit"]
    paths = corpus["paths"]
    if len(paths) != 16 or len({item["git_blob_sha1"] for item in paths}) != 16:
        raise ValueError("Stage 7E requires exactly 16 unique sealed GP3 blobs")

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    families = []
    downloaded = []
    for index, item in enumerate(paths, start=1):
        relative = item["path"]
        url = f"https://raw.githubusercontent.com/robust-guitar-tabs/code/{commit}/{relative}"
        data = _download(url)
        if len(data) != int(item["bytes"]):
            raise ValueError(f"byte-size mismatch for {relative}")
        actual_blob = git_blob_sha1(data)
        if actual_blob != item["git_blob_sha1"]:
            raise ValueError(f"Git blob mismatch for {relative}")
        local = work / Path(relative).name
        local.write_bytes(data)
        family_id = f"final_gp3_{Path(relative).stem.zfill(2)}"
        family = extract_song(local, family_id)
        family["source_path"] = relative
        family["git_blob_sha1"] = actual_blob
        family["source_sha256"] = sha256(data).hexdigest()
        families.append(family)
        downloaded.append({
            "path": relative,
            "git_blob_sha1": actual_blob,
            "sha256": family["source_sha256"],
            "bytes": len(data),
        })

    report = {
        "schema": "st-guitar-stage7e-sealed-gp3-extraction-v1",
        "stage": "7E",
        "contains_model_metrics": False,
        "repository": corpus["repository"],
        "repository_commit": commit,
        "source_files": downloaded,
        "source_file_count": len(downloaded),
        "families": families,
        "family_count": len(families),
        "families_with_eligible_chords": sum(item["eligible_chord_events"] > 0 for item in families),
        "eligible_chord_events": sum(item["eligible_chord_events"] for item in families),
        "unsupported_chord_beats": sum(item["unsupported_chord_beats"] for item in families),
        "safety": {
            "router_scored": False,
            "specialist_scored": False,
            "final_targets_used_for_fit": False,
            "checkpoint_retained": False,
            "production_integration": False,
        },
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "family_count": report["family_count"],
        "families_with_eligible_chords": report["families_with_eligible_chords"],
        "eligible_chord_events": report["eligible_chord_events"],
        "unsupported_chord_beats": report["unsupported_chord_beats"],
        "contains_model_metrics": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
