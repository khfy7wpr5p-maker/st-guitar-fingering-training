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
2. rule-derived deterministic metadata/targets;
3. blind full-candidate Teacher preference;
4. blind pairwise Teacher preference;
5. independent per-candidate component score;
6. pilot/calibration label;
7. repeat/reliability label;
8. diagnostic-only label;
9. future assignment-level ranking supervision, only if explicitly introduced by a new model-development protocol.

These types may not be silently collapsed into one training target. `EQUAL_OR_UNSURE` is preserved and is never coerced into A/B.

## Protected historical label boundary

Current rules remain:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- historical repeat/reliability labels: not additional training rows;
- S1-F project-label fit: `HARD_CLOSED` until a separately approved newer model-development protocol explicitly replaces that gate.

S1-G v1 remains immutable merged preregistration history. PR #70 was closed as superseded without merge and is not active dataset policy.

## Family isolation

- family identity is the primary leakage boundary;
- train/validation/test families must remain disjoint unless a preregistered nested-development design explicitly defines inner folds;
- event-level random splitting may not divide one source family across train and evaluation sets;
- any future assignment-level rows inherit the family identity of the source musical event.

## Consumed evidence

- Stage 7E: permanently evaluation-only;
- E3-E Teacher-GOLD: permanently consumed untouched evaluation evidence;
- historical development labels: not fresh validation;
- S0-C and S1 repeat labels: reliability-only;
- S1-E pilot/repeat labels: never training;
- S1-G v2 first-pass: diagnostic-only/never-training.

## S1-H-A deterministic candidate records

H-A records rule-derived candidate metadata from the complete authoritative `valid_chord_voicings()` set:

- stable candidate ID;
- deterministic geometry/topology facts;
- class (`PLAUSIBLE`, `BORDERLINE`, `DOMINATED`, `IMPRACTICAL`);
- fixed-order reason codes;
- prune boolean;
- optional compared-candidate ID;
- rule version.

These are deterministic facts, not Teacher-GOLD preference labels.

## S1-H-B deterministic fretting-resource records

For every authoritative H-A candidate, H-B may record:

- inherited stable candidate ID and upstream class;
- H-B class (`UPSTREAM_PRUNED`, `RESOURCE_INFEASIBLE`, `RESOURCE_FEASIBLE`);
- positive fret set;
- deterministic continuous-barre groups;
- blockers by fret;
- `minimum_standard_fingers`;
- canonical resource witness when feasible;
- H-B reason codes;
- rule version.

These fields describe the frozen ordinary four-finger/barre resource model. They are not human preference labels and must not be presented as evidence of comfort or naturalness.

## S1-H-C deterministic assignment records

For every H-B-retained voicing, H-C emits zero or more standard finger-assignment records with:

- source voicing candidate ID;
- stable `assignment_id`;
- exact `(pitch, string, fret, finger)` placements;
- explicit barre metadata `(finger, fret, span_start_string, span_end_string)`;
- H-C rule version.

Contract invariants:

- open strings use finger `0`;
- fretted notes use fingers `1..4`;
- exact pitch/string/fret placement is unchanged;
- different H-B groups use distinct fretting fingers;
- strictly lower-fret groups use lower-numbered fingers than strictly higher-fret groups;
- upstream-pruned voicings receive no assignments;
- every H-B-retained voicing produces at least one assignment or fails closed;
- assignment IDs are stable/deterministic.

An H-C assignment is a **deterministic candidate**, not a positive Teacher label and not proof that it is the best fingering.

## Future learned assignment-ranking rows

No real assignment-ranking training corpus is currently authorized.

A future protocol may create one only after explicitly freezing:

- how a Teacher or other legitimate target source compares/selects H-C assignments;
- exact provenance value(s) eligible for fit;
- family ID propagation;
- handling of ties/unsure;
- whether labels are pairwise, listwise, ordinal, or scalar;
- minimum sample/family support;
- separation of development, reliability, and untouched evaluation roles.

The model target must reference H-C `assignment_id` values and must never redefine physical validity.

## Authority boundary

Teacher judgments and learned predictions never override deterministic physical/feasibility state. A future learned ranker may only choose among S1-H-C assignments supplied for the same event. Output outside that set is an error, not a new candidate.

## Frozen evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots. Their status fields are not rewritten solely because a later PR is merged. Current live status is tracked in the top-level project documentation.
