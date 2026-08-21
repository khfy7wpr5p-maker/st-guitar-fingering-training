# Stage 7G-E3 — GuitarSet Cross-Repo Shadow Compatibility v1

## Purpose

This gate corrects the runtime-target assumptions of the earlier offline training-repository shadow seam without rewriting its historical evidence.

The retained model remains exactly `GUITARSET-OBSERVED-VOICING-MODEL.v1` with artifact SHA-256:

`5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869`

The real target runtime is `khfy7wpr5p-maker/musicxml-to-guitar-tab-engine` at the reviewed main SHA:

`72a128082b2c43603e7808c76ba6744e4e92160c`

No runtime connection is made by this gate.

## Fresh-read correction to PR #102 assumptions

PR #102 remains valid as an offline, non-authoritative seam inside the training repository. It is not rewritten.

For the actual GuitarTab Engine, two runtime-target assumptions differ:

1. The polyphonic physical voicing seam is internal `GuitarVoicingCandidateModel 1.0.0` (`STANDARD_SIX_STRING_DISTINCT_STRING_1.0`), not the training-repository `valid_chord_voicings()` helper.
2. The runtime PA-7 standard configuration uses frets `0..20`; the retained learned model was preregistered and trained only on `0..19`.

Therefore fret 20 cannot be silently removed to make a runtime candidate group fit the model domain.

## Compatible semantics

The reviewed runtime PA-7 candidate model and the retained model agree on the properties needed for an offline adapter:

- standard six-string tuning with string 1 = E4 through string 6 = E2;
- exact target MIDI preservation;
- one note per occupied string;
- distinct-string simultaneous voicing assignments;
- complete candidate groups are available before any learned ranking;
- candidate IDs and source event IDs are not model features.

A runtime candidate is canonically projected for the learned scorer as sorted `[targetMidi, string, fret]` rows. This projection must preserve duplicate pitches as a multiset and may not alter the PA-7 candidate set.

## Fret-domain mismatch policy

The runtime can emit fret 20 while the model domain ends at fret 19.

Mandatory policy:

`IF_ANY_CANDIDATE_HAS_FRET_GT_19_THEN_NO_SCORE_NO_TRUNCATION`

The entire group is reported as unsupported for the shadow model. No candidate may be clipped, filtered, replaced or regenerated.

## Existing LR-S0 shadow module

The engine already has a generic internal `shadowRanking.js` path, but it is not the correct scorer for this checkpoint. Its seven-dimensional pedagogical feature contract and lower-is-better score direction do not match the frozen GuitarSet 28D static voicing geometry model, whose score direction is higher-is-better.

The GuitarSet checkpoint therefore requires a separate internal adapter rather than coercing the checkpoint into LR-S0.

## Cross-language transport requirement

The retained checkpoint is a JSON linear scorer:

`dot((features - mean) / scale, coef)`

Its 28 means, scales and coefficients are serialized as Python hexadecimal floating-point strings. JavaScript does not natively parse Python/C99 hexadecimal floats with `p` exponents. Any Node adapter must use a strict explicit parser and prove score/rank parity against Python golden fixtures before shadow execution can be reviewed.

## Authority boundary

This gate authorizes only implementation and testing of an offline Node adapter.

It does **not** authorize:

- live/project shadow execution;
- optimizer influence;
- TAB-output influence;
- checkpoint mutation;
- model refit or tuning;
- validation/final reuse for training;
- runtime connection;
- production use.

Next gate:

`OFFLINE_NODE_SHADOW_ADAPTER_IMPLEMENTATION_AND_CROSS_LANGUAGE_PARITY`
