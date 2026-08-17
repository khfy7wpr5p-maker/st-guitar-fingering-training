# Stage 7G-E3-S1-D — Blind Repeat Reliability Scoring

## Scope

S1-D scores the already sealed 48-task blind repeat against the already completed 120-task S1 first pass. It is a reliability measurement stage only.

This stage does **not** select new tasks, change A/B orientations, change rubric definitions, tune thresholds, fit weights, train a model, retain a checkpoint, or authorize GuitarTab Engine integration.

## Frozen identities

The scorer accepts only the S1-B sealed manifests:

- first-pass manifest SHA-256: `4a5dd305bd9110eec115cd901ba43a154c6724dca13f54ff634a41f07dd286a1`
- repeat manifest SHA-256: `7a4fe1ef61df3a991984b00e35050cb0c5faff55b09bc6d8f7578157c70fae17`
- first-pass task count: 120
- repeat task count: 48
- paired option ratings per component: 96

The hidden first/repeat audits are used only after repeat annotation to align independently reblinded A/B options back to the same source option. They are not Teacher-facing material.

## Minimum-delay gate

The exported first-pass JSON records `completed_at`; the repeat export records `started_at`.

The scorer refuses to score the repeat unless:

`repeat.started_at - first_pass.completed_at >= 24 hours`

The timestamp comparison requires timezone-aware ISO-8601 values. This prevents a repeat that starts too early from being accidentally treated as valid S1-D evidence.

## Frozen primary component gate

Every component is evaluated over 96 aligned option-score pairs:

- `POSITION_COMFORT`
- `STRING_DISTRIBUTION`
- `FINGER_SPREAD`
- `OPEN_STRING_UTILITY`

Every component must satisfy all of the following:

- quadratic-weighted Cohen kappa >= 0.90
- exact 1–5 score agreement >= 0.80
- within ±1 point agreement >= 0.98
- mean absolute score difference <= 0.35
- at least 3 distinct first-pass scores on the repeat subset
- no single first-pass score > 85% of that component's 96 ratings

Undefined quadratic-weighted kappa is a fail/review condition.

All four components must pass. A pass opens only a separate component-model training protocol design; it does not authorize training.

## Frozen secondary overall-preference gate

The final A/B/equal-or-unsure preference is decoded through the hidden A/B source-option mapping before comparison.

Frozen conditions:

- exact semantic repeat agreement >= 0.90
- three-way Cohen kappa >= 0.80
- repeat equal-or-unsure rate <= 0.10

Undefined three-way kappa is a fail/review condition.

If the primary component gate passes but this secondary gate fails, component-model protocol design may be opened while direct overall-preference/Base Guitaristic Arbiter target training remains closed.

## Fail-closed validation

Before metrics are computed, the scorer verifies:

- exact sealed manifest identities and canonical manifest hashes;
- exact 120/48 task counts and unique task IDs;
- expected first/repeat export schemas and manifest references;
- complete integer 1–5 A/B scores for all four components;
- valid overall preference values;
- hidden audit linkage between each repeat task and its first-pass task;
- independently reblinded A/B source-option mappings;
- matching annotator identity;
- timezone-aware timestamps and the frozen 24-hour delay.

Any integrity failure stops scoring rather than producing a partial reliability result.

## Scientific boundary

S1-D repeat labels are permanently reliability-only. They may not be used for training, tuning, model selection, fitted rubric weights, DCR hard-error mining, checkpoint selection, or production/shadow integration.

No component specialist, Base Guitaristic Arbiter, or DCR-inspired refiner is trained or activated by this scorer.
