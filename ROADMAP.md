# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0–4 | safety, dataset, intake, normalization, deterministic physical engine | ✅ complete |
| 5–7E | bounded placement/routing research + untouched evaluation | ✅ research complete; untouched evidence consumed |
| 7G-E1/E2/E3 | Teacher-GOLD ergonomics research | ✅ completed through diagnostics; no production checkpoint |
| 7G-E3-S0 | failure diagnostics + reliability redesign | ✅ completed |
| 7G-E3-S1-A/B/C/D | independent-component reliability program | ✅ historical evidence path |
| 7G-E3-S1-F | fail-closed model-preparation harness | ✅ merged; historical project-label fit remains hard-closed |
| 7G-E3-S1-G v1 | full-reliability preregistration | ✅ immutable merged history |
| PR #70 / S1-G v2 | obsolete STRING-only proposal | ✅ closed superseded, never merged |
| 7G-E3-S1-H-A | deterministic guitaristic plausibility | ✅ merged PR #71 |
| 7G-E3-S1-H-B | four-finger/barre resource feasibility | ✅ merged PR #73 |
| 7G-E3-S1-H-C | standard finger-assignment enumeration | ✅ merged PR #74 |
| 7G-E3-S2-A | learned static fingering-ranker protocol | 📋 preregistered design; real fit closed |
| S2-A implementation | data package + 30D features + pairwise ranker/eval harness | ⏳ next technical stage; no real fit |
| S2-A corpus/reliability | fresh pairwise Teacher data + repeat gate | 🔒 evidence gate |
| S2-A real fit | frozen linear pairwise ranker | 🔒 closed until corpus/reliability PASS |
| S2-A untouched final | family-disjoint final evaluation | 🔒 closed until development PASS |
| Later | checkpoint retention / promotion | 🔒 separate gate |
| Later | sequence/transition ranker | 🔒 separate future specialist |
| Later | GuitarTab Engine shadow / production | 🔒 separate gate |

## Current position

The deterministic pre-model pipeline is complete through **Stage 7G-E3-S1-H-C** and the first learned-stage **design** is now preregistered as S2-A.

```text
valid_chord_voicings()
  → S1-H-A plausibility
  → S1-H-B ordinary four-finger/barre resource feasibility
  → S1-H-C standard finger assignments
  → S2-A static learned ranker protocol
  → [implementation only, no fit]
  → corpus/reliability gate
  → real fit gate
  → untouched final gate
  → checkpoint review gate
```

## Why S2-A is stateless first

S1-H-C has already isolated the valid assignment set. The next scientific question should therefore be the smallest learned problem:

> For one isolated chord, which valid H-C assignment is more natural/easier for the left hand under ordinary technique?

Previous/next fingering, tempo, style, voice-leading, right-hand pattern, tone-color goals and player-specific anatomy are intentionally not mixed into v1. Sequence/transition preference will be a later specialist only after the static ranker is established.

## S2-A data design

### Target

`STATIC_STANDARD_FINGERING_NATURALNESS`

Blind pairwise responses:

- `A`
- `B`
- `EQUAL_OR_UNSURE`

Exact provenance:

- first-pass development: `S2A_STATIC_NATURALNESS_FIRST_PASS`;
- repeat reliability: `S2A_STATIC_NATURALNESS_REPEAT`;
- untouched final: `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL`.

Only decisive first-pass rows may ever become fit-eligible. Repeat and final rows are never training rows.

### Pair construction

Pairs are generated only from the complete H-C assignment set of the same event and before labels exist.

- `FINGER_ONLY`: same voicing, different finger/barre assignment;
- `MIXED`: different voicing;
- L1 feature distance stratified into `NEAR/MID/FAR`;
- at most one pair per pair-type × distance cell;
- at most 6 tasks/event;
- A/B order fixed by hash.

## S2-A feature contract

Exactly 30 deterministic target-blind features:

- 18 per-string features: `used`, normalized fret, normalized finger for strings 1..6;
- 10 aggregate geometry/resource features: open ratio, mean/span fret, string span/gaps, finger count, barre count/span/override;
- 2 cross-finger mechanics: maximum finger/fret step and same-fret multi-finger pair ratio.

No labels, annotator/source/family identity, observed source fingering, context event, previous model score or consumed evidence enters features.

## S2-A learned model v1

Frozen interpretable first model:

```text
pair delta = phi(A) - phi(B)
mirrored delta rows for exact class symmetry
LogisticRegression(
  penalty="l2",
  C=1.0,
  fit_intercept=False,
  class_weight=None,
  solver="lbfgs",
  max_iter=2000,
  random_state=0
)
score(assignment) = w · phi(assignment)
```

No learned scaler and no hyperparameter search in v1.

## S2-A minimum evidence gates

### Before real fit

- >=40 development families;
- >=200 eligible events;
- >=600 decisive first-pass pairs;
- >=150 `FINGER_ONLY` and >=150 `MIXED` decisive pairs;
- >=100 decisive pairs in each `NEAR/MID/FAR` stratum;
- repeat reliability PASS: >=max(120,20%), 24–72h, 50% A/B reversal, exact agreement >=0.85, decisive kappa >=0.75.

### Development CV PASS

Five-fold `family_id`-isolated CV:

- pairwise accuracy >=0.65;
- macro-family accuracy >=0.65;
- ROC-AUC >=0.70;
- macro-family delta >=+0.05 vs frozen comparator;
- family wins > losses;
- required FINGER_ONLY/MIXED slice floors;
- 10/10 deterministic reproduction.

Untouched final is not opened if development fails.

### Untouched final PASS

- >=20 disjoint families;
- >=200 decisive pairs;
- pairwise and macro-family accuracy >=0.65;
- ROC-AUC >=0.70;
- macro-family delta >=+0.05 vs comparator;
- family wins > losses;
- positive family-block bootstrap 95% CI lower bound for improvement;
- zero candidate-authority violations.

Final PASS produces only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`.

## Next controlled technical milestone

Implement the frozen S2-A machinery without consuming real Teacher labels or running a real fit:

1. assignment 30-feature extractor;
2. label-blind pair sampler and blinded manifest/audit generator;
3. response validator with exact provenance roles;
4. reliability evaluator;
5. mirrored pair-difference dataset builder;
6. fixed linear ranker constructor with fit execution still gated;
7. family-isolated CV/evaluation helpers;
8. deterministic baselines and final-evaluation report schema;
9. tests for no leakage, no out-of-set assignment, symmetry and repeatability.

Only after that implementation is independently verified should real corpus collection/reliability evidence be considered.

## Promotion gates remain separate

Even a successful future S2-A final result does not automatically authorize checkpoint retention, sequence-level modeling, GuitarTab Engine shadow integration or production integration.

## Evidence semantics

Frozen preregistration/evidence files remain immutable historical snapshots. Live repository status is maintained in the top-level documents.
