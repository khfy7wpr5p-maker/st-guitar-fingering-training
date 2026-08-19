# Dataset Contract v1

## Normalized source identity

Each normalized source event records at minimum:

- `family_id` for leakage control;
- exact source-byte digest;
- tuning and explicit pitch mode;
- measure/onset/duration/voice;
- sounding pitches;
- observed string/fret placement when present;
- deterministic physical-validation result.

Observed placement is eligible only when tuning/pitch mode are resolved and every technical placement matches the normalized sounding pitch under the supported physical range.

## Supervision types must remain separate

The repository distinguishes:

1. observed corpus placement;
2. rule-derived synthetic/property targets;
3. blind full-candidate Teacher preference;
4. blind pairwise Teacher preference;
5. independent per-candidate component score;
6. pilot/calibration label;
7. repeat/reliability label;
8. diagnostic-only label.

These types may not be silently collapsed into one training target. `EQUAL_OR_UNSURE` is preserved and is never coerced into A/B.

## Current S1 label boundary

The merged S1-H-A scientific contract supersedes older assumptions that completion of the S1-D-era reliability workflow would automatically make project labels trainable.

Current status:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- S1-F project-label model fit: `HARD_CLOSED`.

S1-G v1 remains immutable merged preregistration history. Open PR #70 is not merged dataset policy.

## S1-F future-training provenance contract

The preparation harness recognizes future supervised provenance only under its exact frozen contract and does not itself authorize real fitting. Pilot, repeat, diagnostic, or manually renamed sources must not be admitted through provenance-string tricks.

A later training protocol must explicitly define the eligible first-pass corpus, minimum sample/family counts, validation policy, and model-retention gate before real project-label fitting can be opened.

## Family isolation

- family identity is the primary leakage boundary;
- train/validation/test families must remain disjoint unless a separately preregistered nested-development design explicitly defines inner folds;
- a source family may not be split event-by-event to manufacture a larger apparent validation set.

## Consumed evidence

- Stage 7E: permanently evaluation-only;
- E3-E Teacher-GOLD: permanently consumed untouched evaluation evidence;
- historical development labels: not fresh validation;
- S0-C and S1 repeat labels: reliability-only;
- S1-E pilot/repeat labels: never training under the current merged contract;
- S1-G v2 first-pass: diagnostic-only/never-training under the current merged contract.

## S1-H-A deterministic candidate records

S1-H-A adds deterministic candidate-analysis facts, not Teacher labels.

A valid plausibility record must be derived from the complete authoritative `valid_chord_voicings()` set for the same pitch set and tuning. Candidate records may contain:

- stable candidate ID;
- deterministic geometry/topology facts;
- class (`PLAUSIBLE`, `BORDERLINE`, `DOMINATED`, `IMPRACTICAL`);
- fixed-order reason codes;
- prune boolean;
- optional compared-candidate ID;
- top-level rule version.

These fields are rule-derived deterministic metadata. They must not be presented as Teacher-GOLD or learned preference targets.

## Authority boundary

Dataset labels, descriptors, Teacher judgments, and learned predictions never override deterministic physical validity. S1-H-A may only classify/prune candidates already inside the complete authoritative valid set, and future learned ranking may only consume candidates retained by the deterministic boundary defined by the active merged protocol.

## Frozen evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots. Their status fields should not be rewritten solely because a later PR was merged. Current live status is tracked in the top-level project documentation.
