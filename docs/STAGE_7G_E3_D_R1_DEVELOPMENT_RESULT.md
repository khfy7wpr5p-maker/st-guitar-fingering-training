# Stage 7G-E3-D-R1 — Conservative Compact-Gate Development Result

## Scope

This document records the completed Stage 7G-E3-D-R1 manual Colab execution. The run is **nested development CV, not untouched validation**. It does not authorize checkpoint retention, model promotion, production integration, or GuitarTab Engine shadow integration.

The exact user-exported aggregate result file was `ST_Guitar_Stage7G_E3_D_R1_result.json` with SHA-256:

`5626a1ea70a2bc285d3585ec2f155eb86040ece6507a03dd6a477dd073ec67d3`

The repository stores only aggregate evidence. Raw Teacher-GOLD rows remain outside Git.

## Execution identity

- repository: `khfy7wpr5p-maker/st-guitar-fingering-training`
- approved execution SHA: `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`
- actual execution SHA: `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`
- Python: `3.12.13`
- NumPy: `2.0.2`
- scikit-learn: `1.6.1`
- protocol: `7G-E3-D`

## Sealed inputs and preflight

The preflight status was exactly:

`PREFLIGHT_PASS_STOP_BEFORE_TRAIN`

Verified inputs:

- curriculum package SHA-256: `e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`
- audit SHA-256: `e8fa34998a409a275d372ae089b9a3f3ed1ea5b53de5c15e58a61de0210a2915`
- teacher manifest SHA-256: `433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2`
- choices SHA-256: `db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e`
- frozen feature-list SHA-256: `6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3`

Preflight reproduced:

- 400 Teacher-GOLD tasks
- 399 decisive binary rows
- 1 equal/unsure row excluded from fit/evaluation
- 40 source families
- L1=140, L2=120, L3=80, L4=60
- decoded preferences: `OPEN_LOW=311`, `COMPACT=88`, `EQUAL_OR_UNSURE=1`
- exactly 40 frozen target-blind features
- 5 outer / 4 inner family-isolated splits
- outer random state `731`
- inner random states `7310..7314`

## Frozen model and threshold protocol

No model-family, feature, C, class-weight, calibration, or threshold search was introduced after labels were observed.

The frozen model remained:

- `StandardScaler()`
- `LogisticRegression(max_iter=2000, class_weight=None, C=1.0, solver="lbfgs", random_state=0)`
- positive class: `COMPACT`
- default decision: `OPEN_LOW`
- candidate thresholds: `[0.50, 0.60, 0.70, 0.80, 0.90, 0.95]`
- threshold selection: inner out-of-fold predictions only

Selected thresholds by outer fold were:

`[0.5, 0.5, 0.6, 0.5, 0.5]`

## Aggregate result

Final frozen nested-CV result:

`POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`

| Metric | Result |
|---|---:|
| Events | 399 |
| Event accuracy | 86.22% |
| `always_open_low` event baseline | 77.94% |
| Event delta | **+8.27 pp** |
| Macro-family accuracy | 86.18% |
| Macro-family baseline | 78.34% |
| Macro-family delta | **+7.84 pp** |
| Compact precision | 77.97% |
| Compact recall | 52.27% |
| Compact TP / FP / FN | 46 / 13 / 42 |
| Compact switch count | 59 |
| Compact switch rate | 14.79% |
| Family win / tie / loss | 22 / 13 / 5 |

Curriculum-level diagnostics:

| Level | Events | Accuracy | Compact switches | Switch rate |
|---|---:|---:|---:|---:|
| L1 | 140 | 97.14% | 9 | 6.43% |
| L2 | 120 | 73.33% | 4 | 3.33% |
| L3 | 80 | 90.00% | 19 | 23.75% |
| L4 | 59 | 81.36% | 27 | 45.76% |

## Frozen development-gate decision

All preregistered continuation conditions passed:

1. event delta > 0: **PASS**
2. macro-family delta > 0: **PASS**
3. pooled compact precision > 0.5: **PASS**
4. compact TP > FP: **46 > 13 — PASS**
5. family wins > losses: **22 > 5 — PASS**

Therefore the only authorized scientific conclusion is:

> The conservative compact-gate hypothesis has a positive development signal and is eligible for Stage 7G-E3-E untouched-validation design.

This is not a promotion result.

## Safety state

- Stage 7E mounted or used: **no**
- checkpoint retained: **no**
- production integration: **no**
- shadow integration: **not authorized**
- raw Teacher-GOLD rows committed to Git: **no**

The prior 40-family Teacher-GOLD development domain has influenced E1/E2/E3 hypothesis development. It therefore cannot serve as the Stage 7G-E3-E untouched family-disjoint validation set.
