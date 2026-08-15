# Stage 7G-E3-D — Conservative compact-gate training protocol

## Status

**Protocol freeze only. No model is fitted in this stage. No checkpoint is retained and no production integration is authorized.**

This protocol is defined after the negative Stage 7G-E1 Teacher-GOLD router, the Stage 7G-E2 false-positive diagnostic, the E3-A 40-descriptor ergonomics contract, and the newly sealed E3 curriculum Teacher-GOLD Batch01 responses.

The purpose is narrow: test whether a target-blind, interpretable model can safely recover some teacher-preferred `compact` decisions while keeping `open_low` as the default. The deterministic physical engine remains the sole authority for physical validity.

## Why the policy is conservative

Stage 7G-E1 recovered 66 teacher-`compact` cases but created 107 false `compact` switches. Relative to always choosing `open_low`, that was a net loss of 41 correct decisions. E3-D therefore does not treat the two classes symmetrically at decision time.

Frozen policy:

- default action: `OPEN_LOW`;
- the model may switch to `COMPACT` only through an inner-CV-selected high-confidence threshold;
- if no threshold satisfies the frozen safety criteria, the fold uses `NO_SWITCH` and predicts `OPEN_LOW` for every event;
- no threshold may be selected after inspecting an outer-fold result.

## Training/development corpus

The E3-D fit corpus is **only the new E3 curriculum Batch01 pairwise Teacher-GOLD batch** sealed in Stage 7G-E3-C.

Required external inputs:

1. `ST_Guitar_Stage7G_E3_B_R1_Curriculum_Batch01_400.zip`
   - SHA-256: `e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`
   - internal audit SHA-256: `e8fa34998a409a275d372ae089b9a3f3ed1ea5b53de5c15e58a61de0210a2915`
   - blind teacher manifest SHA-256: `433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2`
2. `ST_Guitar_E3_Batch01_choices_400of400.json`
   - SHA-256: `db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e`

Preflight must reproduce:

- 400 task IDs;
- exact task-set match;
- 40 source families;
- L1=140, L2=120, L3=80, L4=60;
- Teacher-GOLD decoded counts: `open_low=311`, `compact=88`, `EQUAL_OR_UNSURE=1`;
- decisive binary fit rows: 399.

The single `EQUAL_OR_UNSURE` row is retained in audit counts but excluded from binary fit and binary metrics.

The prior 556 decisive E1/E2 pairwise rows are **not** added to E3-D fit data. They influenced hypothesis development and are already consumed development evidence. The historical first 38 full-candidate labels remain a different semantic label type and are also excluded.

Stage 7E is forbidden.

## Frozen target-blind representation

Model input is exactly `STAGE7G_E3_FEATURE_NAMES` from the merged E3-A contract: **40 descriptors**, in the frozen order.

Feature-list SHA-256, computed as SHA-256 of the UTF-8 feature names joined by newline, is:

`6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3`

The 40 descriptors are:

- 7 current chord/candidate-set descriptors;
- 11 `open_low` proposal geometry descriptors;
- 11 `compact` proposal geometry descriptors;
- 11 `compact_minus_open` geometry deltas.

Forbidden model inputs include:

- teacher A/B display side;
- decoded Teacher-GOLD label;
- task ID;
- family ID;
- source file/name/path/hash;
- source TAB/string-fret target information;
- curriculum level;
- rule-derived property target/value;
- Stage 7E information;
- previous-event or future-event context.

`family_id` is permitted only as the split-group key. `curriculum_level` is permitted only for aggregate reporting after predictions are frozen.

## Frozen model

Positive class: `COMPACT`.

Pipeline:

1. `StandardScaler()` fit inside each training fold only;
2. `LogisticRegression(`
   - `max_iter=2000`,
   - `class_weight=None`,
   - `C=1.0`,
   - `solver="lbfgs"`,
   - `random_state=0`
   `)`.

`class_weight=None` is intentional. The earlier balanced E1 model over-switched to compact; E3-D tests a naturally prevalence-aware probability model plus a conservative decision gate.

There is no regularization search, class-weight search, feature selection, feature-subset search, model-family search, calibration search, or sequence model in E3-D.

