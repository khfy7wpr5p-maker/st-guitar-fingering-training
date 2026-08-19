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
9. S2-A assignment-level blind pairwise static-naturalness supervision.

These types may not be silently collapsed into one training target. `EQUAL_OR_UNSURE` is preserved and is never coerced into A/B.

## Protected historical label boundary

Current rules remain:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- historical repeat/reliability labels: not additional training rows;
- S1-F project-label fit remains `HARD_CLOSED`;
- S2-A preregistration does not retroactively authorize any S1 label for fit.

S1-G v1 remains immutable merged preregistration history. PR #70 was closed as superseded without merge and is not active dataset policy.

## Family isolation

- family identity is the primary leakage boundary;
- train/validation/test families must remain disjoint unless a preregistered nested-development design explicitly defines inner folds;
- event-level random splitting may not divide one source family across train and evaluation sets;
- assignment-level S2-A rows inherit the family identity of the source musical event;
- mirrored pair-difference rows remain in the same family/fold as the original human judgment;
- S2-A untouched-final families may never enter S2-A development or fit.

## Consumed evidence

- Stage 7E: permanently evaluation-only;
- E3-E Teacher-GOLD: permanently consumed untouched evaluation evidence;
- historical development labels: not fresh validation;
- S0-C and S1 repeat labels: reliability-only;
- S1-E pilot/repeat labels: never training;
- S1-G v2 first-pass: diagnostic-only/never-training.

Consumed historical labels and final-test evidence may not be reclassified as S2-A supervision.

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

## S2-A assignment-ranking supervision preregistration

S2-A v1 introduces one new target only:

`STATIC_STANDARD_FINGERING_NATURALNESS`

It is a blind A/B comparison between two H-C assignments of the same event under an isolated, ordinary left-hand-technique prompt. Previous/next context, tempo, style, right-hand pattern, tone-color goals and extended technique are outside the target.

Exact provenance roles are frozen:

- `S2A_STATIC_NATURALNESS_FIRST_PASS` — only decisive A/B rows are potentially fit-eligible after all S2-A gates pass;
- `S2A_STATIC_NATURALNESS_REPEAT` — reliability-only, never training/tuning/model selection;
- `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL` — final evaluation only, never training/tuning/model selection.

`EQUAL_OR_UNSURE` is retained as ambiguity evidence and is never forced to A/B.

Every S2-A human row must reference two stable H-C `assignment_id` values from the same exact event and H-C output. A row referencing an absent/out-of-set assignment is invalid.

Pair construction must be label-blind and is allowed only after complete H-C enumeration. Pair metadata may distinguish `FINGER_ONLY` and `MIXED` pairs and `NEAR/MID/FAR` feature-distance strata, but these metadata are audit/sampling facts, not Teacher labels.

### Minimum S2-A development evidence before fit can even be considered

- >=40 development families;
- >=200 eligible events;
- >=600 decisive first-pass pairs;
- >=150 decisive `FINGER_ONLY` pairs;
- >=150 decisive `MIXED` pairs;
- >=100 decisive pairs in each distance stratum;
- reliability gate PASS.

### Reliability role

At least `max(120, 20% of development tasks)` must be repeated after 24–72 hours, with exactly 50% A/B presentation reversal. Repeat rows remain non-trainable even if perfectly consistent.

### Untouched final role

S2-A final evaluation requires >=20 family-disjoint untouched families and >=200 decisive final pairs. These labels may not be inspected before the frozen all-development model, comparator and evaluation code are sealed.

## S2-A feature/data separation

The S2-A model feature vector is deterministic and assignment-derived only. It may not contain:

- Teacher response or response history;
- annotator identity;
- family/source identity;
- observed source fingering;
- previous/next event information;
- historical specialist prediction;
- model score;
- any consumed final label.

The frozen S2-A v1 feature list and exact formulas live in `docs/STAGE_7G_E3_S2A_LEARNED_FINGERING_RANKER_PREREGISTRATION.md` and its frozen evidence JSON.

## S2-A fit state

The S2-A protocol design is preregistered, but **real fitting remains closed** until the implementation, corpus minimums, reliability evidence, and execution gate are separately verified.

A future execution stage may open fitting only for exact `S2A_STATIC_NATURALNESS_FIRST_PASS` decisive rows under the merged S2-A protocol. It may not open S1-F historical project labels by side effect.

## Authority boundary

Teacher judgments and learned predictions never override deterministic physical/feasibility state. S2-A may only score/rank S1-H-C assignments supplied for the same event. Output outside that exact set is an error, not a new candidate.

Checkpoint retention, GuitarTab Engine shadow integration, and production integration remain separate later gates even if S2-A evaluation passes.

## Frozen evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots. Their status fields are not rewritten solely because a later PR is merged. Current live status is tracked in the top-level project documentation.
