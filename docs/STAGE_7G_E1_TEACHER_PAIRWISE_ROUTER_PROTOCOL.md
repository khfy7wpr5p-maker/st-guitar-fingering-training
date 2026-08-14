# Stage 7G-E1 — Teacher-GOLD pairwise router protocol

## Purpose

Stage 7G-D-R3 closed the preregistered collection gate with 556 decisive blind A/B labels across all 40 independent Batch01 families. Stage 7G-E1 is the first model-fit protocol allowed to use those pairwise teacher preferences.

This stage is deliberately narrower than a full voicing ranker. It asks only:

> When the already-frozen `open_low` and `compact` specialists disagree, can a target-blind stateless router predict which proposal the teacher prefers?

The first 38 full-candidate selections remain separate richer preference evidence and are **not** mixed into this binary experiment.

## Fixed supervision

- input label pool: the 562 sealed Stage 7G-D-R2 pairwise tasks;
- decisive binary labels available: 556;
- `EQUAL_OR_UNSURE`: 6, preserved but excluded from binary fitting and binary accuracy metrics;
- independent families with decisive labels: 40;
- label target: `0 = teacher prefers open_low`, `1 = teacher prefers compact`;
- raw teacher choice rows stay outside Git and are pinned by SHA-256;
- no source-observed TAB/string/fret is a model target or feature.

The known preference imbalance (`open_low` 433, `compact` 123 on this disagreement-enriched sample) is treated as a baseline fact, not as a reason to tune features or thresholds.

## Fixed model

One model only:

- `StandardScaler`;
- `LogisticRegression`;
- `class_weight="balanced"`;
- `C=1.0`;
- `solver="lbfgs"`;
- `max_iter=2000`;
- `random_state=0`;
- decision threshold fixed at 0.5;
- no hyperparameter search;
- no feature selection after seeing validation results;
- no calibration pass.

This is intentionally a small interpretable router. Colab is used for reproducible execution, not because GPU compute is required.

## Fixed target-blind feature space

Exactly 15 features are preregistered before real Teacher-GOLD model fitting.

Current chord / deterministic candidate-set features:

1. chord size;
2. pitch span;
3. mean pitch;
4. log candidate count;
5. fraction of deterministic candidates containing an open string;
6. mean candidate mean-fret;
7. mean candidate fret-span.

Frozen `open_low` Top-1 geometry:

8. open-string ratio;
9. mean fret;
10. maximum fret;
11. fret span.

Frozen `compact` Top-1 geometry:

12. open-string ratio;
13. mean fret;
14. maximum fret;
15. fret span.

The feature vector may not contain teacher response, source title, source origin, family ID, task ordering, observed source TAB, observed source string/fret, Stage 7E information, or future/previous musical context.

## Family-isolated validation

Validation is fixed at deterministic 5-fold family-isolated cross-validation:

- all 40 family IDs are ordered by the existing SHA-256 deterministic fold rule;
- each family appears in validation exactly once;
- no row from a validation family may appear in that fold's training data;
- expected family split: 32 train families / 8 validation families per fold;
- no event-level random split is allowed.

The six equal/unsure rows are reported as annotation evidence but never coerced into either binary class.

## Metrics fixed before fit

Primary diagnostics:

- macro-family accuracy;
- macro-family accuracy delta versus `always_open_low`;
- event-weighted accuracy;
- event-weighted accuracy delta versus `always_open_low`.

Secondary diagnostics:

- balanced accuracy;
- open-low recall;
- compact recall;
- predicted compact count;
- per-fold family membership and metrics.

`always_open_low` is the required baseline because the collected teacher labels are strongly imbalanced toward `open_low` on this deliberately disagreement-enriched sample.

Stage 7G-E1 does **not** preregister a checkpoint-promotion threshold from this same cross-validation set. CV is development evidence only. If the router is promising, a later stage must preregister retention criteria and evaluate on a new untouched family-disjoint final set.

## Colab execution contract

After this protocol is reviewed and merged, the real run may be executed in Colab using the exact repository commit and external sealed label/teacher-manifest files.

The Colab run must:

- verify the raw teacher export SHA-256 before loading labels;
- verify the sealed pairwise teacher-manifest SHA-256;
- reconstruct family identity only from the pinned Stage 7G-C-R1 source-hash mapping;
- reconstruct deterministic physical candidates from pitches+tuning;
- decode A/B specialist side only with the already-fixed task-id hash rule;
- exclude all six `EQUAL_OR_UNSURE` rows from binary fitting;
- run the exact fixed 5 folds and fixed logistic model;
- emit only derived metrics/evidence for Git review;
- keep raw teacher labels outside Git.

## Scientific boundary

Stage 7G-E1 authorizes a diagnostic Teacher-GOLD model fit only after this protocol is merged. It does not authorize:

- checkpoint retention;
- production integration;
- Stage 7E reuse for training/tuning/calibration/validation;
- sequence context;
- model or feature tuning based on validation outcomes;
- treating pairwise labels as full-candidate Teacher-GOLD labels.

A negative result is valid evidence: if the learned router does not improve on `always_open_low`, `open_low` remains the stronger research baseline and no checkpoint is retained.
