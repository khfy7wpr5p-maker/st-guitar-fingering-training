# Stage 7G-E3-S1-H-C — Deterministic Standard Finger-Assignment Generator

Status: **PREREGISTERED BEFORE IMPLEMENTATION**  
Rule version: `S1-H-C.v1`

## Purpose

Convert every S1-H-B-retained voicing into the complete deterministic set of ordinary four-finger assignment candidates without learning or choosing a preferred fingering.

Pipeline:

`valid_chord_voicings()` → S1-H-A plausibility → S1-H-B fretting-resource feasibility → **S1-H-C standard finger assignments** → future ranking/model gate.

This stage enumerates possibilities. It does not decide which fingering is most natural.

## Input boundary

- S1-H-C recomputes S1-H-B from the pitch set and tuning.
- Only S1-H-B `RESOURCE_FEASIBLE` voicings may receive assignments.
- S1-H-A/S1-H-B pruned voicings remain audited and receive zero assignments.
- No voicing may be created, repaired, legalized, or reintroduced.

## Finger semantics

- open string → finger `0`;
- fretted note → one of fingers `1..4`;
- every S1-H-B fretting group receives exactly one distinct fretting finger;
- notes in the same S1-H-B group share that finger and the group's continuous-barre span;
- one fretting finger may not own two different S1-H-B groups;
- if group A is on a lower fret than group B, `finger(A) < finger(B)`;
- groups on the same fret have no frozen preference order and may use any distinct fingers.

The monotonic fret/finger rule is a standard simultaneous-fingering envelope, not a comfort ranking.

## Enumeration

For `N` S1-H-B groups (`0 <= N <= 4`):

1. enumerate every ordered choice of `N` distinct fingers from `1..4`;
2. reject assignments violating strict finger order across strictly increasing frets;
3. project group fingers back to every candidate note;
4. assign finger `0` to open strings;
5. emit continuous-barre metadata for every group spanning more than one string position;
6. deduplicate structurally identical assignments;
7. sort output deterministically and derive stable SHA-256 assignment IDs.

No score, heuristic preference, probability, Teacher label, or learned parameter participates.

## Output contract

Each assignment contains:

- stable `assignment_id`;
- exact `(pitch, string, fret, finger)` placements;
- explicit barre tuples `(finger, fret, span_start_string, span_end_string)`;
- source voicing candidate ID inherited from S1-H-A/H-B lineage.

Each retained voicing must produce at least one assignment. Zero assignments for a retained voicing is a fail-closed invariant error, not a silent prune.

## Required invariants

1. complete S1-H-B state is recomputed;
2. only H-B-retained voicings receive assignments;
3. every emitted note preserves pitch/string/fret exactly;
4. open strings always use finger 0;
5. fretted notes always use fingers 1..4;
6. every H-B group has exactly one finger;
7. different H-B groups use distinct fingers;
8. lower fret groups use lower-numbered fingers than higher fret groups;
9. barre metadata exactly matches H-B group spans;
10. assignment IDs are stable and unique per voicing;
11. output ordering is deterministic;
12. 10/10 repeated execution is identical;
13. no model, Teacher label, checkpoint, or production integration is opened.

## Explicit non-goals

S1-H-C does not decide:

- best/natural fingering;
- hand comfort or stretch quality;
- thumb-over or extended technique;
- transition/voice-leading preference;
- style/tone/resonance preference;
- player-specific anatomy;
- model ranking or checkpoint retention.

## Scientific boundary

This is the final deterministic candidate-expansion layer before a future learned fingering-ranking stage can be designed. S1-F real fit remains hard-closed and no real model development is authorized by this stage alone.