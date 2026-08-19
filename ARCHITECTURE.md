# Architecture

## Authoritative current map

```text
Guitar Pro / MusicXML source
        ↓
Safe intake + stream/tuning/pitch normalization
        ↓
Event / chord extraction
        ↓
Independent deterministic pitch ↔ string/fret validation
        ↓
valid_chord_voicings()
        │
        │ AUTHORITATIVE PHYSICAL BOUNDARY
        ↓
S1-H-A deterministic guitaristic plausibility analyzer ✅ MERGED
  ├─ requires the complete authoritative candidate set
  ├─ preserves raw physically-valid candidates for audit
  ├─ canonical candidate IDs + stable reason codes
  ├─ PLAUSIBLE
  ├─ BORDERLINE
  ├─ DOMINATED (diagnostic-only in v1; retained)
  └─ IMPRACTICAL
       └─ hard prune v1: H001_MIN_FINGER_PROXY_GE_6 only
        ↓
Future ranking / component-analysis layer 🔒 CLOSED
        ↓
Future Base Guitaristic Arbiter / Ranker 🔒 CLOSED
        ↓
Optional future hard-error refinement 🔒 CLOSED
        ↓
Checkpoint-retention gate 🔒 CLOSED
        ↓
GuitarTab Engine shadow / production integration 🔒 CLOSED
```

## Implemented and merged

- safe Guitar Pro / MusicXML intake and normalization;
- deterministic physical validation and candidate generation;
- historical `open_low` / `compact` research proposal layers;
- target-blind geometry/ergonomics descriptors and family-isolated evaluation infrastructure;
- Teacher-GOLD pairwise and independent-component research machinery;
- S1-F preparation-only component-training harness;
- S1-G v1 full-reliability preregistration as immutable merged history;
- S1-H-A deterministic plausibility analyzer and conservative pruning contract.

## S1-F boundary

S1-F prepares fixed features, provenance validation, family-safe folds, and a baseline model shape, but `fit_component_specialist()` remains deliberately hard-closed for project-label fitting.

Real fitting may be opened only by a later separately merged training protocol after independently sufficient reliability evidence and explicit training-corpus rules exist. A caller-supplied flag or dictionary cannot open the fit path.

## S1-G state

S1-G v1 is merged historical preregistration and must remain immutable.

Open draft PR #70 contains an S1-G v2 STRING-only protocol based on `ac146e9…`. It is not part of current `main`; current `main` is nine commits ahead of that branch. Therefore PR #70 is not an architectural dependency of S1-H-A and must not be described as current merged behavior.

The merged S1-H-A contract records the stricter current scientific boundary:

- S1-E v2 pilot labels: never training;
- S1-E repeat labels: never training;
- S1-G v2 first-pass: diagnostic-only / never training;
- S1-G repeat: do not run;
- S1-F real model fit: hard-closed.

## S1-H-A deterministic plausibility contract

`valid_chord_voicings()` remains the sole physical authority. S1-H-A may classify and conservatively prune existing physically-valid candidates, but may never create a candidate, repair an invalid mapping, or reinterpret preference as physical truth.

The lower-level analyzer accepts a supplied raw candidate collection only when that collection is exactly equal to the authoritative full set. Non-authoritative candidates, duplicates, and incomplete authoritative subsets fail closed.

### v1 classes and precedence

`IMPRACTICAL > DOMINATED > BORDERLINE > PLAUSIBLE`

### v1 hard prune

Only one hard-prune rule is frozen:

`H001_MIN_FINGER_PROXY_GE_6`

The conservative minimum-finger proxy is the number of distinct positive fret values. Six or more distinct positive fret values are outside the ordinary single-fretting-hand simultaneous-chord envelope and are classified `IMPRACTICAL`.

### Retained diagnostic classes

- Five distinct positive fret values => `BORDERLINE`, retained.
- Same-topology mechanical dominance based only on minimum-finger proxy and effective fretted-hand span => `DOMINATED`, retained in v1.

### Explicit non-rules

No candidate is hard-pruned merely because of open-string count, high position, internal string gaps, multiple fretted runs, isolated fretted strings, lower-position preference, tone, resonance, color, or artistic preference.

## Evidence and status semantics

Frozen JSON evidence/preregistration records capture the state at the time they were sealed. They are historical artifacts and may still contain values such as `PREPARATION_ONLY_DRAFT_PR` or `merge_authorized=false` after a later authorized merge. Those fields must not be retroactively rewritten solely to make history look current.

Live repository status is maintained in `README.md`, `STATUS.md`, `ROADMAP.md`, and this file.

## Current continuation point

There is no merged post-S1-H-A next-stage protocol yet. The safe next sequence is:

1. finish global documentation synchronization;
2. reconcile open PR #70 with current `main` and the S1-H-A scientific boundary;
3. preregister a new bounded deterministic S1-H continuation before runtime changes;
4. keep all learned-model fitting, checkpoint retention, and integration closed unless a later explicit gate opens them.

A plausible next research direction is a deterministic hand/finger feasibility refinement that improves on the current lower-bound finger proxy, but this is a proposal for the next preregistration stage, not current repository truth.

## Non-negotiable authority rules

1. Deterministic guitar rules own physical validity.
2. Learned systems may only rank candidates already inside the deterministic valid set.
3. Dataset families may not leak across declared evaluation boundaries.
4. Repeat/reliability labels are distinct from training labels.
5. Consumed untouched evidence may not be recycled for training/tuning or a fresh validation claim.
6. No checkpoint or GuitarTab Engine shadow/production integration exists without a separately preregistered promotion gate.
