# Status

## Current repository truth

- Default branch: `main`
- Deterministic runtime baseline through S1-H-C: `154d8d4c514849535a523ca79ea22b6fae7e77de`
- Latest merged runtime technical stage: **Stage 7G-E3-S1-H-C** via PR #74
- PR #70 / S1-G v2: ✅ closed as **SUPERSEDED WITHOUT MERGE**
- S2-A learned ranker: **protocol preregistration only; no real fit/checkpoint/integration authorized**

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
S2-A learned static fingering ranker            📋 PREREGISTERED / FIT CLOSED
        ↓
checkpoint retention / integration             🔒 CLOSED
```

## S1-H deterministic boundary

### S1-H-A — plausibility

✅ merged. Requires complete authoritative candidates and only conservatively prunes the frozen H-A impossibility rule.

### S1-H-B — fretting-resource feasibility

✅ merged via PR #73.

- ordinary four-finger/barre resource model;
- deterministic barre blocking/override rules;
- `H101_MIN_STANDARD_FINGERS_GE_5` hard prune;
- upstream-pruned candidates cannot be reintroduced;
- PR #73 CI #193: 236 tests PASS + compile PASS.

### S1-H-C — standard finger assignments

✅ merged via PR #74.

- enumerates every standard assignment for H-B-retained voicings;
- open string finger 0, fretted fingers 1..4;
- exact pitch/string/fret preservation;
- explicit barre metadata and stable assignment IDs;
- PR #74 CI #195: 245 tests PASS + compile PASS.

## Stage 7G-E3-S2-A — learned static fingering ranker

Status: 📋 **PREREGISTERED DESIGN / REAL FIT CLOSED**

Purpose: rank only the S1-H-C assignments of the same isolated chord by `STATIC_STANDARD_FINGERING_NATURALNESS`.

Frozen target boundary:

- stateless isolated chord;
- ordinary left-hand technique only;
- no previous/next chord;
- no tempo, style, right-hand, tone-color target, extended technique or player-profile input;
- blind pairwise Teacher response: `A`, `B`, `EQUAL_OR_UNSURE`.

Exact label roles:

- `S2A_STATIC_NATURALNESS_FIRST_PASS` — only future potentially fit-eligible decisive rows;
- `S2A_STATIC_NATURALNESS_REPEAT` — reliability-only, never training;
- `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL` — final-only, never training.

Frozen model shape:

- 30 target-blind deterministic assignment features;
- pairwise difference representation;
- mirrored pairs for exact class symmetry;
- linear Bradley-Terry-style utility through `LogisticRegression`;
- `C=1`, L2, `fit_intercept=False`, no learned scaler, no hyperparameter search;
- scalar score ranks all supplied H-C assignments; exact score ties use stable `assignment_id`.

## S2-A corpus/reliability gate

Real fit remains closed unless development evidence reaches at minimum:

- 40 families;
- 200 eligible events;
- 600 decisive first-pass pairs;
- 150 `FINGER_ONLY` + 150 `MIXED` decisive pairs;
- 100 decisive pairs in each `NEAR/MID/FAR` distance stratum;
- repeat gate: at least `max(120, 20%)`, 24–72h, 50% A/B reversal, exact agreement >=0.85 and decisive kappa >=0.75.

Repeat rows never become extra training data.

## S2-A evaluation gate

Development uses deterministic 5-fold family-isolated CV.

Preregistered development PASS includes:

- pairwise accuracy >=0.65;
- macro-family accuracy >=0.65;
- ROC-AUC >=0.70;
- macro-family accuracy delta >=+0.05 versus the frozen comparator;
- family wins > losses;
- required `FINGER_ONLY` and `MIXED` slice floors;
- 10/10 same-environment deterministic reproduction.

Untouched final is not opened unless development passes. Final requires >=20 disjoint families and >=200 decisive pairs and repeats the main accuracy/AUC/baseline gates plus a positive family-block bootstrap 95% CI lower bound for improvement.

A final PASS means only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`; it does not retain or deploy a model.

## Protected historical evidence

- S1-F historical project-label fitting remains hard-closed;
- S1-E pilot/repeat labels: never training;
- S1-G v2 first-pass: diagnostic-only / never training;
- S1-G repeat: do not run;
- historical repeat/reliability labels: not additional training rows;
- Stage 7E and E3-E: permanently consumed evaluation evidence.

S2-A cannot reactivate any of these by renaming provenance.

## Current controlled continuation point

The model **design** is now frozen, but model execution is not.

Next safe stage is implementation of the S2-A data-package builder, 30-feature extractor, pairwise ranker harness and evaluation machinery **without running a real fit**. After that implementation is independently tested and merged, actual Teacher collection/reliability and real model fitting remain evidence gates.

Checkpoint retention, shadow integration and production integration remain separately closed.

## Frozen evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots and are intentionally not rewritten after merge. Live status is maintained in the top-level project documentation.
