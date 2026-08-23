# Roadmap

## Live continuation map

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

## Completed and sealed

- deterministic physical candidate generation and S1-H-C.v1 assignment authority;
- S2-A feature, blind-task, pairwise ranker, development-CV, and final-evaluation machinery;
- GuitarSet ingestion, performer-isolated split, v1 research history, and separate v2 preregistration;
- `GUITARSET-OBSERVED-VOICING-MODEL.v2` DEVELOPMENT, one-shot VALIDATION, model seal, one-shot UNTOUCHED_FINAL, checkpoint-retention review, and shadow-integration review;
- engine-side `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` for exact engine commit `acdb66e2bb2ad809ab45fc7c2183d84280d61ad7`.

V2 identity remains fixed:

- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

## Open gates

1. `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`: human/safety review before any normal-runtime, user-file, or consequential shadow connection.
2. Optional numerical-convergence hardening: controlled reconstruction producing a new supplemental artifact with explicit optimizer termination evidence; do not rewrite the historical v2 seal.
3. A future S2-A fit only after a genuinely fresh, fit-eligible Teacher corpus passes the frozen evidence gate.
4. Separate approval for any authoritative selector influence or production activation.

PR #90 is closed without merge; S1-H-C.v1 remains authoritative. It is not a continuation gate.

Current authorization: `new_training_or_refit_authorized=false`, `runtime_connection_authorized=false`, and `production_authorized=false`.

The engine artifact path is `evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`. It is a bounded repository-fixture diagnostic, not a production milestone.
