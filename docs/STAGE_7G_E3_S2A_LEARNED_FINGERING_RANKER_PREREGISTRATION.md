# Stage 7G-E3-S2-A — Learned Fingering Ranker Preregistration

Status: **PREREGISTRATION / NO FIT AUTHORIZED**  
Protocol version: `S2-A.v1`  
Deterministic runtime baseline: S1-H-C (`154d8d4c514849535a523ca79ea22b6fae7e77de`)

## 1. Purpose

S2-A is the first learned stage after the deterministic S1-H-A/B/C boundary.

Its task is deliberately narrow:

> Given the complete S1-H-C assignment set for one isolated chord event, rank those already-valid assignments by **static standard-fingering naturalness / left-hand comfort**.

S2-A may never create, repair, legalize, or reintroduce a fingering. The model output is a score attached only to supplied S1-H-C `assignment_id` values.

Pipeline:

`valid_chord_voicings()` → S1-H-A → S1-H-B → S1-H-C → **S2-A learned static ranker** → later context/transition stage → later checkpoint/integration gates.

## 2. Target semantics

Frozen v1 target name:

`STATIC_STANDARD_FINGERING_NATURALNESS`

Teacher prompt semantics:

- treat the chord as an isolated event;
- assume ordinary four-finger left-hand technique described by S1-H-B/C;
- ignore previous/next chord, tempo, voice-leading, right-hand pattern, tone-color goals, style-specific effects, thumb-over and extended technique;
- choose the option that is more natural/easier to execute accurately with less unnecessary left-hand tension;
- if neither option is clearly preferable, answer `EQUAL_OR_UNSURE`.

S2-A therefore does **not** claim universal anatomy-independent comfort. v1 learns the frozen reference-expert preference target under the prompt above. Multi-player consensus and sequence-context preference are separate future stages.

## 3. Supervision form

Supervision is pairwise and blind.

Allowed responses:

- `A`
- `B`
- `EQUAL_OR_UNSURE`

Teacher-facing tasks show only:

- pitches/tuning needed to understand the chord;
- two S1-H-C TAB/finger assignments A and B;
- explicit finger numbers and barre spans.

Teacher-facing tasks must hide:

- model identity or score;
- feature values;
- source/family identity;
- observed source fingering;
- pair-selection stratum;
- deterministic baseline preference;
- prior responses.

A/B order is fixed by a deterministic SHA-256 hash before annotation and may not depend on labels.

## 4. Data roles and exact provenance

Three roles are frozen and must never be silently mixed.

### 4.1 Development first-pass

Exact eligible fit provenance:

`S2A_STATIC_NATURALNESS_FIRST_PASS`

Only decisive first-pass `A` or `B` responses with this exact provenance are fit-eligible.

`EQUAL_OR_UNSURE` remains stored as ambiguity evidence and is excluded from fit without being relabeled.

### 4.2 Reliability repeat

Exact provenance:

`S2A_STATIC_NATURALNESS_REPEAT`

Repeat rows are **never** training, tuning, feature selection, threshold selection, hard-error mining, or checkpoint-selection rows.

### 4.3 Untouched final

Exact provenance:

`S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL`

These families and labels are never used for fit, hyperparameter choice, feature choice, baseline choice, stopping decisions, or threshold selection.

## 5. Source/family boundary

Every assignment-level row inherits the musical source `family_id` of its event.

Required exclusions:

- Stage 7E consumed final families: never S2-A training/tuning;
- E3-E consumed Teacher-GOLD families: never S2-A training/tuning;
- historical pilot/repeat/diagnostic labels: never S2-A training;
- S1-E/S1-G labels: never S2-A training;
- any family placed in S2-A untouched final: never S2-A development.

Preferred S2-A corpus policy is fresh source families not previously used in Teacher preference experiments. Historical development sources may be used for unlabeled engineering smoke-tests only; they do not establish new evaluation evidence.

Raw source scores remain outside Git when licensing or repository policy requires it; Git stores only approved manifests, hashes, derived deterministic assignment IDs, protocol metadata, and aggregate evidence.

## 6. Eligible events

An event is eligible for pair construction only when:

1. S1-H-C completes without fail-closed error;
2. at least two distinct H-C `assignment_id` values exist;
3. all pair members belong to the same event, pitch set and tuning;
4. each member is present in the exact S1-H-C output for that event;
5. source `family_id` and event identity are stable.

No observed source fingering is used to create pairs or labels.

## 7. Label-blind pair construction

For every eligible event:

1. build the complete unordered assignment-pair set;
2. classify each pair as:
   - `FINGER_ONLY`: same pitch/string/fret voicing, different finger/barre assignment;
   - `MIXED`: different voicing and therefore potentially different finger assignment;
