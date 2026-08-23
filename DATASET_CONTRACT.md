# Dataset contract

## Live contract view

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

This file summarizes the current live data boundary. Versioned contracts and sealed evidence under `docs/` and `evidence/` remain the exact historical authority.

## GuitarSet observed voicing

Approved observations come from the sealed GuitarSet `*_comp.jams` archive and preserve observed string/fret placement. They do not provide finger-number, barre, S2-A Teacher preference, transition, performer-anatomy, or production-runtime gold.

Frozen split roles:

- DEVELOPMENT performers: `00, 01, 04, 05`;
- VALIDATION performer: `03`;
- UNTOUCHED_FINAL performer: `02`;
- performer, recording, note, and voicing identity overlap across roles: zero;
- backing-track and style identities are shared, so unseen-repertoire and unseen-style claims are forbidden.

For `GUITARSET-OBSERVED-VOICING-MODEL.v2`:

- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- candidate construction preserves the exact MIDI pitch multiset and deterministic standard-tuning physical validity;
- single-candidate events do not enter ranking fit metrics;
- candidate generation is independent of labels and model scores.

V2 identity:

- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

Development, validation, untouched-final, retention, integration-review, and DEVELOPMENT-only numerical-hardening evidence is sealed. Numerical status is `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`; artifact `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json`, byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`. It records `n_iter=37`, optimizer status 0, 39 function/gradient evaluations, and projected-gradient stationarity without reading validation/final. Validation and final labels remain excluded from training, selection, and post-final tuning. `new_training_or_refit_authorized=false`.

## S2-A Teacher data

S2-A is a separate target over S1-H-C.v1 assignment IDs. Batch01 is `DIAGNOSTIC_ONLY_NEVER_TRAINING` because its source-family identities had already participated in earlier development. Its effective fit-row count is zero. No fit-eligible fresh Teacher corpus is currently available, so no real S2-A fit has occurred.

PR #90 is closed without merge and does not change S1-H-C.v1 or retroactively relabel S2-A evidence.

## Cross-repository and privacy boundary

The engine sealed `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` at `evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`. That artifact contains bounded hashes/diagnostics, not raw GuitarSet labels or user files.

`runtime_connection_authorized=false` and `production_authorized=false`.

Next human/consequential gate: `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`. Historical data/evidence remains immutable.
