# st-guitar-fingering-training

Training, evaluation, and deterministic guitar-fingering research for polyphony, voicing, string/fret selection, and guitaristic fingering.

## Core rule

Physical validity and ordinary-technique candidate feasibility are deterministic and authoritative. A learned system may only rank assignments already emitted by the active deterministic pipeline; it may never create, repair, legalize, or silently reintroduce an invalid/pruned placement.

## Current architecture

```text
Guitar Pro / MusicXML
  → safe normalization
  → deterministic pitch/string/fret validation
  → valid_chord_voicings()                         [authoritative physical set]
  → S1-H-A deterministic plausibility              [merged]
  → S1-H-B four-finger/barre resource feasibility [merged]
  → S1-H-C standard finger assignments            [merged]
  → REAL MODEL DEVELOPMENT GATE                   [stopped here]
  → learned fingering ranker                      [not started]
  → checkpoint / GuitarTab Engine integration     [closed]
```

## Verified repository position

Current `main` after PR #74 is `154d8d4c514849535a523ca79ea22b6fae7e77de`.

Implemented pre-model boundary:

- ✅ S1-H-A requires the complete `valid_chord_voicings()` set and applies only its conservative plausibility rule;
- ✅ S1-H-B rejects ordinary four-finger/barre resource impossibilities under an explicit deterministic model;
- ✅ S1-H-C enumerates every standard finger assignment admitted by that deterministic boundary;
- ✅ PR #70 is closed as superseded without merge;
- 🔒 no real project model fit, checkpoint retention, shadow integration, or production integration has been opened.

## S1-H-B in brief

H-B counts deterministic fretting resources rather than guessing comfort.

- open strings consume no fretting finger;
- same-fret notes may share a continuous barre;
- unused strings may lie under a barre;
- a higher-fret note may override a lower underlying barre;
- a required open string or required lower positive fret blocks a higher-fret barre crossing;
- `minimum_standard_fingers >= 5` is pruned by `H101_MIN_STANDARD_FINGERS_GE_5`.

This is an ordinary four-finger envelope, not a claim about extended techniques.

## S1-H-C in brief

H-C is an assignment enumerator, not a preference engine.

- open strings use finger `0`;
- each fretted H-B group gets a distinct finger `1..4`;
- lower fret groups use lower-numbered fingers than strictly higher fret groups;
- same-fret groups have no frozen preference order;
- pitch/string/fret is preserved exactly;
- barre spans are explicit;
- assignment IDs are stable SHA-256 identities;
- upstream-pruned voicings receive no assignments.

## Verification

- PR #73 / CI #193: **236 tests PASS**, compile validation PASS; Stage 7B-C2 comparison step skipped by branch condition.
- PR #74 / CI #195: **245 tests PASS**, compile validation PASS; Stage 7B-C2 comparison step skipped by branch condition.

A skipped workflow step is not counted as PASS evidence.

## What remains for a learned model

The deterministic pipeline intentionally does not decide which surviving assignment is most natural, comfortable, stylistically appropriate, or best in musical context. Detailed hand comfort, player-specific anatomy, transitions, style, tone, and preference remain outside hard physical truth.

The next justified stage is therefore a learned **fingering ranker** over S1-H-C assignment IDs, not another arbitrary deterministic preference rule.

Before real fitting begins, a separate model-development protocol must freeze the target, eligible label provenance, features, family-isolated evaluation, baselines/metrics, tie handling, model-selection policy, checkpoint gate, and strict output restriction to S1-H-C assignments.

## Protected evidence

- Stage 7E and E3-E remain consumed evaluation-only evidence.
- S1-E pilot/repeat labels remain never-training.
- S1-G v2 first-pass remains diagnostic-only/never-training; its repeat is not run.
- historical repeat/reliability labels are not extra training rows.
- S1-G v1 remains immutable merged history.
- frozen evidence JSON files remain historical snapshots and are not rewritten after merge.

## Current stop

**The repository has reached the real model-development gate. No real model fit has been started.**

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `docs/STAGE_7G_E3_S1H_A_GUITARISTIC_PLAUSIBILITY.md`, `docs/STAGE_7G_E3_S1H_B_FRETTING_RESOURCE_FEASIBILITY.md`, and `docs/STAGE_7G_E3_S1H_C_STANDARD_FINGER_ASSIGNMENTS.md`.
