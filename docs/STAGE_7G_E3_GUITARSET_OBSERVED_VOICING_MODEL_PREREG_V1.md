# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 Preregistration

## Purpose

Freeze the first learned model that uses `GUITARSET-OBSERVED-GOLD.v1` before any model fit.

This model does **not** learn left-hand finger numbers or barre identity. Its target is narrower:

`OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`

Given the exact simultaneous MIDI pitch multiset of a derived GuitarSet comp voicing, rank physically exact string/fret realizations so that the guitarist-observed realization is preferred.

The benchmark remains `UNSEEN_PERFORMER_SEEN_REPERTOIRE` from `GUITARSET-SPLIT.v1`.

## Data roles

- DEVELOPMENT: performers `00, 01, 04, 05`
- VALIDATION: performer `03`
- UNTOUCHED_FINAL: performer `02`

No validation or final row may enter fit. Untouched final remains closed until development and validation gates pass and the fitted development model artifact is sealed.

## Candidate set

For every accepted derived strum-voicing event:

1. preserve the exact MIDI pitch multiset;
2. use standard tuning `1:E4=64, 2:B3=59, 3:G3=55, 4:D3=50, 5:A2=45, 6:E2=40`;
3. enumerate all exact pitch→string/fret assignments with one note per string;
4. require fret range `0..19`;
5. require the observed GuitarSet placement to be present;
6. exclude single-candidate events from fit and ranking metrics, but report them separately.

No H-C finger assignment, Teacher label, S2-A preference, historical label, or model score participates in candidate construction.

## Frozen feature schema

Version: `GUITARSET-VOICING-FEATURES.v1`

Feature count: `28`

SHA-256:

`05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`

Features describe only static pitch/string/fret geometry: open-string ratio, fret position/span, string span/adjacency/gaps, mean string, six string-occupancy values, six per-string fret values, and six per-string MIDI-pitch values.

No previous/next chord, style label, performer identity, Teacher preference, fingering number, barre label, or model output is a feature in v1.

## Frozen model

Training objective:

`PAIRWISE_OBSERVED_VS_ALTERNATIVE`

For each ambiguous development event, the observed voicing is paired against alternatives. To keep the fit bounded, at most 32 alternatives are selected by an immutable label-independent SHA-256 ordering:

`SHA256(GUITARSET-NEGSEL.v1|voicing_id|canonical_candidate)`

Each selected comparison is emitted symmetrically as positive and negative feature differences.

Pipeline:

- `StandardScaler()`
- `LogisticRegression`
- `C=1.0`
- `fit_intercept=False`
- `class_weight=None`
- `solver="lbfgs"`
- `max_iter=2000`
- `random_state=0`
- no hyperparameter tuning

All candidates are retained for evaluation ranking even when only 32 alternatives are sampled for fit.

## Frozen deterministic comparator

`LOW_TOTAL_FRET.v1`

Ascending rank key:

`(sum_fret, max_fret, positive_fret_span, -open_count, string_span, canonical_candidate)`

The learned model must beat this comparator; uniform-random performance may be reported but is not the promotion gate.

## Development gate

Development diagnostics use leave-one-development-performer-out 4-fold CV.

Required:

- at least 1000 ambiguous development events;
- macro event Top-1 improvement over comparator >= `+0.03`;
- macro event MRR improvement >= `+0.05`;
- Top-1 wins in at least `3/4` held-out performers;
- MRR wins in at least `3/4` held-out performers;
- 10/10 deterministic reproduction of generated identities, rows, metrics and fitted coefficients within the execution environment.

Metrics also report event Recall@3 and recording-macro Top-1/MRR.

Failure means stop. Validation stays closed.

## Validation gate

Validation is a one-shot evaluation on performer `03`. It cannot tune features, thresholds, candidate rules or model hyperparameters.

Required:

- at least 500 ambiguous validation events;
- event Top-1 delta vs comparator >= `+0.02`;
- event MRR delta >= `+0.05`;
- recording-macro Top-1 delta > `0`;
- recording-macro MRR delta > `0`;
- 2000-repetition recording-block bootstrap, seed 0, 95% lower bound of MRR delta > `0`.

Only after PASS may the already fitted DEVELOPMENT model artifact be sealed for untouched-final opening. Validation is not added to fit.

## Untouched-final gate

Performer `02` remains unopened until:

`DEVELOPMENT_PASS AND VALIDATION_PASS AND MODEL_ARTIFACT_SEALED`

After opening there is no refit and no tuning.

Final PASS requires positive event Top-1/MRR and recording-macro Top-1/MRR deltas vs comparator, plus a 2000-repetition recording-block bootstrap whose 95% lower bound for MRR delta is > 0.

Final PASS means only:

`ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`

It does not authorize runtime connection or production deployment.

## Current authorization boundary

This preregistration is evidence only:

- `training_authorized = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`
- `final_access_authorized = false`

The next gate is `OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT`.

Frozen protocol SHA-256:

`1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`
