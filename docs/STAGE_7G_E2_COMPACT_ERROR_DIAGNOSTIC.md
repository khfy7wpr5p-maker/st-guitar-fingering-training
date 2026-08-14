# Stage 7G-E2 — compact preference error diagnostic

Stage 7G-E1-R1 is a negative development result: the fixed Teacher-GOLD router reached 70.50% event-weighted teacher agreement while the preregistered `always_open_low` baseline reached 77.88%. Stage 7G-E2 does **not** attempt to rescue that result by retuning the same 556 labels.

## Goal

Explain the failure structure before proposing another model. The diagnostic is limited to three questions:

1. Which exact out-of-fold error types did E1 make, especially compact false negatives versus compact false positives?
2. Does teacher preference vary systematically across a small, fixed set of target-blind guitar geometry differences between the `open_low` and `compact` proposals?
3. How heterogeneous are teacher preference and E1 accuracy across the 40 family-isolated source families?

## Frozen inputs

The diagnostic reuses only the already-consumed Stage 7G development Teacher-GOLD pairwise set:

- 562 blind pairwise tasks,
- 556 decisive A/B labels,
- 6 `EQUAL_OR_UNSURE` labels excluded,
- 40 families,
- first 38 full-candidate choices excluded,
- Stage 7E excluded.

The input manifest and completed teacher export are pinned by the same SHA-256 values as Stage 7G-E1-R1.

## No new model fit

E2 regenerates the exact E1 five-fold family-isolated out-of-fold predictions with the already-fixed StandardScaler + balanced LogisticRegression configuration. It does not alter:

- features,
- class weights,
- `C`,
- solver,
- decision threshold,
- fold assignment.

No additional classifier, feature selector, threshold search, calibration, or checkpoint is allowed in this stage.

## Fixed target-blind geometry diagnostic

For each specialist proposal, E2 computes only current-voicing geometry available without teacher labels or source TAB:

- open-note count,
- fretted-note count,
- minimum positive fret,
- mean positive fret,
- maximum fret,
- positive-fret span,
- number of unique positive frets,
- maximum notes sharing one positive fret,
- string span,
- adjacent-string ratio,
- internal string gaps.

The diagnostic records `compact - open_low` deltas. `max_same_positive_fret_count` is only a barre-like geometry proxy; it is **not** a true left-hand finger assignment.

The strata are fixed before running the diagnostic: chord size, candidate-count range, open-note delta, mean-positive-fret delta, positive-fret-span delta, same-fret proxy delta, and internal-string-gap delta.

## Interpretation boundary

A pattern discovered here is a hypothesis generator only. We must not use the same 556 labels to invent a new feature/model and then describe performance on those same labels as fresh validation. Any E2-derived model hypothesis must be evaluated either on new disjoint Teacher-GOLD data or under a separately preregistered nested evaluation design.

## Closed gates

- checkpoint retention: **closed**
- production integration: **closed**
- Stage 7E reuse: **forbidden**
- sequence context: **not used**
- raw Teacher-GOLD rows in Git: **forbidden**
