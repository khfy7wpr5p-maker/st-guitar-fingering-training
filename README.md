# st-guitar-fingering-training

Training, evaluation, and deterministic guitar-fingering research for polyphony, voicing, string/fret selection, and learned guitaristic fingering ranking.

## Core rule

Physical validity and ordinary-technique candidate feasibility are deterministic and authoritative. A learned system may only rank assignments already emitted by the active S1-H pipeline; it may never create, repair, legalize, or silently reintroduce an invalid/pruned placement.

## Current architecture

```text
Guitar Pro / MusicXML
  → safe normalization
  → deterministic pitch/string/fret validation
  → valid_chord_voicings()                         [authoritative physical set]
  → S1-H-A deterministic plausibility              [merged]
  → S1-H-B four-finger/barre resource feasibility [merged]
  → S1-H-C standard finger assignments            [merged]
  → S2-A 30D deterministic assignment features    [merged PR #78]
  → S2-A blind pair/repeat reliability machinery  [merged PR #78]
  → S2-A fail-closed learned ranker/CV harness     [merged PR #79]
  → S2-A untouched-final evaluation gate          [merged PR #80]
  → NEW S2-A TEACHER CORPUS + RELIABILITY         [required next]
  → real model fit                                [closed until evidence PASS]
  → checkpoint retention                          [separate closed gate]
  → GuitarTab Engine shadow / production          [separate closed gate]
```

## Current repository position

The deterministic S1-H-C runtime baseline is `154d8d4c514849535a523ca79ea22b6fae7e77de`.

The executable S2-A implementation through PR #80 is based on merge commit `7b05c18bcde3b8ff84f77dffc25a5ced307c47a4`. Later documentation-only merges may advance `main`; use GitHub history for the live branch head.

Completed S2-A implementation:

- ✅ frozen 30D target-blind assignment feature extractor;
- ✅ blind label-free pair sampling over exact S1-H-C `assignment_id` values;
- ✅ deterministic FIRST_PASS / REPEAT / UNTOUCHED_FINAL provenance validation;
- ✅ repeat-reliability evaluator with 24–72h interval and exact 50% A/B reversal;
- ✅ exact mirrored pairwise training matrix;
- ✅ frozen no-intercept L2 logistic ranker constructor;
- ✅ fail-closed real-fit evidence gate;
- ✅ family-isolated 5-fold development CV and fixed baseline comparison;
- ✅ inference restricted to the exact H-C assignment authority set;
- ✅ untouched-final preflight and deterministic family-block bootstrap gate.

The frozen S2-A feature-list SHA-256 is:

`d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`

## Verification

- PR #78 / CI #203: **252 tests PASS**, compile validation PASS.
- PR #79 / CI #205: **256 tests PASS**, compile validation PASS.
- PR #80 / CI #207: **260 tests PASS**, compile validation PASS.
- Stage 7B-C2 comparison step was skipped by branch condition in these PR workflows and is not counted as PASS evidence.

## What has not happened

No real S2-A project model has been fitted yet because no eligible new corpus with provenance `S2A_STATIC_NATURALNESS_FIRST_PASS` currently satisfies the frozen evidence gate.

Real fit requires at minimum:

- 40 development families;
- 200 eligible events;
- 600 decisive FIRST_PASS pairs;
- 150 `FINGER_ONLY` and 150 `MIXED` decisive pairs;
- 100 decisive pairs in each `NEAR/MID/FAR` stratum;
- repeat reliability over at least `max(120, 20%)` tasks;
- exact repeat agreement >= 0.85;
- decisive Cohen kappa >= 0.75;
- 24–72h repeat interval and exactly 50% A/B presentation reversal.

Old S1-E/S1-G/repeat/consumed evaluation evidence cannot be renamed or recycled into this corpus.

## Model boundary

S2-A v1 learns only `STATIC_STANDARD_FINGERING_NATURALNESS` for an isolated chord under ordinary left-hand technique. Previous/next chord transitions, tempo, style, tone, right-hand behavior, extended techniques, and player-specific anatomy remain outside this v1 target.

Even a successful development and untouched-final result cannot automatically retain or deploy a checkpoint. Final PASS yields only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`.

## Current continuation point

**The code path for S2-A model development is ready. The next unavailable input is fresh blind Teacher data, not more model code.**

The safe next operational step is to create/collect the new S2-A FIRST_PASS corpus, perform the frozen repeat-reliability check, and only then allow `fit_s2a_ranker()` to execute if every gate passes.

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, and `docs/STAGE_7G_E3_S2A_LEARNED_FINGERING_RANKER_PREREGISTRATION.md`.
