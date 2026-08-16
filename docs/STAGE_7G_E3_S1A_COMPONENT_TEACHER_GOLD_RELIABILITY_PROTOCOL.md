# Stage 7G-E3-S1-A — Component Teacher-GOLD Reliability Contract

## Purpose

S1-A is the first stage after the S0 diagnostic/rubric work. It does **not** train a model. It freezes a larger independent-component Teacher-GOLD collection and a blind repeat-reliability test before any component specialist or Guitaristic Arbiter is designed for training.

The reason is direct:

- S0-C showed that the old single A/B “more natural” target was not repeatable enough for specialist activation;
- S0-D-A showed that asking several pairwise subquestions still produced perfectly collinear answers;
- S0-D-B showed that independent 1–5 scoring of A and B can separate guitaristic components.

S1-A therefore tests whether that decomposed rubric is **reliably repeatable at larger scale**.

The machine-readable authority is `evidence/stage7g_e3_s1a_component_teacher_gold_reliability_protocol.json`.

## Frozen first-pass corpus

S1-A will seal **120 tasks** before Teacher responses are collected:

- L1: 30
- L2: 30
- L3: 30
- L4: 30

Selection is target-blind and deterministic. Historical Teacher preference may not influence task selection.

The source is the same 40-family E3 development domain used for the earlier Batch01 work. This means S1-A is a **development/data-quality stage**, not a new untouched external-validation claim.

Before selection, the following are excluded:

- the original 1 equal/unsure source row;
- the 60 S0-C repeat tasks;
- the 20 S0-D-A rubric tasks;
- the 20 S0-D-B independent-scoring pilot tasks.

The selected 120-task corpus must contain at least **32 distinct families** and no family may contribute more than **4 tasks**.

## Family isolation

The 120 tasks receive a frozen five-fold family assignment before labels are used.

Families are deterministically ordered by a SHA-256 salt and assigned round-robin to folds 0–4. Every task from one family stays in the same fold.

These folds preserve future family-isolated development evaluation structure. **S1-A itself does not authorize training.**

## Teacher scoring flow

For every task:

1. show candidate A alone;
2. score A on all four 1–5 component scales;
3. lock those scores;
4. show candidate B alone;
5. score B on all four 1–5 component scales;
6. lock those scores;
7. only then show A and B together and collect the overall A/B/equal-or-unsure preference.

The four frozen component dimensions are:

- `POSITION_COMFORT`
- `STRING_DISTRIBUTION`
- `FINGER_SPREAD`
- `OPEN_STRING_UTILITY`

The scale anchors are unchanged from S0-D-B. In particular:

- high fret position is not automatically bad;
- open string is not automatically good;
- no-open-string cases use 3 as neutral for `OPEN_STRING_UTILITY`;
- finger spread must focus on hand shape/stretch rather than fret height by itself.

To reduce fatigue, the 120 tasks are divided into **four sealed sessions of 30**. Session membership is deterministic and may not be changed because of answers.

## Blind repeat test

Before any first-pass answers are opened, **48 of the 120 tasks** are also frozen as the repeat subset:

- L1: 12
- L2: 12
- L3: 12
- L4: 12

No family may contribute more than two repeat tasks.

The repeat test occurs at least **24 hours after first-pass completion**. A/B sides are independently reblinded and the task order is reshuffled. First-pass scores, historical answers, family IDs, curriculum levels, and specialist identities remain hidden.

The 48 repeated tasks create **96 paired option ratings per component** because each task contains both A and B option scores.

Repeat responses are permanently **reliability-only**. They may not be duplicated into a training set.

## Primary component-reliability gate

Every one of the four component scales must satisfy all of the following on the frozen repeat set:

| Metric | Required |
|---|---:|
| Quadratic-weighted Cohen kappa | >= 0.90 |
| Exact 1–5 score agreement | >= 0.80 |
| Agreement within ±1 point | >= 0.98 |
| Mean absolute score difference | <= 0.35 |

A variance guard also applies. For each component, the first-pass ratings in the repeat subset must use at least three distinct score values and no single score may exceed 85% of those ratings. Undefined kappa is a failure/review condition, not a pass.

If **all four** components pass, the status is:

`S1A_COMPONENT_RELIABILITY_GATE_PASS_ELIGIBLE_FOR_COMPONENT_TRAINING_PROTOCOL_DESIGN`

This opens only the design of a later component-model training protocol. It does not train or activate any model.

If any component fails, the status is:

`S1A_COMPONENT_RELIABILITY_GATE_FAIL_REVIEW_RUBRIC_BEFORE_TRAINING`

No threshold may be changed after seeing the answers.

## Secondary overall-preference repeat gate

The 48 repeated task-level final A/B/equal-or-unsure choices are measured separately.

Frozen secondary thresholds:

- exact semantic repeat agreement >= 0.90;
- three-way Cohen kappa >= 0.80;
- repeat equal-or-unsure rate <= 0.10.

This gate is intentionally separate from the component gate. A component scale may be reliable even if the final global preference remains unstable.

If the overall gate fails, direct overall-preference / Guitaristic Arbiter supervision stays closed even if the four component scales pass.

## Training quarantine

S1-A is a data-quality gate, not a training stage.

- first-pass component labels remain quarantined until the primary component-reliability gate passes **and** a separate training protocol is merged;
- repeat labels are reliability-only forever;
- S1-A overall preference labels are descriptive only;
- S0-D-B pilot labels remain architecture-design evidence and do not automatically enter a future training corpus.

## Forbidden in S1-A

- model training;
- component specialist training;
- Guitaristic Arbiter training;
- rubric-weight fitting;
- threshold or hyperparameter tuning;
- post-result changes to task quotas or reliability thresholds;
- historical Teacher preference-driven task selection;
- Stage 7E reuse;
- E3-E Teacher-GOLD reuse;
- checkpoint retention/promotion;
- GuitarTab Engine shadow or production integration.

## What happens after S1-A

There are two independent decisions:

1. **Component gate PASS** → a new, separately preregistered training protocol may be designed for component analyzers.
2. **Overall gate PASS** → later Arbiter target design may be studied; it still does not authorize Arbiter training by itself.

If the component gate fails, the project remains in rubric/data-design mode and does not solve the failure by silently lowering the gate or training a larger model.
