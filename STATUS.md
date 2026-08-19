# Status

## Current repository truth

- Default branch: `main`
- Verified current `main`: `154d8d4c514849535a523ca79ea22b6fae7e77de`
- Latest merged stage: **Stage 7G-E3-S1-H-C** via PR #74
- PR #72 documentation synchronization: ✅ merged
- PR #73 / S1-H-B: ✅ merged at `0029cb0ab263fbc61bcb1106e3f997811f1455aa`
- PR #74 / S1-H-C: ✅ merged at `154d8d4c514849535a523ca79ea22b6fae7e77de`
- PR #70 / S1-G v2: ✅ closed as **SUPERSEDED WITHOUT MERGE**

## Deterministic pipeline now implemented

```text
Guitar Pro / MusicXML
        ↓
safe normalization + event/chord extraction
        ↓
independent deterministic pitch ↔ string/fret validation
        ↓
valid_chord_voicings()                         ✅ AUTHORITATIVE PHYSICAL SET
        ↓
S1-H-A guitaristic plausibility                ✅ MERGED
        ↓
S1-H-B four-finger/barre resource feasibility  ✅ MERGED
        ↓
S1-H-C standard finger-assignment enumeration  ✅ MERGED
        ↓
REAL MODEL DEVELOPMENT GATE                    ⛔ STOP / separate approval required
```

## Stage 7G-E3-S1-H-A — deterministic plausibility

Status: ✅ **MERGED**

- complete authoritative candidate set required;
- incomplete/non-authoritative/duplicate raw sets fail closed;
- raw physical set remains auditable;
- stable candidate IDs/reason codes;
- only v1 hard prune: `H001_MIN_FINGER_PROXY_GE_6`;
- five distinct positive frets remain `BORDERLINE` at H-A;
- dominance is diagnostic-only at H-A.

## Stage 7G-E3-S1-H-B — deterministic fretting-resource feasibility

Status: ✅ **MERGED** via PR #73

Purpose: test whether an H-A-retained voicing can be covered inside the declared ordinary four-fretting-finger envelope when continuous same-fret barre coverage is allowed.

Frozen v1 behavior:

- open strings consume no fretting finger;
- same-fret targets can share a continuous barre when no blocking required note lies between them;
- unused intervening strings are passable;
- higher-fret intervening notes are passable as overrides of an underlying lower barre;
- required open strings and required lower positive frets block a higher-fret barre crossing;
- `minimum_standard_fingers` is deterministic;
- hard prune: `H101_MIN_STANDARD_FINGERS_GE_5`;
- upstream H-A-pruned candidates remain audited and cannot be reintroduced;
- empty final set is explicit as `NO_STANDARD_FINGERING_CANDIDATE`.

Verification on PR #73 / CI #193:

- 236 unit tests: ✅ PASS
- compile validation: ✅ PASS
- Stage 7B-C2 full comparison workflow step: SKIPPED by branch condition, not counted as PASS evidence

## Stage 7G-E3-S1-H-C — deterministic standard finger assignments

Status: ✅ **MERGED** via PR #74

Purpose: enumerate all ordinary four-finger assignment candidates for every S1-H-B-retained voicing without choosing which is most natural.

Frozen v1 behavior:

- open string → finger `0`;
- fretted groups → distinct fingers `1..4`;
- notes in one H-B barre group share a finger;
- strictly lower-fret groups must use lower-numbered fingers than strictly higher-fret groups;
- same-fret groups have no frozen preference order;
- every output preserves pitch/string/fret exactly;
- explicit barre metadata is emitted;
- assignment IDs are stable SHA-256 identities;
- pruned voicings receive zero assignments;
- a retained voicing producing zero assignments fails closed.

Verification on PR #74 / CI #195:

- 245 unit tests: ✅ PASS
- compile validation: ✅ PASS
- Stage 7B-C2 full comparison workflow step: SKIPPED by branch condition, not counted as PASS evidence

## Scientific limitation of the deterministic boundary

H-B/H-C deliberately do **not** claim to know the most comfortable or musically natural fingering. They do not hard-code player-specific anatomy, wrist posture, detailed reach comfort, transition quality, tone, style, or artistic preference.

Their role is narrower:

1. preserve physical truth;
2. reject clear four-finger/barre resource impossibilities under the declared envelope;
3. enumerate auditable standard fingering candidates;
4. hand only those candidates to a future ranking model.

## Historical model/reliability path

- S1-F preparation harness: ✅ merged, but real project-label fitting remains hard-closed
- S1-G v1: ✅ immutable merged historical preregistration
- S1-G v2 / PR #70: closed superseded, never merged
- S1-E pilot/repeat labels: 🚫 never training
- S1-G v2 first-pass: 🚫 diagnostic-only / never training
- S1-G repeat: 🚫 do not run
- historical repeat/reliability labels: not additional training rows
- Stage 7E and E3-E: permanently consumed evaluation evidence

## Current controlled stopping point — REAL MODEL DEVELOPMENT GATE

All approved pre-model deterministic technical work is now merged through S1-H-C.

The next meaningful step is no longer another mechanical candidate-generation rule. It is the design and execution of a **real learned fingering-ranking stage** that ranks S1-H-C assignments while remaining unable to override the deterministic physical/feasibility boundary.

Before any real fit is opened, a separate model-development protocol must define at minimum:

- exact prediction target;
- eligible training-label provenance;
- features available to the model;
- family-isolated split/evaluation policy;
- baselines and acceptance metrics;
- checkpoint-retention rule;
- forbidden consumed/reliability corpora;
- fail-closed relation to S1-H-A/B/C outputs.

**Stop here pending explicit approval for real model development.**

## Frozen evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots and are intentionally not rewritten after merge. Live status is maintained in the top-level project documentation.
