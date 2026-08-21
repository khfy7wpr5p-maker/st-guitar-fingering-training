# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 VALIDATION RESULT

## Result

Accepted validation evidence status:

`VALIDATION_PASS_FINAL_STILL_CLOSED`

The sealed DEVELOPMENT model was evaluated on performer `03` without refit or tuning.

- validation recordings: 30
- accepted notes: 6,722
- quarantined notes: 3
- derived voicings: 2,016
- ambiguous ranking voicings: 1,890
- single-candidate voicings excluded from ranking metrics: 126
- full exact candidate count across all validation voicings: 51,716

## Metrics

| Metric | Baseline | Sealed model | Delta |
|---|---:|---:|---:|
| Event Top-1 | 0.621693 | 0.770370 | +0.148677 |
| Event MRR | 0.713209 | 0.882055 | +0.168846 |
| Recording-macro Top-1 | 0.575752 | 0.744652 | +0.168901 |
| Recording-macro MRR | 0.668564 | 0.868435 | +0.199870 |

Learned Recall@3: `0.9968253968`.

The frozen 2000x recording-block bootstrap, seed 0, gives:

- lower 95% order-statistic bound: `0.07505422203438902` at zero-based index `49`;
- upper descriptive bound: `0.2655305264004872` at zero-based index `1949`;
- bootstrap mean: `0.1686459147667668`.

Every preregistered validation gate passes.

Accepted evidence SHA-256:

`13b706076205abea42a436d10cf019a36445035e08172054989191121ff59e51`

Validation event identity SHA-256:

`a68c6aaa223119e8176ebca3a00e167d58a2565aa26a6eec07ce6269a1a6d73b`

## Run-01 invalidation

The first workflow execution is **not** accepted as validation evidence. The pre-outcome request and test fixed the lower bootstrap order statistic at zero-based index `49`, but a floating-point quantile-index calculation produced `50`. Normal CI caught the mismatch (`50 != 49`).

That run is permanently recorded as:

`INVALIDATED_IMPLEMENTATION_DEVIATION_DO_NOT_USE_FOR_GATE`

The correction did not change the model, features, thresholds, source, validation performer, bootstrap repetitions, seed, confidence level, or sampling sequence. It replaced only the floating-point-derived lower index with the already-predeclared literal index `49`. The corrected run remained PASS with the more conservative lower bound `0.07505422203438902 > 0`.

Run-01 invalidation evidence is stored separately in `evidence/stage7g_e3_guitarset_observed_voicing_validation_run01_invalidated_v1.json`.

## Safety state

- DEVELOPMENT model refit: **false**
- hyperparameter tuning: **false**
- performer `02` opened: **false**
- checkpoint authorized: **false**
- runtime connection authorized: **false**
- final access authorized: **false**

Validation PASS therefore authorizes only the next explicit gate:

`OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW`

It does not itself open performer `02`.
