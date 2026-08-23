# Status

## Live status

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

Documentation synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).

| Track | Current state |
|---|---|
| Deterministic physical and S1-H-C.v1 assignment authority | Active and authoritative |
| S2-A Teacher naturalness | Machinery complete; no fit-eligible corpus; no real fit |
| PR #90 S1-H-C.v2 experiment | Closed without merge; non-authoritative |
| GuitarSet v1 | Historical 0..19-domain evidence, frozen |
| `GUITARSET-OBSERVED-VOICING-MODEL.v2` | Development, validation, final, retention, and integration review complete |
| Engine controlled-offline v2 evidence | `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` |
| Engine runtime connection | Closed pending human review |
| Production learned selection | Closed |

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

## Residual evidence limitation

The retained model records `n_iter=37`, finite coefficients, deterministic reproduction, and successful preregistered metric gates. The sealed historical artifacts do not contain a gradient norm or an independent optimizer termination certificate. This status therefore does not upgrade iteration count into numerical-convergence proof. Closing that scientific hardening item requires a separately authorized controlled reconstruction and a new supplemental evidence version; historical artifacts must not be rewritten.
