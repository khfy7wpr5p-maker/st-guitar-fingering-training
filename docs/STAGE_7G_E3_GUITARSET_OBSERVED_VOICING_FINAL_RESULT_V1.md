# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 UNTOUCHED FINAL RESULT

## Result

Accepted untouched-final evidence status:

`FINAL_PASS_ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`

The exact sealed DEVELOPMENT model was evaluated once on performer `02` with no refit and no tuning.

Final source:

- recordings: 30
- accepted notes: 7,194
- quarantined notes: 33
- derived voicings: 2,210
- ambiguous ranking voicings: 1,816
- single-candidate voicings excluded from ranking metrics: 394
- full exact candidate count across all final voicings: 27,718

## Metrics

| Metric | LOW_TOTAL_FRET.v1 | Sealed model | Delta |
|---|---:|---:|---:|
| Event Top-1 | 0.425661 | 0.688326 | +0.262665 |
| Event MRR | 0.600337 | 0.836308 | +0.235971 |
| Recording-macro Top-1 | 0.429336 | 0.662275 | +0.232939 |
| Recording-macro MRR | 0.609288 | 0.822366 | +0.213078 |

Learned Recall@3: `0.9950440529`.

The frozen 2000x recording-block bootstrap, seed 0, gives:

- lower 95% order-statistic bound: `0.1036506366023133` at zero-based index `49`;
- upper descriptive bound: `0.35892659280807027` at zero-based index `1949`;
- bootstrap mean: `0.2354086714268711`.

Every preregistered untouched-final gate passes.

Accepted evidence SHA-256:

`c883fbbe076ea1bc098357cd70aca592a3a95a7fedf0174cab2bdf95dcb4e57e`

Final event identity SHA-256:

`cd9eef90ae4d5e5ea45185aa81ad76ee2e341d85d2dd7624acd74fc7f94478a1`

Workflow artifact ZIP SHA-256:

`945e781a6dccfea0a2a37c8fb8251e0ff068d68ede5cf6553def9b7469085317`

## Safety state

- DEVELOPMENT model refit: **false**
- hyperparameter tuning: **false**
- performer `02` opened: **true**
- final PASS: **true**
- checkpoint-retention review eligible: **true**
- checkpoint authorized: **false**
- runtime connection authorized: **false**
- production authorized: **false**

The next gate is therefore:

`CHECKPOINT_RETENTION_REVIEW`

This result does not itself retain a checkpoint or authorize shadow/production use.
