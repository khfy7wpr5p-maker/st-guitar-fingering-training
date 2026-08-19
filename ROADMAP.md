# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0–4 | safety, dataset, intake, normalization, deterministic physical engine | ✅ complete |
| 5–7E | bounded placement/routing research + untouched evaluation | ✅ research complete; untouched evidence consumed |
| 7G-E1/E2/E3 | Teacher-GOLD ergonomics research | ✅ historical research complete |
| 7G-E3-S0/S1 | diagnostics, reliability redesign, preparation history | ✅ historical evidence path |
| 7G-E3-S1-H-A | deterministic guitaristic plausibility | ✅ merged PR #71 |
| 7G-E3-S1-H-B | four-finger/barre resource feasibility | ✅ merged PR #73 |
| 7G-E3-S1-H-C | standard finger-assignment enumeration | ✅ merged PR #74 |
| 7G-E3-S2-A protocol | static learned fingering-ranker preregistration | ✅ merged PR #77 |
| S2-A data/features/reliability | 30D features + blind pair/repeat machinery | ✅ merged PR #78 |
| S2-A ranker/development harness | fail-closed fit + family-isolated CV | ✅ merged PR #79 |
| S2-A untouched-final harness | fixed final comparator + family-block bootstrap | ✅ merged PR #80 |
| S2-A FIRST_PASS collection | new blind Teacher corpus | ⏳ NEXT REQUIRED INPUT |
| S2-A repeat reliability | fresh 24–72h reblind check | 🔒 requires FIRST_PASS responses |
| S2-A real development fit | frozen linear pairwise ranker | 🔒 requires corpus + reliability PASS |
| S2-A untouched final | disjoint final Teacher corpus | 🔒 requires development PASS |
| Checkpoint retention | retention/promotion review | 🔒 separate gate |
| Sequence/transition ranker | contextual fingering specialist | 🔒 later stage |
| GuitarTab Engine integration | shadow / production | 🔒 separate gate |

## Current position

The **S2-A executable model-development machinery is complete** through PR #80. The repository is no longer waiting for model code; it is waiting for new human supervision collected under the frozen S2-A contract.

```text
valid_chord_voicings()
  → S1-H-A plausibility
  → S1-H-B four-finger/barre feasibility
  → S1-H-C standard assignments
  → S2-A 30D features                         ✅
  → blind pair/repeat machinery               ✅
  → fail-closed ranker + development CV       ✅
  → untouched-final evaluation harness        ✅
  → NEW FIRST_PASS TEACHER DATA               ⏳
  → REPEAT RELIABILITY                        🔒
  → REAL FIT + DEVELOPMENT CV                 🔒
  → UNTOUCHED FINAL                           🔒
  → CHECKPOINT RETENTION REVIEW               🔒
```

Executable S2-A implementation baseline through PR #80: `7b05c18bcde3b8ff84f77dffc25a5ced307c47a4`.

## Completed S2-A technical milestones

### PR #78

- exact 30D deterministic assignment feature vector;
- frozen feature SHA-256 `d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`;
- label-blind FINGER_ONLY/MIXED, NEAR/MID/FAR pair sampling;
- deterministic A/B blinding;
- exact provenance response validation;
- repeat package with 50% reversal;
- exact agreement + Cohen-kappa reliability evaluator;
- CI #203: 252 tests PASS + compile PASS.

### PR #79

- fresh H-C recomputation before supervised row admission;
- exact mirrored pair matrix;
- frozen no-intercept L2 logistic ranker;
- fail-closed minimum corpus/reliability gate;
- 5-fold family-isolated development CV;
- fixed LOW_FRET/COMPACT baseline comparison;
- threshold-free/calibration metrics plus family/slice metrics;
- exact H-C assignment-set restriction at inference;
- CI #205: 256 tests PASS + compile PASS.

### PR #80

- untouched-final accepts FINAL provenance only;
- development PASS required before final;
- comparator cannot be reselected on final data;
- >=20 final families / >=200 decisive pairs;
- development/final family overlap rejected before inference;
- deterministic 2000-resample family-block bootstrap;
- final PASS requires 95% CI lower bound >0;
- PASS gives only checkpoint-review eligibility;
- CI #207: 260 tests PASS + compile PASS.

The Stage 7B-C2 workflow step was skipped by branch condition in these PRs and is not counted as PASS evidence.

## Data gate before real fit

The following minimums remain binding:

- >=40 development families;
- >=200 eligible events;
- >=600 decisive FIRST_PASS pairs;
- >=150 FINGER_ONLY and >=150 MIXED decisive pairs;
- >=100 decisive pairs in each NEAR/MID/FAR stratum;
- repeat sample >=max(120, 20% of annotated tasks);
- exact repeat agreement >=0.85;
- decisive Cohen kappa >=0.75;
- 24–72h repeat interval;
- exact 50% A/B reversal;
- development/final family disjointness.

No current repository corpus satisfies this new S2-A requirement. Therefore real project coefficients have not been fitted.

## Development and final gates

When eligible data exists, the already-implemented code will enforce:

- deterministic five-fold family-isolated development CV;
- pairwise accuracy >=0.65;
- macro-family accuracy >=0.65;
- ROC-AUC >=0.70;
- macro-family delta >=+0.05 against the frozen development comparator;
- family wins > losses;
- supported FINGER_ONLY/MIXED slice floors;
- 10/10 development-CV reproduction.

Only a development PASS may open the untouched-final evaluator. Final additionally requires a positive family-block bootstrap 95% CI lower bound.

## Next controlled milestone

**Collect fresh S2-A supervision.**

1. choose new development families/events without protected evidence reuse;
2. generate sealed blind FIRST_PASS packages through the merged S2-A builder;
3. collect A/B/EQUAL_OR_UNSURE responses;
4. generate and collect the repeat subset 24–72h later;
5. evaluate reliability and corpus coverage;
6. execute real fit only if all gates pass.

The software must not manufacture Teacher labels to satisfy this milestone.

## Promotion gates remain separate

Even a successful S2-A untouched-final result does not automatically authorize checkpoint retention, sequence-level modeling, GuitarTab Engine shadow integration, or production integration.

## Evidence semantics

Frozen preregistration/evidence files remain immutable historical snapshots. Live repository status is maintained in the top-level documents.
