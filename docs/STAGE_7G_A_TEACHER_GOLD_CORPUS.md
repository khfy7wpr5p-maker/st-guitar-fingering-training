# Stage 7G-A — Teacher-GOLD Preference Corpus Contract

Status: **PROTOCOL / INTAKE INFRASTRUCTURE — NO MODEL TRAINING**

## Goal

Stage 7G changes the supervision target from observed Guitar Pro behavior to explicit human guitaristic preference.

A `Teacher-GOLD` label means: a human guitar teacher selected one preferred voicing from the complete deterministic set of physically valid string/fret candidates for an ambiguous chord event.

It does **not** mean:

- the voicing happened to appear in an existing Guitar Pro file;
- a synthetic rule preferred the voicing;
- a specialist model predicted the voicing;
- an oracle chose whichever specialist matched the target.

## Annotation boundary

The annotation task contains only:

- source identity and family identity;
- chord pitches;
- six-string tuning;
- the complete candidate set returned by deterministic `valid_chord_voicings()`.

It contains no observed placement, no previous target voicing, no specialist prediction, and no router result.

The teacher chooses a candidate while blind to specialist predictions. Only after that choice is fixed are the four stateless specialist Top-1 predictions attached as diagnostic/sampling metadata:

- `open_low`
- `compact`
- `mid_position`
- `high_position`

`common_tone` is excluded from Stage 7G v1 because its rollout path was rejected in Stage 7D-B-R1.

## Fail-closed validity rules

A record is accepted only when:

1. its source SHA-256, source origin, family ID, event ID and pseudonymous annotator ID are present;
2. the event has at least two pitches and at least two deterministic physical voicing candidates;
3. the teacher-preferred voicing belongs to that deterministic candidate set;
4. all four stateless specialist predictions belong to the same deterministic candidate set;
5. annotation is declared blind to specialist predictions;
6. label semantics are exactly `TEACHER_GOLD`;
7. quarantined Stage 7E source hashes and source origins are absent;
8. event IDs are unique and one source hash cannot be mapped to multiple families.

Specialist disagreement is derived from the stored Top-1 predictions. It is not a manually editable label.

## Stage 7G corpus gate

Before any Teacher-GOLD training experiment, the corpus must contain at least:

- **30 independent families**;
- **600 Teacher-GOLD ambiguous events**;
- **100 specialist-disagreement events**.

Validation must remain family-isolated.

The Stage 7E untouched final corpus is permanently evaluation-only. Its sources, hashes, targets and labels may not be reused for Stage 7G training, tuning, calibration, feature selection or hyperparameter selection.

## Sampling priorities

Prefer annotation tasks that are informative rather than merely numerous:

1. `open_low` versus `compact` disagreement;
2. any stateless-specialist disagreement;
3. high candidate count / large position-choice space;
4. diverse chord sizes, pitch spans and registers;
5. candidate sets extending above synthetic fret 12, without assuming high fret is preferred.

## Safety state

- model fitting: **not started**
- Teacher-GOLD corpus committed to Git: **no**
- checkpoint retained: **no**
- production integration: **no**
- sequence-context training: **deferred**

This stage first establishes trustworthy human-label intake. Training begins only after a later corpus-readiness gate passes the preregistered minimums and leakage checks.
