# Stage 7G-E4 — GuitarSet Observed Voicing Model v2 Shadow Integration Review

## Decision

`SHADOW_INTEGRATION_REVIEW_PASS_OFFLINE_NON_AUTHORITATIVE_V2_ADAPTER_ELIGIBLE_RUNTIME_CLOSED`

The retained `GUITARSET-OBSERVED-VOICING-MODEL.v2` checkpoint may be transported into a **controlled offline Node shadow adapter** for exact cross-language parity work only.

This review does not authorize live execution, user-input execution, optimizer influence, CanonicalTabResult influence, TAB output influence, runtime connection, or production use.

## Retained scientific identity

- model artifact SHA-256: `7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314`
- checkpoint-retention evidence SHA-256: `53f4ea1491b37dfc8360278f852927229f7a3ba6f10a6f8c9a3fb8fb8df80c71`
- feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`
- protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`
- candidate domain: `0..20`
- observed positive-gold domain: `0..19`
- fret-20 positive gold: `0`
- fret-20 quality authority: **false**

## Fresh cross-repo target

The reviewed engine target is:

- repository: `khfy7wpr5p-maker/musicxml-to-guitar-tab-engine`
- exact reviewed main: `ed36e9243714f32b57159dd97eeeb20d66231a7b`
- physical authority: `GuitarVoicingCandidateModel 1.0.0`
- candidate policy: `STANDARD_SIX_STRING_DISTINCT_STRING_1.0`
- candidate fret domain: `0..20`
- aggregate candidate limit: `10,000`
- candidate module blob: `146de2c2591f9ac3183552237f40401e632412d5`
- tuning module blob: `06b1f76b6815ddb87cd39ac69e6ff03b018cc377`
- standard tuning strings 1..6: `[64, 59, 55, 50, 45, 40]`

Unlike retained model v1, v2 has an **exact candidate fret-domain match** with this engine target. Therefore fret-20 candidates do not require candidate clipping or whole-group abstention merely because of model-domain mismatch.

This does **not** create a fret-20 pedagogical-quality claim. The v2 model may score fret-20 candidates because `0..20` was preregistered as its candidate domain throughout DEVELOPMENT/VALIDATION/UNTOUCHED_FINAL evaluation, while the absence of positive fret-20 observed gold remains explicit.

## Mandatory adapter boundary

The next adapter must:

- consume only the exact complete PA-7 `GuitarVoicingCandidateModel` candidate group;
- preserve every candidate and every `[targetMidi, string, fret]` placement;
- never add, remove, filter, truncate, mutate, repair, or synthesize candidates;
- support standard tuning only;
- require exact model, protocol, and feature-schema identities;
- parse Python hexadecimal float transport explicitly and deterministically;
- reproduce Python feature vectors, scores, and ranking in Node before any controlled offline execution;
- return diagnostic shadow information only.

Still forbidden:

- optimizer authority: **false**
- authoritative voicing-selection effect: **false**
- canonical result effect: **false**
- TAB output effect: **false**
- checkpoint mutation/refit/tuning: **false**
- live/user input: **false**
- runtime connection: **false**
- production: **false**

## Next gate

`OFFLINE_NODE_SHADOW_ADAPTER_V2_IMPLEMENTATION_AND_CROSS_LANGUAGE_PARITY`

Only after exact Node/Python parity and isolation tests PASS may a separate controlled fixture-only offline shadow execution review be considered. Runtime shadow connection remains a later, separate consequential gate.
