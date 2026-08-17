# Stage 7G-E3-S1-F — Component Training Preparation

## Status

Preparation only. No S1-D or S1-E project labels are read or fitted in this stage.

The purpose of S1-F is to remove idle time while reliability work continues. It prepares a fixed, target-blind training/evaluation harness for three future micro-specialists:

- `STRING_SKIP_PENALTY`
- `OPEN_STRING_HAND_RELIEF`
- `OPEN_STRING_CONTROL_PENALTY`

## Scientific boundary

S1-F does **not** authorize training execution.

Model fitting on project labels stays closed until all of the following are true:

1. a new independent full component-reliability test has status `PASS`;
2. a separate component-training protocol is reviewed and merged;
3. pilot labels are excluded from training;
4. repeat labels are excluded from training, tuning, and model selection;
5. validation threshold is not tuned on the same validation labels;
6. checkpoint retention and production/shadow integration remain separately closed.

The preparation API therefore requires a fail-closed `st-guitar-stage7g-e3-s1f-training-authorization-v1` object before its in-memory baseline `fit()` path can execute.

## Feature contract

S1-F reuses the already-frozen target-blind Stage 7G-E3 proposal geometry rather than creating a second guitar-geometry definition.

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

## Label contract

Future supervised rows may be constructed only from a separately authorized `FULL_RELIABILITY_FIRST_PASS` source.

- `YES -> 1`
- `NO -> 0`
- `UNSURE -> excluded from fit`

The code rejects provenance containing `PILOT` or `REPEAT`.

## Family-safe validation

The harness uses deterministic five-fold assignment at the `family_id` level. A family may never appear in both the training and validation partition for the same fold.

The split does not use Teacher labels.

## Fixed baseline

The prepared baseline is intentionally simple and fixed:

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

The threshold is not searched or tuned in S1-F.

Evaluation reports accuracy, balanced accuracy, YES precision/recall/F1, TN/FP/FN/TP, and constant/majority baseline comparison.

No promotion threshold is defined in this preparation stage.

## What happens after reliability

If the future full reliability test passes, a separate training-protocol PR must define the exact eligible first-pass corpus, minimum sample/family counts, final cross-validation policy, model-retention gate, and comparison criteria. Only after that protocol is merged may real component training execution be authorized.
