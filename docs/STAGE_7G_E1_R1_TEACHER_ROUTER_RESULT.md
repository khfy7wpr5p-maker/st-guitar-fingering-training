# Stage 7G-E1-R1 — Teacher-GOLD pairwise router validation result

## Scope

This stage executes the merged Stage 7G-E1 preregistered development experiment on the completed blind Teacher-GOLD pairwise labels. It is development cross-validation only. It does **not** retain a checkpoint and does **not** authorize production integration.

The direct runtime available to this project session cannot launch a Google Colab kernel. Therefore the experiment was executed as a deterministic local reproduction of the merged protocol at `bd6e894fd239f521f1880240d701cf2f6a5c234a`. A separate Colab reproduction notebook was prepared externally so the same pinned experiment can be independently rerun in Colab.

## Inputs

- sealed teacher manifest SHA-256: `3d3fbf9d0107ef8a1a31e597820b687a072fa0f2cc5123b8e59adbbf07e4a167`
- completed blind choice export SHA-256: `87aecd6f26f3aa450bb71524fd4205afefa77cb9aee8b8741577f8a0f169afde`
- pairwise tasks: 562
- decisive labels used: 556
- `EQUAL_OR_UNSURE` preserved and excluded from binary fit: 6
- independent families: 40
- decoded teacher preference inside this disagreement-enriched batch: `open_low` 433, `compact` 123
- first 38 full-candidate choices used in this binary experiment: no
- Stage 7E reused: no

Raw teacher response rows remain outside Git.

## Frozen model and split

The run uses the already-merged Stage 7G-E1 specification without search or tuning:

- target-blind stateless `open_low` vs `compact` router
- exactly 15 fixed current-event features
- `StandardScaler`
- `LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, solver="lbfgs", random_state=0)`
- probability threshold 0.5
- deterministic 5-fold family-isolated cross-validation
- required reference baseline: always choose `open_low`

No threshold search, hyperparameter search, calibration, feature selection, or sequence context was added after seeing the labels.

## Aggregate result

| Metric | Teacher-GOLD router | Always `open_low` | Delta |
|---|---:|---:|---:|
| Event-weighted accuracy | **70.50%** | **77.88%** | **-7.37 pp** |
| Macro family accuracy | **70.37%** | **77.95%** | **-7.57 pp** |

Additional diagnostic metrics:

- macro fold balanced accuracy: **64.13%**
- macro fold `open_low` recall: **75.29%**
- macro fold `compact` recall: **52.97%**

Fold accuracy deltas versus always-`open_low` were:

1. -1.79 pp
2. 0.00 pp
3. -11.61 pp
4. -26.85 pp
5. +2.65 pp

Only one fold improves over the baseline; one ties and three are worse.

## Interpretation

The fixed router is not empty: balanced accuracy above 0.5 and non-zero `compact` recall show that the 15-feature model learns some signal associated with teacher `compact` preferences. However, the primary practical objective is to choose the teacher-preferred proposal. On that objective the router is materially worse than the preregistered always-`open_low` baseline.

This result therefore produces **no promotion** and **no checkpoint**.

The most obvious temptation would be to change the class weighting, decision threshold, features, or regularization after seeing this result. That is intentionally not done here. Such a change would be a new hypothesis and must be preregistered as a separate experiment rather than tuned against these same family-isolated CV outcomes and then presented as if it were untouched evidence.

## Scientific boundary

- development CV complete: yes
- checkpoint retained: no
- production integration: no
- Stage 7E reused: no
- sequence context used: no
- raw teacher rows committed: no
- post-hoc threshold/hyperparameter tuning: no
- promotion: **NO**

The next research decision should be made only after this negative result is reviewed. A follow-up experiment may be proposed, but it must explicitly distinguish hypothesis development on the already-consumed Teacher-GOLD development corpus from any future untouched validation corpus.