3. compute L1 distance between the two frozen 30-dimensional assignment feature vectors;
4. within each pair type, split distances deterministically into `NEAR`, `MID`, `FAR` strata using event-local rank terciles;
5. hash-sort pairs inside each non-empty `(pair_type, distance_stratum)` cell;
6. take at most one pair from each cell.

This yields at most six teacher tasks per event and creates both local and global contrasts without using Teacher preference.

If a cell is empty, no replacement pair is manufactured from another cell. Pair sampling is fixed before any response is collected.

## 8. Minimum corpus gate before real fit

Real S2-A fitting remains closed unless all are true:

- development families >= 40;
- development eligible events >= 200;
- decisive first-pass pairs >= 600;
- `FINGER_ONLY` decisive pairs >= 150;
- `MIXED` decisive pairs >= 150;
- each distance stratum contributes >= 100 decisive pairs in aggregate;
- no development family appears in untouched final;
- reliability repeat gate passes.

These are minimums, not sampling targets. More independent families are preferred over more pairs from the same family.

## 9. Reliability gate

Before any real fit:

- repeat at least `max(120, 20% of development tasks)` tasks;
- repeat interval: 24–72 hours;
- exactly 50% of repeat tasks reverse A/B presentation relative to first pass;
- old answer must not be visible or importable;
- compare the three-class response (`A`, `B`, `EQUAL_OR_UNSURE`) after decoding presentation reversal.

PASS requires:

- three-class exact agreement >= 0.85;
- decisive-only Cohen kappa >= 0.75;
- no task-identity mismatch;
- no response import from first pass.

If reliability fails, real fit remains closed. Repeat labels never become extra training rows even when agreement is perfect.

## 10. Frozen assignment feature contract

S2-A v1 uses exactly **30 deterministic, target-blind features**. All are computed from the S1-H-C assignment plus its S1-H-B/C metadata. No Teacher response, source identity, family ID, observed fingering, previous/next event, style, tempo or model prediction enters the vector.

`MAX_FRET = 24` remains the repository normalization authority.

### 10.1 Per-string features — 18

For strings `1..6`, in standard repository string numbering, emit three values per string:

1. `string_N_used` = 1 if the assignment uses the string, else 0;
2. `string_N_fret_norm` = `fret / 24` if used, else 0;
3. `string_N_finger_norm` = `finger / 4` if used, else 0.

Open strings therefore have `used=1`, `fret_norm=0`, `finger_norm=0`; unused strings are distinguished by `used=0`.

### 10.2 Aggregate geometry/resource features — 10

19. `open_note_ratio` = open used notes / used notes.
20. `mean_positive_fret_norm` = mean positive fret / 24, or 0 if none.
21. `positive_fret_span_norm` = positive-fret max-min / 24, or 0 if fewer than two positive fret values.
22. `used_string_span_norm` = `(max_used_string - min_used_string) / 5`.
23. `internal_string_gap_ratio` = internal unused positions divided by available internal positions, or 0 when no internal position exists.
24. `standard_finger_count_norm` = distinct positive finger IDs used / 4.
25. `barre_count_norm` = number of explicit H-C barres / 4.
26. `max_barre_span_norm` = maximum `(span_end - span_start) / 5`, or 0.
27. `total_barre_span_norm` = sum of `(span_end - span_start) / 20`.
28. `barre_override_note_ratio` = fretted notes above an underlying lower-fret barre inside that barre span / fretted notes, or 0.

### 10.3 Cross-finger mechanics — 2

29. `max_finger_fret_step_norm` = for adjacent active fingers ordered by finger number, max `((fret_j - fret_i) / (finger_j - finger_i)) / 24`, or 0 with fewer than two active fingers.
30. `same_fret_multi_finger_pair_ratio` = unordered active-finger pairs assigned to the same fret / 6.

All 30 values must be finite. Feature order is part of the contract and must be hash-pinned before fit.

## 11. Pairwise learning representation

For a teacher pair `(A, B)`:

- compute individual vectors `phi(A)` and `phi(B)`;
- use pair difference `delta = phi(A) - phi(B)`;
- decisive A preference maps to `y=1` for `delta`;
- decisive B preference maps to `y=0` for `delta`;
- each decisive original pair is mirrored once with `-delta` and `1-y` for exact numerical class symmetry;
- mirrored rows are bookkeeping augmentation, not additional independent evidence.

The model therefore learns one scalar utility:

`score(assignment) = w dot phi(assignment)`

and

`P(A preferred to B) = sigmoid(score(A) - score(B))`.

This ensures pair-order antisymmetry and allows all H-C assignments of an event to be ranked by one score.

## 12. Frozen v1 model family

No hyperparameter search is authorized in S2-A v1.

Frozen baseline learned model:

```text
LogisticRegression(
    penalty="l2",
    C=1.0,
    fit_intercept=False,
    class_weight=None,
    solver="lbfgs",
    max_iter=2000,
    random_state=0
)
```

