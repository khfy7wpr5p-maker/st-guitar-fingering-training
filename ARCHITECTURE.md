# Architecture

## Live architecture view

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

The architecture separates deterministic candidate authority from two independent learned ranking paths.

```text
source score / observed event
  -> deterministic normalization and physical validation
  -> valid_chord_voicings()                 [authoritative candidates]
       -> S1-H-A/B/C.v1                     [authoritative assignments]
            -> S2-A Teacher ranker          [no eligible real fit]
       -> GuitarSet v2 28D ranker           [sealed offline research]
            -> engine controlled-offline adapter evidence
            -> runtime connection           [closed]
```

## Deterministic authority

`valid_chord_voicings()` is the sole authoritative generator of physically exact pitch/string/fret candidates. S1-H-A/B/C.v1 produces the standard left-hand assignment set used by S2-A. PR #90's S1-H-C.v2 experiment is closed without merge and is not part of the live authority chain.

Learned code cannot create, repair, legalize, filter, truncate, or reintroduce a candidate. It cannot change physical validity, canonical output, TAB output, or writer behavior.

## S2-A path

S2-A targets `STATIC_STANDARD_FINGERING_NATURALNESS` over exact S1-H-C.v1 assignment IDs. Its 30D target-blind feature contract and fail-closed pairwise ranking/evaluation code exist. Batch01 is diagnostic-only and contributes zero fit rows; a fit-eligible fresh Teacher corpus is unavailable. Consequently no real S2-A model fit, untouched-final opening, or checkpoint exists.

## GuitarSet v2 path

`GUITARSET-OBSERVED-VOICING-MODEL.v2` targets `OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET` and ranks only exact physical candidates.

- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- features: frozen 28D static pitch/string/fret geometry;
- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

The v2 scientific sequence is complete: preregistration -> DEVELOPMENT -> one-shot VALIDATION -> sealed model -> one-shot UNTOUCHED_FINAL -> checkpoint-retention review -> cross-repository shadow-integration review -> DEVELOPMENT-only numerical evidence hardening. There was no post-final refit.

Numerical evidence status: `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`. Artifact `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json`, byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`. The exact DEVELOPMENT reconstruction records L-BFGS success/status 0, `n_iter=37`, 39 function/gradient evaluations, projected-gradient termination, sealed gradient infinity norm `0.00008273717518741651 <= 0.0001`, and a non-increasing accepted objective trace. The historical checkpoint remains byte-identical.

## Cross-repository boundary

The engine sealed `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` against exact engine commit `acdb66e2bb2ad809ab45fc7c2183d84280d61ad7` at:

`evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`

That artifact belongs to the engine repository. It demonstrates bounded fixture-only adapter execution and candidate preservation, not normal-runtime integration.

Current gates remain fail-closed: `new_training_or_refit_authorized=false`, `runtime_connection_authorized=false`, and `production_authorized=false`.

Next human/consequential gate: `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`.
