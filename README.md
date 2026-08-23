# st-guitar-fingering-training

Training, evaluation, and deterministic guitar-fingering research for polyphony, voicing, string/fret selection, and learned guitaristic ranking.

## Live repository position

`LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE`

This live view was reconciled against source commit `929264a1778b061ff21464da41ecacbcd952a3cd` (merged PR #115). Historical, versioned evidence documents remain authoritative for the stage at which they were sealed.

The repository has two deliberately separate learned-research paths:

1. **S2-A static fingering naturalness** ranks exact S1-H-C.v1 assignment IDs from blind Teacher supervision. The executable ranker, development CV, and final-evaluation machinery exist, but no fit-eligible fresh Teacher corpus has passed the frozen admission gate. Batch01 is `DIAGNOSTIC_ONLY_NEVER_TRAINING` and contributes zero fit rows. No real S2-A fit has been executed.
2. **GuitarSet observed voicing** ranks physically exact string/fret realizations for a fixed MIDI pitch multiset. Historical v1 used candidate frets 0..19. Separately preregistered `GUITARSET-OBSERVED-VOICING-MODEL.v2` uses candidate domain: 0..20 and completed DEVELOPMENT, one-shot VALIDATION, one-shot UNTOUCHED_FINAL, checkpoint-retention review, and shadow-integration review.

PR #90 is closed without merge. Its S1-H-C.v2 same-fret experiment is not authoritative; S1-H-C.v1 remains the assignment authority consumed by S2-A.

## Non-negotiable authority boundary

Physical validity remains deterministic and authoritative. Learned systems may rank only candidates already emitted by the deterministic boundary; they may never create, repair, legalize, filter, truncate, or reintroduce a candidate.

Current v2 facts:

- target: `OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`;
- candidate domain: 0..20;
- observed positive-gold domain: 0..19;
- `fret20QualityAuthority=false`;
- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`;
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`;
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`;
- shadow-integration review SHA-256: `f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140`.

The retained checkpoint is research-only. `new_training_or_refit_authorized=false`, `runtime_connection_authorized=false`, and `production_authorized=false`.

Numerical status: `NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED`. The DEVELOPMENT-only supplemental artifact is `evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json` (byte SHA-256 `30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670`, internal evidence SHA-256 `0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e`). It records L-BFGS status 0, projected-gradient convergence, `n_iter=37`, 39 function/gradient evaluations, sealed gradient infinity norm `0.00008273717518741651 <= 0.0001`, a non-increasing accepted objective trace, and coefficient reconstruction delta `5.4577231622943145e-11` without rewriting the model.

## Sealed GuitarSet v2 results

- DEVELOPMENT: 7,919 ambiguous events and 342,904 symmetric pair rows; learned Top-1 `0.733522626` vs baseline `0.498412364`; learned MRR `0.857954420` vs baseline `0.599848430`; 4/4 performer-fold wins; 10/10 deterministic reproduction.
- VALIDATION: 1,890 ambiguous events; Top-1 delta `+0.148677`; MRR delta `+0.168898`; recording-block bootstrap MRR-delta lower bound `0.0746363`.
- UNTOUCHED_FINAL: 1,816 ambiguous events; Top-1 delta `+0.266520`; MRR delta `+0.237991`; recording-block bootstrap MRR-delta lower bound `0.1076984`.

These are offline research results for the preregistered split. They do not establish production behavior, live-user performance, unseen-repertoire performance, or fret-20 positive quality.

## Cross-repository state

The GuitarTab Engine has now sealed `GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE` for exact engine commit `acdb66e2bb2ad809ab45fc7c2183d84280d61ad7`. Its immutable artifact is:

`evidence/offline-shadow/exact-main/acdb66e2bb2ad809ab45fc7c2183d84280d61ad7/controlled-offline-shadow-evidence.v2.json`

That engine evidence records repository-fixture-only diagnostic execution. It grants no authority back to this training repository and does not authorize runtime selection.

Next human/consequential gate: `ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW`. Numerical evidence is now supplemental and complete for the frozen DEVELOPMENT surface; it grants no runtime or production authority.

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, and `DATASET_CONTRACT.md` for the synchronized live view. Historical stage records under `docs/` and `evidence/` remain immutable evidence.

## Licensing

First-party software and first-party model rights identified by this repository
are available under the PolyForm Noncommercial License 1.0.0. Commercial use
requires a separate signed agreement; see
[`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md). Dataset provenance,
commercial-training exclusions, model authority, third-party notices, and
contributor terms are documented in [`DATASET-LICENSES.md`](DATASET-LICENSES.md),
[`MODEL-LICENSE.md`](MODEL-LICENSE.md), and [`CONTRIBUTING.md`](CONTRIBUTING.md).
