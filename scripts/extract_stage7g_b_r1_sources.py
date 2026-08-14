from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import urllib.request

import guitarpro

from st_guitar_fingering_training.dataset import valid_chord_voicings


def git_blob_sha1(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "st-guitar-stage7g-b-r1-v1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _track_tuning(track) -> dict[int, int] | None:
    if bool(getattr(track, "isPercussionTrack", False)):
        return None
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
    observed_missing_from_candidates = 0
    single_candidate_chords = 0

    for track_index, track in enumerate(song.tracks):
        tuning_by_string = _track_tuning(track)
        if tuning_by_string is None:
            continue
        eligible_tracks += 1
        tuning = tuple(tuning_by_string[index] for index in range(1, 7))

        for measure_index, measure in enumerate(track.measures):
            for voice_index, voice in enumerate(measure.voices):
                for beat_index, beat in enumerate(voice.beats):
                    notes = tuple(beat.notes)
                    if len(notes) < 2:
                        continue
                    try:
                        placements = tuple(sorted(
                            (
                                tuning_by_string[int(note.string)] + int(note.value),
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

                    pitches = tuple(sorted(pitch for pitch, _, _ in placements))
                    candidates = valid_chord_voicings(pitches, tuning)
                    if placements not in candidates:
                        observed_missing_from_candidates += 1
                        continue
                    if len(candidates) < 2:
                        single_candidate_chords += 1
                        continue

                    events.append({
                        "event_id": f"{family_id}:t{track_index}:m{measure_index}:v{voice_index}:b{beat_index}",
                        "track_index": track_index,
                        "measure_index": measure_index,
                        "voice_index": voice_index,
                        "beat_index": beat_index,
                        "tuning": list(tuning),
                        "pitches_midi": list(pitches),
                        "candidate_count": len(candidates),
                        "source_observed_voicing_internal_only": [list(item) for item in placements],
                    })

    return {
        "family_id": family_id,
        "eligible_tracks": eligible_tracks,
        "eligible_ambiguous_chord_events": len(events),
        "single_candidate_chords_excluded": single_candidate_chords,
        "unsupported_chord_beats": unsupported_chord_beats,
        "observed_missing_from_deterministic_candidates": observed_missing_from_candidates,
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract pinned Stage 7G-B-R1 source fixtures without model scoring")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--stage7e-seal", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("status") != "SOURCE_INTAKE_PENDING" or manifest.get("stage") != "7G-B-R1":
        raise ValueError("Stage 7G-B-R1 requires a pending source-intake manifest")

    corpus = manifest["external_corpus"]
    if corpus["repository"] != "CoderLine/alphaTab" or corpus["license"] != "MPL-2.0":
        raise ValueError("unexpected Stage 7G-B-R1 source repository or license")
    commit = str(corpus["repository_commit"])
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        raise ValueError("source repository must be pinned to a full commit SHA")

    paths = tuple(str(path) for path in corpus["paths"])
    excluded = set(str(path) for path in corpus.get("explicitly_excluded", ()))
    prefix = str(corpus["path_prefix"])
    if len(paths) < 30 or len(paths) != len(set(paths)):
        raise ValueError("Stage 7G-B-R1 source intake requires at least 30 unique allowlisted fixture files")
    if set(paths) & excluded:
        raise ValueError("an explicitly excluded source entered the allowlist")
    if any(not path.startswith(prefix) or not path.endswith(".gp5") for path in paths):
        raise ValueError("all Stage 7G-B-R1 sources must be allowlisted GP5 fixtures under the pinned path prefix")

    stage7e = json.loads(Path(args.stage7e_seal).read_text(encoding="utf-8"))
    final_corpus = stage7e["external_corpus"]
    if final_corpus["repository"] == corpus["repository"]:
        raise ValueError("Stage 7G-B-R1 source repository overlaps the Stage 7E final repository")
    final_blob_hashes = {str(item["git_blob_sha1"]) for item in final_corpus["paths"]}

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    families = []
    source_files = []
    seen_sha256: set[str] = set()
    final_blob_overlap = 0

    owner_repo = corpus["repository"]
    for index, relative in enumerate(paths, start=1):
        url = f"https://raw.githubusercontent.com/{owner_repo}/{commit}/{relative}"
        data = _download(url)
        blob = git_blob_sha1(data)
        digest = sha256(data).hexdigest()
        if blob in final_blob_hashes:
            final_blob_overlap += 1
            raise ValueError(f"source blob overlaps Stage 7E final corpus: {relative}")
        if digest in seen_sha256:
            raise ValueError(f"duplicate Stage 7G-B-R1 source SHA-256: {relative}")
        seen_sha256.add(digest)

        local = work / f"{index:03d}.gp5"
        local.write_bytes(data)
        family_id = f"stage7g_alpha_{index:03d}"
        family = extract_song(local, family_id)
        family["source_path"] = relative
        family["source_origin"] = f"github:{owner_repo}@{commit}:{relative}"
        family["git_blob_sha1"] = blob
        family["source_sha256"] = digest
        families.append(family)
        source_files.append({
            "path": relative,
            "git_blob_sha1": blob,
            "sha256": digest,
            "bytes": len(data),
        })

    report = {
        "schema": "st-guitar-stage7g-b-r1-source-intake-report-v1",
        "stage": "7G-B-R1",
        "status": "SOURCE_INTAKE_EXTRACTED",
        "contains_model_metrics": False,
        "contains_teacher_gold_labels": False,
        "repository": owner_repo,
        "repository_commit": commit,
        "license": corpus["license"],
        "source_files": source_files,
        "source_file_count": len(source_files),
        "families": families,
        "family_count": len(families),
        "families_with_eligible_ambiguous_chords": sum(
            family["eligible_ambiguous_chord_events"] > 0 for family in families
        ),
        "eligible_ambiguous_chord_events": sum(
            family["eligible_ambiguous_chord_events"] for family in families
        ),
        "single_candidate_chords_excluded": sum(
            family["single_candidate_chords_excluded"] for family in families
        ),
        "unsupported_chord_beats": sum(family["unsupported_chord_beats"] for family in families),
        "observed_missing_from_deterministic_candidates": sum(
            family["observed_missing_from_deterministic_candidates"] for family in families
        ),
        "stage7e_final_blob_overlap": final_blob_overlap,
        "safety": {
            "specialist_scored": False,
            "router_scored": False,
            "teacher_gold_labels_generated": False,
            "source_observed_voicing_used_for_sampling": False,
            "checkpoint_retained": False,
            "production_integration": False,
            "raw_gp5_committed_to_training_repo": False,
        },
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "source_file_count": report["source_file_count"],
        "family_count": report["family_count"],
        "families_with_eligible_ambiguous_chords": report["families_with_eligible_ambiguous_chords"],
        "eligible_ambiguous_chord_events": report["eligible_ambiguous_chord_events"],
        "observed_missing_from_deterministic_candidates": report["observed_missing_from_deterministic_candidates"],
        "stage7e_final_blob_overlap": report["stage7e_final_blob_overlap"],
        "contains_model_metrics": False,
        "contains_teacher_gold_labels": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