No learned StandardScaler is used because the 30 features are already deterministically normalized and centering pair differences can introduce an effective intercept.

Inference:

1. recompute the exact H-C assignment set;
2. compute all 30 feature vectors;
3. score each assignment;
4. sort descending by score;
5. break exact score ties by stable `assignment_id` lexical order;
6. reject any model output referencing an assignment outside the supplied H-C set.

## 13. Preregistered non-learned baselines

Three deterministic baselines are reported:

- `HASH_BASELINE`: lexical-lowest assignment ID wins;
- `LOW_FRET_BASELINE`: lower `mean_positive_fret_norm` wins, then assignment ID;
- `COMPACT_BASELINE`: lower `positive_fret_span_norm` wins, then assignment ID.

During development CV, the stronger of `LOW_FRET_BASELINE` and `COMPACT_BASELINE` by macro-family accuracy becomes the single frozen comparator for untouched final. This baseline choice is made before final labels are opened.

## 14. Development evaluation

Use deterministic 5-fold family-isolated cross-validation.

Rules:

- `family_id` is the split unit;
- mirrored rows stay with their source pair and family;
- no event or family crosses train/validation within a fold;
- feature list, model family, C, solver and pair sampling are fixed;
- no threshold search;
- every family is evaluated exactly once out-of-fold.

Primary metrics on original, non-mirrored decisive pairs:

- pairwise accuracy;
- macro-family accuracy;
- ROC-AUC;
- log loss;
- Brier score;
- family wins/ties/losses versus the frozen comparator;
- accuracy by `FINGER_ONLY` / `MIXED`;
- accuracy by `NEAR` / `MID` / `FAR`.

Development PASS requires all of:

- pairwise accuracy >= 0.65;
- macro-family accuracy >= 0.65;
- ROC-AUC >= 0.70;
- macro-family accuracy delta versus selected comparator >= +0.05;
- family wins > family losses versus comparator;
- `FINGER_ONLY` accuracy >= 0.60 when that slice has >=100 decisive pairs;
- `MIXED` accuracy >= 0.60 when that slice has >=100 decisive pairs;
- no leakage/invariant violation;
- 10/10 same-environment reruns produce identical pair predictions, rankings and aggregate metrics.

If development fails, untouched final is not opened and post-hoc model-family/hyperparameter changes require a new protocol version.

## 15. Frozen all-development model before final

Only after development PASS:

1. fit the frozen model once on all eligible development first-pass decisive pairs;
2. record feature-list hash, training-row manifest hash, library versions, coefficients and model artifact hash;
3. freeze the comparator chosen during development;
4. freeze all final-test code and metric definitions;
5. only then open the untouched final responses.

No final-test-driven retraining or retuning is permitted.

## 16. Untouched final evaluation

Minimum final evidence:

- untouched final families >= 20;
- decisive final pairs >= 200;
- final families disjoint from all S2-A development families;
- final labels never previously inspected for model decisions.

Final PASS requires all of:

- pairwise accuracy >= 0.65;
- macro-family accuracy >= 0.65;
- ROC-AUC >= 0.70;
- macro-family accuracy delta versus the frozen comparator >= +0.05;
- family wins > family losses;
- `FINGER_ONLY` accuracy >= 0.60 when slice size >=50;
- `MIXED` accuracy >= 0.60 when slice size >=50;
- family-block bootstrap 95% confidence interval for accuracy delta versus comparator has lower bound > 0;
- zero candidate-authority violations;
- zero use of final labels for fit/tuning/selection.

If final PASSes, status becomes only:

`ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`

It does **not** automatically retain a checkpoint, activate a ranker in GuitarTab Engine, or authorize production.

## 17. Failure handling

- Reliability FAIL → no fit.
- Corpus minimum FAIL → no fit.
- Development FAIL → no untouched final consumption; revise only under a new preregistration version.
- Untouched final FAIL → no checkpoint retention/promotion.
- Any H-C lineage mismatch → fail closed.
- Any out-of-set model assignment ID → runtime error, never legalization.

## 18. Explicit non-goals of S2-A v1

S2-A v1 does not model:

- transitions from previous fingering;
- future chord anticipation;
- tempo/duration;
- melody/voice-leading continuity;
- right-hand fingering;
- tone/resonance/style goals;
- player anatomy/profile;
- extended left-hand techniques;
- sequence-level optimization.

Those belong in later, separately evaluated specialists after the static ranker is scientifically established.

## 19. Gate state

This preregistration freezes a design only.

- pair-package implementation: not authorized by this document alone;
- real Teacher collection: not automatically authorized by this document alone;
- real model fit: **CLOSED**;
- checkpoint retention: **CLOSED**;
- GuitarTab Engine shadow/production integration: **CLOSED**.

A later explicit execution step may implement the frozen data/feature/evaluation machinery without changing these scientific definitions. Real fit must use this or a newer merged preregistered protocol exactly.