## Nested family-isolated development CV

This is **nested development CV**, not untouched final validation. Prior E1/E2 analysis used the same 40-family development domain, so even outer E3-D folds must not be described as fresh family-disjoint final evidence.

Outer split:

- `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=731)`;
- group key: source family;
- target: binary Teacher-GOLD preference on decisive rows only.

For each outer fold, threshold selection is performed only inside that outer training partition.

Inner split:

- `StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=7310 + outer_fold_index)`;
- inner OOF probabilities are generated for every row in the outer-training partition;
- scalers and logistic models are re-fit separately inside each inner training fold.

Preflight must abort before fitting if any split leaks a family between train and held-out partitions, if an outer/inner training fold lacks either binary class, or if any model feature is non-finite.

## Frozen compact-threshold selection

Candidate probability thresholds are fixed before training:

`[0.50, 0.60, 0.70, 0.80, 0.90, 0.95]`

For each outer fold, compute metrics for each threshold using **only pooled inner OOF probabilities** from the outer-training families.

A threshold is eligible only if all are true:

1. at least 10 inner-OOF events are predicted `COMPACT`;
2. `compact_precision >= 2/3`;
3. inner event-weighted accuracy is at least the inner `always_open_low` accuracy.

Among eligible thresholds choose, in order:

1. highest `compact_recall`;
2. then highest event-accuracy delta versus `always_open_low`;
3. then highest `compact_precision`;
4. then the **higher** probability threshold.

If no candidate is eligible, select `NO_SWITCH`. `NO_SWITCH` predicts `OPEN_LOW` for every outer-test event.

Outer-test labels must never affect threshold choice. After an outer result is observed, its threshold cannot be changed.

## Frozen reporting metrics

Aggregate outer OOF predictions must report at minimum:

- event-weighted Teacher-GOLD agreement;
- always-`open_low` event accuracy and delta;
- macro-family Teacher-GOLD agreement;
- always-`open_low` macro-family accuracy and delta;
- `compact` precision;
- `compact` recall;
- `compact` true positives;
- `compact` false positives;
- `compact` false negatives;
- predicted compact switch count/rate;
- family win/tie/loss versus always-`open_low`;
- per-outer-fold selected threshold or `NO_SWITCH`;
- L1/L2/L3/L4 aggregate accuracy and compact-switch rate for diagnosis only.

Curriculum-level metrics cannot be used to alter the already-frozen model or thresholds in the same run.

## Development interpretation gate

This gate controls only whether the result is worth carrying forward to design a new untouched E3-E Teacher-GOLD test. It does **not** authorize checkpoint retention or production use.

`POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN` requires all of:

1. outer pooled event accuracy delta versus always-`open_low` > 0;
2. macro-family accuracy delta versus always-`open_low` > 0;
3. outer pooled `compact_precision > 0.50`;
4. outer pooled compact true positives > compact false positives;
5. family wins > family losses.

Otherwise the result is `NEGATIVE_DEVELOPMENT_CV_NO_PROMOTION`.

No minimum percentage-point improvement is being declared as a production gate here because this corpus is development-overlapping and cannot authorize promotion.

## Colab execution boundary

E3-D training may begin only after this protocol is merged and a Colab notebook is pinned to the resulting exact Git SHA.

The notebook must follow `COLAB_MANUAL_TRAINING_CONTROL.md`:

1. clone and checkout exact approved SHA;
2. install package and print Python/NumPy/scikit-learn versions;
3. upload the two required external artifacts;
4. verify outer ZIP, manifest, audit, and choice SHA-256 values;
5. print the full preflight report and STOP;
6. user manually runs the clearly separated TRAIN cell;
7. run only the frozen nested evaluation;
8. export aggregate evidence JSON.

Default output flags:

- `checkpoint_retained=false`;
- `production_integration=false`.

No model file is retained by default.

## Closed gates

- E3-D model fit: not executed by this protocol PR;
- Colab run: not executed;
- E3-E untouched validation: not created;
- checkpoint retention: no;
- production integration: no;
- automatic teacher-feedback learning: no;
- Stage 7E reuse: forbidden.
