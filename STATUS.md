# Status

## Live status

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`
`LIVE_DOCUMENTATION_COMPATIBILITY_GOVERNANCE_HARDENED`

Scientific synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).
Compatibility/governance hardening baseline: `5b18e0c6ac44ab3fba575658dd6ac8814cc1f0f8` (PR #121).

These SHA references are provenance anchors, not a claim that this document blob equals either historical commit.

| Track | Current state |
|---|---|
| Deterministic physical and S1-H-C.v1 assignment authority | Active and authoritative |
| MusicXML measure identifier propagation | Compatibility hardened: opaque string identity preserved through H-C and Teacher Correction audit evidence |
| H-C failure evidence retention | Fail-closed upload guard present; audit artifact upload runs on `always()`, missing artifact remains an error |
| Required CI safety gate | Branch-protected `test` aggregates unit/compile + real-source H-C audit + Teacher Correction pilot boundary validation |
| S2-A Teacher naturalness | Machinery complete; no fit-eligible corpus; no real fit |
| PR #67 S1-D legacy draft | Closed without merge; archived, non-authoritative |
| PR #90 S1-H-C.v2 experiment | Closed without merge; non-authoritative |
| GuitarSet v1 | Historical 0..19-domain evidence, frozen |
| `GUITARSET-OBSERVED-VOICING-MODEL.v2` | Development, validation, final, retention, and integration review complete |
| GuitarSet v2 numerical hardening | `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED` |
| Engine controlled-offline v2 evidence | `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` |
| Engine runtime connection | Closed pending human review |
| Production learned selection | Closed |

## Compatibility hardening

The target-free MusicXML parser already preserves the raw measure `number` attribute as `str`. H-C capacity evidence and Teacher Correction audit generation now use the same contract instead of coercing measure identity with `int(...)`. Regression coverage explicitly preserves `A1`, `12A`, `X`, and zero-padded `001`.

The H-C audit command writes its JSON before returning exit status `2` on scientific failure. The workflow upload step therefore runs under `if: always()` so that a failed run remains auditable. The artifact is still mandatory: `if-no-files-found: error` remains enabled, so absence of evidence is fail-closed.

These changes do not alter source reservation, H-C eligibility thresholds, deterministic assignment authority, Teacher-label access, model fitting, untouched-final access, checkpoint retention, or runtime/production authorization.

## Required CI safety gate

The repository's branch protection already requires the `test` check. That check is the aggregate safety gate and includes:

- the full unit-test discovery suite;
- real-source H-C capacity audit execution and PASS/invariant validation;
- Teacher Correction v1 pilot build plus family/quarantine/untouched-final/training-boundary validation;
- compile validation.

The dedicated H-C and Teacher Correction workflows remain artifact-producing supplemental workflows. Required `test` therefore prevents those safety-critical behaviors from becoming optional merge checks. GitHub Actions in required CI are pinned to immutable SHAs, and CI dependency resolution is constrained for repeatability.

## GuitarSet v2 identity and result

- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

Sealed metrics:

| Gate | Ambiguous events | Learned Top-1 | Baseline Top-1 | Learned MRR | Baseline MRR | Additional gate evidence |
|---|---:|---:|---:|---:|---:|---|
| DEVELOPMENT | 7,919 | 0.733523 | 0.498412 | 0.857954 | 0.599848 | 4/4 fold wins; 10/10 deterministic |
| VALIDATION | 1,890 | 0.770370 | 0.621693 | 0.882055 | 0.713156 | MRR bootstrap lower bound 0.0746363 |
| UNTOUCHED_FINAL | 1,816 | 0.692181 | 0.425661 | 0.838217 | 0.600227 | MRR bootstrap lower bound 0.1076984 |

The retained checkpoint is research-only. No post-final refit occurred.

## S2-A state is different

S2-A must not be described as trained merely because GuitarSet v2 is trained. Batch01 remains `DIAGNOSTIC_ONLY_NEVER_TRAINING`, contributes zero fit rows, and no fit-eligible fresh Teacher supervision is available. S1-H-C.v1 remains authoritative for S2-A.

## Cross-repository evidence

The engine's exact-main artifact is:

`evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`

It is bound to engine commit `acdb66e2bb2ad809ab45fc7c2183d84280d61ad7`, not to future runtime behavior.

Current authorization: `new_training_or_refit_authorized=false`, `runtime_connection_authorized=false`, and `production_authorized=false`.

Next human/consequential gate: `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`.

## Numerical evidence closeout

The retained model's DEVELOPMENT-only numerical hardening is sealed at `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json` (byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal evidence SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`).

- L-BFGS status: `0`, success;
- termination: projected gradient norm within `1e-4`;
- `n_iter=37` of 2,000;
- function/gradient evaluations: `39/39`;
- sealed objective: `0.029548918364167603`;
- sealed gradient L2 norm: `0.00012675530517663626`;
- sealed gradient infinity norm: `0.00008273717518741651`;
- accepted objective trace: non-increasing;
- coefficient reconstruction maximum absolute delta: `5.4577231622943145e-11`.

Status: `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`. Validation/final remained unread, and the historical model/checkpoint was not rewritten.
