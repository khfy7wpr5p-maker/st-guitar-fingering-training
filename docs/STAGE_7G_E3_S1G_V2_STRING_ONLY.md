# Stage 7G-E3-S1-G v2 — STRING-only Full Reliability

Status: **FROZEN BEFORE V2 FULL-RELIABILITY FIRST PASS**  
Base main SHA: `ac146e9a5c6519a03e3650fe00b236c13fe90a7b`

## Decision

S1-E v2 pilot showed:
- `STRING_SKIP_PENALTY`: 16/16 exact, Cohen κ = 1.000 — retained.
- `OPEN_STRING_HAND_RELIEF`: retired as a context-free Teacher label.
- `OPEN_STRING_CONTROL_PENALTY`: retired as a context-free Teacher label.

Open-string geometry remains deterministic factual input (`open_note_count`, `fretted_note_count`, etc.). No further Teacher question is asked for open-string “relief” or “control” in this stage.

S1-G v1 remains immutable history and is **not executed**. V2 supersedes it operationally.

## Frozen v2 batch

- 20 STRING_DISTRIBUTION tasks only.
- 10 triads + 10 tetrads.
- 20 distinct interval families, max 1 task/family.
- Pilot-v2 family overlap: 0.
- Pair categories: 7× 0↔1 internal gaps, 7× 0↔≥2, 6× 1↔≥2.
- Every displayed option has zero open strings.
- Actual selected max fret: 8 (hard bound ≤12).
- All options physically valid under authoritative `valid_chord_voicings()`.

Question:

> Bu mevcut tel dağılımı, gereksiz tel atlaması yüzünden çalmayı belirgin biçimde zorlaştırıyor mu?

Answers: `YES / NO / UNSURE`.

## Reliability gate

Each task has A and B, therefore 40 aligned option ratings.

PASS requires all:
- exact ≥36/40 (90%)
- Cohen κ ≥0.80
- repeat UNSURE ≤4/40
- first-pass YES ≥5 and NO ≥5
- physical/manifest integrity 100%
- repeat start 24–72h after first-pass completion

REVIEW:
- exact 35/40, or
- 0.70≤κ<0.80, or
- repeat UNSURE 5–9/40, or
- insufficient first-pass YES/NO variance, or
- repeat start >72–168h.

FAIL:
- exact ≤34/40, or
- κ<0.70, or
- repeat UNSURE ≥10/40, or
- integrity failure, or
- repeat <24h / >168h.

## Training boundary

Full-reliability first-pass labels remain **QUARANTINED** until this v2 test PASSes and a separate training protocol is reviewed+merged with explicit approval. Repeat labels are reliability-only forever. S1-F fit stays hard-closed.

## SHA-256 commitments

Canonical protocol: `c5c73605de0d6cf03883172120ece281fbf08177889b12b3a156efaf08662895`  
Canonical source manifest: `080197afdf117c4fe25ec049e9e4e1e0de4189652ecab185ae660c32f3b25769`  
Canonical first manifest: `039afc78672d1bc63b07e5e700b91bb07dea2eca07d940bc649e28c34f65a89c`  
Canonical repeat manifest: `b8821d0c8412340ccec60ad76e3a5bd74fcbdd084023f76eec7fcdbd8696ab18`

The source semantic mapping and repeat manifest are withheld until needed for scoring/repeat blinding.
