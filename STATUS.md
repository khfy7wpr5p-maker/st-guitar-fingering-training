# Status

## Current repository truth

- Default branch: `main`
- Verified current `main`: `1a8acf654f21d36c928fdd45b3a21a443b6ebe5a`
- Latest merged stage: **Stage 7G-E3-S1-H-A** via PR #71
- PR #71 CI on final head: ✅ `ci` run #189 succeeded
- Open draft PR #70: **not merged**, based on older `main`, currently diverged from `main`

## Foundation and historical research

- Stage 0 — Safety + architecture baseline: ✅
- Stage 1 — Dataset Contract v1: ✅
- Stage 2 — Guitar Pro/MusicXML intake + normalizer: ✅
- Stage 3 — deterministic physical validation + extraction: ✅
- Stage 4 — Dataset Builder v1: ✅
- Stage 5 — bounded single-note research training: ✅ executed; no retained production checkpoint
- Stage 6 — chord-voicing specialist/context research: ✅ completed as research
- Stage 7D/7E — target-blind routing and untouched evaluation: ✅ completed; Stage 7E permanently consumed/evaluation-only
- Stage 7G-E1/E2/E3 — Teacher-GOLD ergonomics research: ✅ completed through positive/negative diagnostics and consumed untouched E3-E evidence

## Teacher reliability redesign

Earlier single A/B “more natural” supervision failed the frozen repeat-reliability standard. Independent per-option component scoring then produced architecture-design signal, but this did not authorize direct specialist training.

Historical S1-A/B/C/D-era documents remain useful as evidence, but they are no longer the current execution position.

## Stage 7G-E3-S1-F — component-training preparation

Status: ✅ **MERGED PREPARATION ONLY**

- fixed target-blind feature contract;
- exact provenance checks;
- deterministic family-safe evaluation structure;
- fixed baseline model shape;
- real project-label fitting remains **HARD-CLOSED**;
- no checkpoint or integration authorization.

## Stage 7G-E3-S1-G v1

Status: ✅ **MERGED / IMMUTABLE HISTORICAL PREREGISTRATION**

S1-G v1 is retained as frozen historical evidence and is not rewritten to match later architecture decisions.

## Open PR #70 — S1-G v2 STRING-only

Status: 🟡 **OPEN DRAFT / NOT REPOSITORY TRUTH**

- head: `96390b1b626e0769a554f8b031e8f19d65ab40c9`
- base recorded by PR: `ac146e9a5c6519a03e3650fe00b236c13fe90a7b`
- current `main`: `1a8acf654f21d36c928fdd45b3a21a443b6ebe5a`
- compare against current main: branch is 3 commits ahead and 9 commits behind

PR #70 must therefore be reviewed as a stale/diverged proposal. It must not be merged mechanically or cited as current merged architecture without reconciliation.

## Stage 7G-E3-S1-H-A — deterministic guitaristic plausibility

Status: ✅ **MERGED**

PR #71 merged at `1a8acf654f21d36c928fdd45b3a21a443b6ebe5a`.

Implemented invariants:

- `valid_chord_voicings()` remains the sole physical authority;
- analyzer requires the complete authoritative candidate set;
- non-authoritative, duplicate, or incomplete raw candidate inputs fail closed;
- raw physically-valid candidates remain preserved for audit;
- stable candidate IDs and deterministic reason codes;
- classes: `PLAUSIBLE`, `BORDERLINE`, `DOMINATED`, `IMPRACTICAL`;
- only v1 hard prune: `H001_MIN_FINGER_PROXY_GE_6`;
- five distinct positive fret values are `BORDERLINE` and retained;
- same-topology mechanical `DOMINATED` candidates are diagnostic-only and retained;
- open strings, high fret, internal gaps, lower position, tone/resonance, and musical preference are not single-factor prune rules;
- true all-authoritative-candidates-pruned state is explicit as `NO_PLAUSIBLE_CANDIDATE`.

Focused S1-H-A test matrix contains 11 tests, including full-set fail-closed behavior and 10/10 repeatability. The final PR head passed CI.

## Current scientific/training boundary

According to the merged S1-H-A contract:

- S1-E v2 pilot labels: 🚫 never training
- S1-E repeat labels: 🚫 never training
- S1-G v2 first-pass: 🚫 diagnostic-only / never training
- S1-G repeat: 🚫 do not run
- S1-F real component fit: 🔒 hard-closed
- checkpoint retention: 🔒 closed
- GuitarTab Engine shadow/production integration: 🔒 closed

Frozen evidence JSON files may still say `PREPARATION_ONLY_DRAFT_PR` or `merge_authorized=false`; those are historical pre-merge snapshots and are intentionally not rewritten.

## Immediate next controlled step

The repository has **no merged post-S1-H-A protocol** yet.

Proceed in this order:

1. ✅ synchronize stale global documentation through merged S1-H-A;
2. review PR #70 against current `main` and the merged S1-H-A boundary;
3. decide whether PR #70 should be superseded/archived or rewritten as historical evidence rather than merged as an active protocol;
4. preregister the next bounded deterministic S1-H stage before runtime changes;
5. keep model fitting and checkpoint/integration gates closed.

A stronger deterministic finger/hand feasibility solver is a reasonable candidate for the next design stage, because S1-H-A currently uses only a conservative minimum-finger lower bound. That proposal is not yet frozen repository truth.
