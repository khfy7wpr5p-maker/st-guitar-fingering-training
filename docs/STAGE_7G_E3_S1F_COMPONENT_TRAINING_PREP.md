# Stage 7G-E3-S1-F — Component Training Preparation

## Status

Preparation only. No S1-D or S1-E project labels are read or fitted in this stage.

S1-F prepares a fixed, target-blind training/evaluation contract for three future micro-specialists:

- `STRING_SKIP_PENALTY`
- `OPEN_STRING_HAND_RELIEF`
- `OPEN_STRING_CONTROL_PENALTY`

## Scientific boundary

S1-F does **not** authorize training execution.

The executable `fit_component_specialist()` path is hard-closed in this preparation PR. No caller-supplied dictionary, including one claiming `PASS` and `MERGED`, can open it.

A later, separate training-protocol PR may replace that hard-close only after:

1. a new independent full component-reliability test has status `PASS`;
2. the exact eligible first-pass corpus is defined;
3. pilot labels remain excluded from training;
4. repeat labels remain excluded from training, tuning, and model selection;
5. validation/model-retention gates are preregistered;
6. that separate training protocol is reviewed and merged.

Checkpoint retention and production/shadow integration remain separately closed.

## Feature contract

S1-F reuses the already-frozen target-blind Stage 7G-E3 proposal geometry.

The 15 frozen input features are:

1. `chord_size`
2. `pitch_span`
3. `mean_pitch`
4. `candidate_count`
5. `open_note_count`
6. `fretted_note_count`
7. `min_positive_fret`
8. `mean_positive_fret`
9. `max_fret`
10. `positive_fret_span`
11. `unique_positive_frets`
12. `max_same_positive_fret_count`
13. `string_span`
14. `adjacent_string_ratio`
15. `internal_string_gaps`

Teacher answers are never used to construct these features. Geometry is descriptive input, not a rule-derived label.

Every voicing entering the feature builder must belong to the authoritative deterministic `valid_chord_voicings()` candidate set. The two open-string specialists additionally fail closed if the candidate contains no open string.

## Label and provenance contract

Future supervised rows may be constructed only when provenance is **exactly**:

`FULL_RELIABILITY_FIRST_PASS`

Prefix, suffix, substring, pilot, repeat, and manually named alternatives are rejected.

- `YES -> 1`
- `NO -> 0`
- `UNSURE -> excluded from fit`

Provenance is validated **before** `UNSURE` can be excluded, so an `UNSURE` row from a forbidden source is rejected rather than silently discarded.

## Family-safe validation

The harness uses deterministic five-fold assignment at the `family_id` level. A family may never appear in both the training and validation partition for the same fold. The split does not use Teacher labels.

## Fixed baseline

The preparation stage may construct, but not fit, this frozen baseline:

```text
StandardScaler
→ LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    solver="lbfgs",
    random_state=0
  )
→ probability threshold 0.5
```

The threshold is not searched or tuned in S1-F. Evaluation helpers report accuracy, balanced accuracy, YES precision/recall/F1, TN/FP/FN/TP, and constant/majority baseline comparison.

No promotion threshold is defined in this preparation stage.

## What happens after reliability

If the future full reliability test passes, a separate training-protocol PR must define the exact eligible first-pass corpus, minimum sample/family counts, final cross-validation policy, model-retention gate, and comparison criteria. Only that later merged change may open real component training execution.
