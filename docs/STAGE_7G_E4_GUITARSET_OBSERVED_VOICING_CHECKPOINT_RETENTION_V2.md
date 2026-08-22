# Stage 7G-E4 — GuitarSet Observed Voicing Checkpoint Retention v2

## Decision

`CHECKPOINT_RETAINED_RESEARCH_ONLY_SHADOW_REVIEW_ELIGIBLE`

The exact sealed `GUITARSET-OBSERVED-VOICING-MODEL.v2` DEVELOPMENT artifact is retained as an immutable research checkpoint after preregistered DEVELOPMENT, one-shot VALIDATION performer `03`, and one-shot UNTOUCHED_FINAL performer `02` all passed.

This review does not retrain, refit, tune, recalibrate, rewrite, or copy model parameters. Retention is a separate sealed decision pointing to the exact existing artifact.

## Retained identity

- model: `GUITARSET-OBSERVED-VOICING-MODEL.v2`
- artifact: `evidence/stage7g_e4_guitarset_observed_voicing_development_model_v2.json`
- artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`
- accepted final evidence SHA-256: `8aab8f841cf2a5e5a6e6437a8f2207026465b1863fdc064629e2818eae6a67b2`

## Scientific boundary of the 0–20 expansion

The retained v2 model scores candidates in fret domain `0..20`, while the observed GuitarSet positive-gold domain remains `0..19`.

The final evidence contains zero observed positive fret-20 gold examples. Therefore retention does **not** claim that fret-20 quality has been empirically validated. `fret20_quality_authority=false` remains mandatory.

The v2 expansion is retained because it removes the previous technical domain mismatch and has passed DEVELOPMENT, VALIDATION, and UNTOUCHED_FINAL against the frozen baseline. It does not convert extrapolation at fret 20 into teacher/ground-truth authority.

## Retention semantics

Retention authorizes only preservation and exact reference of this immutable research checkpoint.

Still closed:

- checkpoint mutation: **false**
- refit: **false**
- tuning: **false**
- validation reuse for training: **false**
- untouched-final reuse for training: **false**
- shadow integration: **false**
- runtime connection: **false**
- production authority: **false**
- fret-20 quality authority: **false**

## Next gate

`SHADOW_INTEGRATION_REVIEW`

That next gate is not authorized by this retention decision. A separate review is required before the checkpoint can be wired into any shadow inference seam. Even such a future shadow seam must remain non-authoritative unless a later explicit authority gate says otherwise.
