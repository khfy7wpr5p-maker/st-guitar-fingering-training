# Safety

## Physical-authority invariants

- Parse untrusted XML with safe parsers; do not fetch network DTD/schema resources.
- Reject unsupported string/fret mappings, missing tuning, malformed durations, and impossible physical placements.
- `valid_chord_voicings()` remains the authoritative physical candidate generator.
- Deterministic downstream layers may only remove or expand metadata/assignments for candidates from that set; they may never manufacture or legalize a new physical placement.
- Learned systems may only rank final deterministic assignment IDs supplied to them.

## S1-H-A plausibility safety

- complete authoritative candidate set required;
- non-authoritative candidates, duplicates, and incomplete subsets fail closed;
- raw physical set preserved for audit;
- v1 hard prune limited to `H001_MIN_FINGER_PROXY_GE_6`;
- five distinct positive frets retained as `BORDERLINE` at H-A;
- dominance remains diagnostic-only at H-A;
- tone/style/resonance/preference are not physical hard-prune rules.

## S1-H-B fretting-resource safety

S1-H-B is an ordinary four-fretting-finger resource model, not full biomechanics.

- it recomputes the complete H-A state;
- it may only further prune H-A-retained candidates;
- open strings consume no fretting finger;
- same-fret notes may share one continuous barre only under the frozen crossing rules;
- required open strings and lower positive frets block a higher-fret barre crossing;
- unused strings and higher-fret overrides are passable;
- v1 hard prune is limited to `H101_MIN_STANDARD_FINGERS_GE_5`;
- H-A-pruned candidates remain audited and may never be reintroduced;
- zero surviving candidates is explicit as `NO_STANDARD_FINGERING_CANDIDATE`.

H-B must not be described as proving comfort, reach, naturalness, wrist safety, or impossibility under extended techniques such as thumb-over or two-hand tapping.

## S1-H-C assignment-generation safety

S1-H-C enumerates standard assignments but does not choose a preferred one.

- only H-B-retained voicings receive assignments;
- open strings use finger `0`;
- fretted groups use distinct fingers `1..4`;
- notes in one H-B group share a finger;
- strictly increasing frets require strictly increasing finger numbers;
- exact pitch/string/fret placement is preserved;
- barre metadata must match the upstream group span;
- assignment identities are stable and deterministic;
- a retained voicing with zero assignments is a fail-closed invariant error;
- upstream-pruned voicings receive zero assignments.

A future learned ranker must not output an assignment ID that was not supplied by S1-H-C for that event.

## Training and label boundaries

No user upload, teacher correction, annotation, pilot answer, or repeat answer is automatic training consent.

Current protected label rules:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- historical repeat/reliability labels: not extra training rows;
- S1-F real project-label fit remains `HARD_CLOSED` until superseded by an explicitly approved newer model-development protocol.

`EQUAL_OR_UNSURE` responses remain explicit and must not be silently coerced into binary targets.

## Consumed evidence

- Stage 7E is permanently evaluation-only.
- E3-E Teacher-GOLD is permanently consumed untouched evaluation evidence.
- historical development results are not fresh validation.
- consumed untouched or reliability corpora may not be recycled for model selection, threshold tuning, hard-error mining, or a new validation claim.

## Real model-development gate

The repository is now complete through deterministic S1-H-C and has reached the real learned-model boundary.

Before any fit/tuning begins, a separately approved protocol must freeze:

- prediction target over S1-H-C assignments;
- eligible and forbidden label provenance;
- feature contract;
- family-isolated split/evaluation policy;
- baselines and acceptance metrics;
- model/hyperparameter selection policy;
- tie/unsure handling;
- output restriction to supplied assignment IDs;
- checkpoint-retention criteria fixed before the deciding evaluation.

Model-development approval does **not** automatically authorize checkpoint retention, shadow integration, or production.

## Promotion gates

These remain separately closed even after a future model fit:

- retained/promoted checkpoint;
- learned arbiter/refiner activation beyond its approved experiment;
- GuitarTab Engine shadow integration;
- production integration.

## Historical evidence files

Frozen preregistration/evidence JSON files are immutable historical snapshots. Do not rewrite them solely to match a later merge. Live status belongs in the top-level documentation.

## Development-control rule

Pre-model deterministic technical development through S1-H-C was authorized and completed without repeated approval interruptions. The next action that opens real learned-model development is a separate explicit gate. Destructive history operations, checkpoint promotion, and shadow/production integration remain separately consequential gates.
