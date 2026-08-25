# Roadmap

## Live continuation map

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

## Completed and sealed

- deterministic physical candidate generation and S1-H-C.v1 assignment authority;
- MusicXML measure identity compatibility hardening: opaque string identifiers are preserved through H-C capacity and Teacher Correction audit evidence, with regression coverage for non-numeric and zero-padded values;
- H-C failure-evidence retention: the audit artifact upload runs under `if: always()` while missing evidence remains fail-closed through `if-no-files-found: error`;
- S2-A feature, blind-task, pairwise ranker, development-CV, and final-evaluation machinery;
- GuitarSet ingestion, performer-isolated split, v1 research history, and separate v2 preregistration;
- `GUITARSET-OBSERVED-VOICING-MODEL.v2` DEVELOPMENT, one-shot VALIDATION, model seal, one-shot UNTOUCHED_FINAL, checkpoint-retention review, and shadow-integration review;
- `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`: DEVELOPMENT-only projected-gradient/termination evidence, `n_iter=37`, 39 function/gradient evaluations, and immutable artifact `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json` (byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`);
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
2. A future S2-A fit only after a genuinely fresh, fit-eligible Teacher corpus passes the frozen evidence gate.
3. Separate approval for any authoritative selector influence or production activation.

PR #90 is closed without merge; S1-H-C.v1 remains authoritative. It is not a continuation gate.

PR #67 is a legacy draft based on an older architecture snapshot. It is not a continuation gate and must not be merged without a fresh rebase onto current `main`, contract review, and exact-head CI under a separately approved scope.

Current authorization: `new_training_or_refit_authorized=false`, `runtime_connection_authorized=false`, and `production_authorized=false`.

The engine artifact path is `evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`. It is a bounded repository-fixture diagnostic, not a production milestone.
