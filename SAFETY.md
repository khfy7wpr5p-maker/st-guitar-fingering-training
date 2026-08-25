# Safety and scientific authority

## Live safety statement

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`
`LIVE_DOCUMENTATION_COMPATIBILITY_GOVERNANCE_HARDENED`

Scientific synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).
Compatibility/governance hardening baseline: `5b18e0c6ac44ab3fba575658dd6ac8814cc1f0f8` (PR #121).

These SHA references are provenance anchors, not a claim that this document blob equals either historical commit.

Deterministic physical validity is authoritative. A learned score may rank only candidates already admitted by the deterministic authority; it may not create, repair, legalize, filter, truncate, or reintroduce candidates.

## Source identity integrity

MusicXML measure identifiers are opaque source identity fields. They must remain exact strings through target-free parsing, H-C capacity evidence, Teacher task identity, and Teacher Correction audit output. Numeric coercion is forbidden because valid MusicXML identifiers may be non-numeric or formatting-sensitive, including `A1`, `12A`, `X`, and `001`.

A component may derive a temporary numeric ordering hint from an entirely numeric identifier, but that hint must never replace or normalize the stored identifier.

## Failure evidence retention

Scientific FAIL evidence must remain inspectable. `run_s2a_hc_capacity_audit.py` writes the audit JSON before returning exit status `2`; the GitHub Actions artifact upload therefore runs with `if: always()` so the evidence survives a failed audit step or a later assertion failure.

This does not soften the gate. `if-no-files-found: error` remains active, so a missing audit artifact is still a workflow failure. Evidence retention must never convert FAIL into PASS or authorize a subsequent scientific stage.

## Required CI safety boundary

The branch-protected `test` check is the required aggregate merge gate. It must execute the ordinary unit/compile suite plus the real-source H-C capacity audit and Teacher Correction v1 pilot boundary validation. Dedicated artifact workflows remain supplemental; a safety-critical behavior may not become optional merely because its standalone workflow name is not listed separately in branch protection.

Required CI uses immutable commit SHAs for GitHub Actions and a repository CI constraints file for Python dependency resolution. These controls reduce supply-chain drift and improve reproducibility; they grant no scientific, model, runtime, or production authority.

## Separate research targets

- S2-A ranks S1-H-C.v1 finger assignments for static naturalness. Batch01 is diagnostic-only and contributes zero fit rows. No fit-eligible corpus means no real S2-A fit.
- `GUITARSET-OBSERVED-VOICING-MODEL.v2` ranks exact string/fret candidates for a fixed pitch multiset. Its scientific gates are complete, but its retained checkpoint is research-only.
- PR #90 is closed without merge and cannot replace S1-H-C.v1.
- PR #67 is closed without merge and archived as non-authoritative legacy work. Any future reuse requires a fresh branch from current `main`, architecture/contract review, exact-head CI, and separate approval.

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
