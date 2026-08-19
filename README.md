# st-guitar-fingering-training

Training, evaluation, and deterministic guitar-fingering research for polyphony, voicing, string/fret selection, and guitaristic plausibility.

## Core rule

Physical validity is deterministic and authoritative. Learned systems may score or rank only candidates already produced by `valid_chord_voicings()`; they may never create, repair, or legalize an invalid placement.

## Current architecture

```text
Guitar Pro / MusicXML
  -> safe normalization
  -> deterministic pitch/string/fret validation
  -> valid_chord_voicings()                         [authoritative]
  -> S1-H-A deterministic plausibility analyzer     [merged]
       - PLAUSIBLE / BORDERLINE / DOMINATED / IMPRACTICAL
       - v1 hard prune: H001_MIN_FINGER_PROXY_GE_6 only
       - complete authoritative candidate set required
       - raw set preserved for audit
  -> future ranking / component-model work           [closed]
  -> future checkpoint / GuitarTab Engine shadow     [closed]
```

## Verified repository position

Current `main` includes:

- ✅ S1-F component-training preparation harness, with real fitting **hard-closed**;
- ✅ S1-G v1 full-reliability preregistration, retained as immutable merged history;
- ✅ S1-H-A deterministic guitaristic plausibility analyzer, merged by PR #71;
- 🔒 no component-model fit, checkpoint retention, shadow integration, or production integration.

Open draft PR #70 proposes an S1-G v2 STRING-only protocol, but it is **not merged repository truth** and is based on an older `main`. It must be reconciled or superseded before it can be treated as an active stage.

## Human-label reliability boundary

Earlier single global A/B naturalness supervision was not reliable enough for promotion. Later component work therefore separated deterministic facts from human judgments. The current safety boundary is stricter than the older S1-D-era documents:

- S1-F real fit remains hard-closed;
- S1-E pilot/repeat labels are never-training evidence;
- S1-G v2 first-pass evidence is diagnostic-only / never-training according to the merged S1-H-A contract;
- S1-G repeat is not to be run under the merged S1-H-A contract;
- S1 repeat/reliability evidence is never additional training data.

## S1-H-A deterministic plausibility v1

S1-H-A is intentionally conservative.

- `H001_MIN_FINGER_PROXY_GE_6`: six or more distinct positive fret values => `IMPRACTICAL`, prune.
- `B001_FIVE_DISTINCT_POSITIVE_FRETS`: five distinct positive fret values => `BORDERLINE`, retain.
- `D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY`: diagnostic `DOMINATED`, retain in v1.
- Open-string count, high fret, internal gaps, multiple fretted runs, lower position, tone, resonance, and artistic preference are **not** single-factor prune rules.

The analyzer fails closed if the supplied raw set is not exactly the complete authoritative `valid_chord_voicings()` set for the same pitches and tuning.

## What should happen next

Repository truth does not yet contain a merged post-S1-H-A next-stage protocol. The controlled continuation point is therefore:

1. synchronize stale global documentation to S1-H-A;
2. review open PR #70 against current `main` and decide whether to archive/supersede it rather than treating it as current architecture;
3. only then preregister the next bounded S1-H step (for example, a stronger deterministic hand/finger feasibility stage) before changing runtime behavior.

No model training should be resumed merely because the training harness exists.

## Protected evidence

Stage 7E and E3-E remain consumed evaluation-only evidence. Historical repeat/reliability labels remain separate from training data. Frozen preregistration/evidence JSON files are historical records and should not be rewritten merely to reflect a later merge; live status belongs in `README.md`, `STATUS.md`, `ROADMAP.md`, and `ARCHITECTURE.md`.

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `docs/STAGE_7G_E3_S1F_COMPONENT_TRAINING_PREP.md`, `docs/STAGE_7G_E3_S1G_FULL_RELIABILITY_PREREG_V1.md`, and `docs/STAGE_7G_E3_S1H_A_GUITARISTIC_PLAUSIBILITY.md`.
