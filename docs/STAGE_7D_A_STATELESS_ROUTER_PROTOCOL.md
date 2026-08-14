# Stage 7D-A — Stateless Specialist Router Protocol

Status: **DIAGNOSTIC PROTOCOL — REAL ROUTER RESULT PENDING**

## Goal

Test whether a target-blind router can choose among the four stateless Stage 7 specialists on independent real Guitar Pro/MusicXML families and outperform the strongest simple deployment baseline: **always choose `open_low`**.

## Included specialists

- `open_low`
- `compact`
- `mid_position`
- `high_position`

`common_tone` is intentionally excluded from Stage 7D-A. Stage 7C-R1 measured it with the observed previous real voicing as teacher-forced diagnostic context. A rollout-safe context version must be evaluated separately before `common_tone` can enter a deployable router.

## Router supervision

For each ambiguous real chord event, every frozen stateless specialist ranks the full deterministic physical candidate set. A binary label records whether that specialist's Top-1 candidate matches the observed Guitar Pro voicing.

Label semantics:

`specialist_top1_matches_observed_behavior_not_teacher_gold`

The observed target is **not** part of the router feature vector. It is used only to create training labels within training families and to score held-out validation families.

## Router features

Features are target-blind and derived only from:

1. current chord pitches;
2. the deterministic physical candidate set;
3. the frozen specialist's own Top-1 candidate geometry;
4. the frozen specialist's score margin/spread;
5. specialist identity.

The router never creates string/fret candidates.

## Validation

- deterministic family-isolated cross-validation;
- no family may appear in both router train and validation rows;
- validation targets never enter router fitting;
- compare router Top-1 against `always_open_low` on exactly the same held-out events;
- also report stateless oracle coverage as an upper-bound diagnostic, never as deployable accuracy.

## Acceptance gate for a later real-corpus run

A positive router result requires, at minimum:

- family isolation PASS;
- target-blind feature contract PASS;
- router macro Top-1 > always-open-low macro Top-1;
- no checkpoint retention;
- no production integration.

A failure to beat `always_open_low` means the router is rejected; the specialist bank itself is not invalidated.

## Safety state

- AI physical candidate generation: **none**
- common-tone teacher-forced context in router: **none**
- checkpoint retained: **false**
- production integration: **false**
