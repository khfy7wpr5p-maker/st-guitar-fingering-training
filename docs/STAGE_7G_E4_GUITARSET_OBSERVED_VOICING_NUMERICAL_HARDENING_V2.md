# Stage 7G-E4 — GuitarSet v2 Numerical Evidence Hardening

## Decision

`NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`

The retained `GUITARSET-OBSERVED-VOICING-MODEL.v2` checkpoint now has supplemental first-order numerical and optimizer-termination evidence. This evidence does not rewrite the historical model, reopen validation/final, replace the checkpoint, authorize refit, connect runtime, or authorize production.

## Immutable identity

- base training main: `959ed78df27ce49a44ff1c444d329fc871abb334`
- controlled capture head: `f19c52615ff26352ca0e377826989f3594b1c9a5`
- capture workflow run: `32655541511`
- capture job: `97233537745`
- artifact: `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json`
- artifact byte SHA-256: `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`
- internal evidence SHA-256: `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`
- retained model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`

## Controlled surface

- data role: DEVELOPMENT only;
- ambiguous events: `7,919`;
- selected pairs: `171,452`;
- symmetric training rows: `342,904`;
- features: `28`;
- selected-pair identity SHA-256: `6bc82ad12e99cafcdb26632b33e2240ed5f33c7a3e785a5594f744013d0c7663`;
- validation access: false;
- final access: false.

The reconstruction used Python `3.13.15`, numpy `2.3.5`, scipy `1.17.0`, and scikit-learn `1.8.0`.

## Numerical result

- optimizer: `L-BFGS-B`;
- status: `0` / success;
- termination: `CONVERGENCE: NORM OF PROJECTED GRADIENT <= PGTOL`;
- resolved tolerance: `1e-4`;
- iterations: `37` of maximum `2,000`;
- function evaluations: `39`;
- gradient evaluations: `39`;
- sealed-model objective: `0.029548918364167603`;
- sealed-model gradient L2 norm: `0.00012675530517663626`;
- sealed-model gradient infinity norm: `0.00008273717518741651`;
- sealed-model stationarity within resolved tolerance: true;
- accepted objective trace: non-increasing;
- reconstructed coefficient maximum absolute delta: `5.4577231622943145e-11`;
- training-score maximum absolute delta: `3.269491344326525e-10`;
- mathematically derived score-delta limit: `4.415294255815478e-9`.

All numerical gates passed. The diagnostic reconstruction reproduced the recorded `n_iter=37` while leaving the sealed checkpoint bytes unchanged.

## Authority boundary

- historical model rewritten: false;
- checkpoint replacement authorized: false;
- model mutation/refit authorized: false;
- validation/final access authorized: false;
- runtime connection authorized: false;
- production authorized: false;
- `fret20QualityAuthority=false`.

The next consequential gate remains `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`.
