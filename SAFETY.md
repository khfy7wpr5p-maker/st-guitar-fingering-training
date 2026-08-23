# Safety and scientific authority

## Live safety statement

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

Deterministic physical validity is authoritative. A learned score may rank only candidates already admitted by the deterministic authority; it may not create, repair, legalize, filter, truncate, or reintroduce candidates.

## Separate research targets

- S2-A ranks S1-H-C.v1 finger assignments for static naturalness. Batch01 is diagnostic-only and contributes zero fit rows. No fit-eligible corpus means no real S2-A fit.
- `GUITARSET-OBSERVED-VOICING-MODEL.v2` ranks exact string/fret candidates for a fixed pitch multiset. Its scientific gates are complete, but its retained checkpoint is research-only.
- PR #90 is closed without merge and cannot replace S1-H-C.v1.

## GuitarSet v2 limits

- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

The positive dataset has no fret-20 gold. Scoring a fret-20 candidate demonstrates domain compatibility only; it is not evidence that fret 20 is preferred correctly.

## Closed authority flags

- `new_training_or_refit_authorized=false`;
- `runtime_connection_authorized=false`;
- `production_authorized=false`;
- candidate mutation: false;
- canonical/TAB/writer effect: false;
- live/user data access: false;
- network/telemetry authority: false.

The engine's `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` artifact at `evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json` is repository-fixture-only and remains subordinate to deterministic engine output.

Next human/consequential gate: `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`.

## Numerical evidence safety

`NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED` is sealed in `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json` (byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`). The DEVELOPMENT-only diagnostic records L-BFGS status 0, projected-gradient termination, `n_iter=37`, 39 function/gradient evaluations, sealed gradient infinity norm `0.00008273717518741651 <= 0.0001`, a non-increasing accepted objective trace, and coefficient delta `5.4577231622943145e-11`.

Validation/final access remained false. The historical model was not rewritten; checkpoint replacement, model mutation/refit, runtime connection, production, and fret-20 quality authority remain false.
