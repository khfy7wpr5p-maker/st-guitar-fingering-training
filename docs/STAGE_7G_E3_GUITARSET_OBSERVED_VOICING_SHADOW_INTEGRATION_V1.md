# Stage 7G-E3 — GuitarSet Observed-Voicing Shadow Integration v1

## Decision

`SHADOW_INTEGRATION_REVIEW_PASS_OFFLINE_NON_AUTHORITATIVE_SEAM_ONLY`

The retained `GUITARSET-OBSERVED-VOICING-MODEL.v1` checkpoint may be wired to an **offline, non-authoritative shadow seam** for test and future shadow-review purposes. This review does not authorize live shadow execution, runtime connection, or production use.

## Authority boundary

`valid_chord_voicings()` remains the sole authoritative physical candidate generator.

The shadow model:

- receives the complete authoritative candidate set from the deterministic engine;
- may never create, repair, legalize, add, or remove physical placements;
- returns only diagnostic scores/ranking plus optional agreement with an already-selected authoritative candidate;
- has no return path that replaces or mutates the authoritative engine choice;
- requires the exact retained checkpoint and exact checkpoint-retention evidence.

## Frozen model-domain mismatch

The core engine supports frets `0..24`, while the frozen GuitarSet observed-voicing model was preregistered and evaluated on standard tuning with frets `0..19`.

This mismatch is handled fail-closed:

1. the caller must supply the complete exact `valid_chord_voicings()` candidate set;
2. if any authoritative candidate contains fret `20..24`, the event is `SHADOW_NOT_SCORED_MODEL_DOMAIN_INCOMPLETE`;
3. the seam does **not** drop the high-fret candidates, clip frets, or rank only the in-domain subset;
4. non-standard tuning is rejected instead of remapped.

Therefore a shadow score exists only when the entire authoritative candidate set lies inside the frozen model domain.

## Checkpoint identity

- retained model SHA-256: `5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869`
- checkpoint-retention evidence SHA-256: `81ee73897a2e401696137f4ae950354b8c8fdde24b6a6fe2d16b612ae027d722`
- physical authority: `valid_chord_voicings()`
- engine maximum fret: `24`
- model maximum fret: `19`
- tuning: standard guitar `[64, 59, 55, 50, 45, 40]` for strings 1..6

## Still closed

- real/live shadow execution: **false**
- authoritative decision effect: **false**
- checkpoint mutation: **false**
- refit: **false**
- tuning/recalibration: **false**
- validation/final reuse for training: **false**
- runtime connection: **false**
- production: **false**

Unit tests may exercise the seam with synthetic/deterministic candidate sets; that is implementation verification, not project shadow execution.

## Next gate

`SHADOW_EXECUTION_REVIEW`

Before any real project input is sent through the retained checkpoint in shadow mode, that gate must define the allowed input source, logging/evidence schema, privacy/data-retention behavior, determinism checks, failure isolation, comparison metrics, stop conditions, and an explicit guarantee that shadow failures cannot alter authoritative GuitarTab Engine output.
