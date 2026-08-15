# Stage 7G-E3-E — Untouched Family-Disjoint Teacher-GOLD Validation Design

## Purpose

Stage 7G-E3-E is the next scientific gate after the positive Stage 7G-E3-D development result. Its purpose is to test whether the conservative `OPEN_LOW`-default / gated-`COMPACT` decision rule transfers to **new source families that have not participated in Teacher-GOLD development, feature/hypothesis development, threshold analysis, or prior final evaluation**.

E3-E is validation-only. It is not a new training/tuning stage.

## Non-negotiable separation

The following material is forbidden for E3-E validation selection or labels:

- the 40-family Teacher-GOLD development domain used across E1/E2/E3;
- the original 556 decisive E1/E2 pairwise labels;
- the first 38 richer full-candidate Teacher-GOLD labels;
- the E3 Batch01 400-task curriculum set;
- Stage 7E, which is permanently consumed and forbidden for reuse;
- any family or exact event already used to form, diagnose, tune, calibrate, or evaluate the E3-D development hypothesis.

A family-disjoint audit must pass before Teacher-GOLD annotation begins.

## Frozen model behavior entering E3-E

E3-E must not use its labels to change the model, features, specialists, or threshold policy.

The entering behavior is frozen from E3-D:

- deterministic guitar physics remains the sole authority for physical validity;
- candidate specialists remain `open_low` and `compact` for this gate;
- exactly the frozen 40 target-blind E3 features are used;
- model family remains `StandardScaler` + `LogisticRegression` with the E3-D fixed hyperparameters;
- `OPEN_LOW` remains the default/fallback decision;
- no sequence context is introduced;
- no post-hoc feature selection, calibration, class-weight change, C search, model-family search, or rescue threshold is allowed after E3-E labels are seen.

## E3-E construction phases

### E3-E-A — New-family intake audit

Before any Teacher-GOLD labels exist:

1. collect new candidate MusicXML source material;
2. assign stable family IDs;
3. prove zero family overlap with all consumed Teacher-GOLD development families and Stage 7E;
4. run only target-blind deterministic parsing, candidate generation, specialist reconstruction, and 40-feature extraction;
5. inventory only events where `open_low != compact`;
6. record licensing/provenance status for every source family;
7. abort on uncertain family identity, target leakage, physical-invalid candidate generation, non-finite features, or provenance ambiguity that prevents the intended research use.

No Teacher-GOLD preference labels may be inspected or collected during this phase.

### E3-E-B — Validation batch seal

From the target-blind disagreement inventory:

1. choose the validation quota and family allocation **before annotation**;
2. prioritize broad family coverage rather than repeated events from a small number of families;
3. preserve L1–L4 only as target-blind diagnostic strata; curriculum level is not a model feature;
4. create a blind A/B Teacher manifest with specialist identities hidden;
5. create a separate internal audit containing family, level, features, proposal mapping, hashes, and overlap proofs;
6. freeze manifest and audit SHA-256 values before Teacher-GOLD answers are collected.

The exact event count is intentionally not fixed in this design document. It must be frozen only after the new-family target-blind inventory is known, without access to preference labels.

### E3-E-C — Blind Teacher-GOLD collection

Teacher annotation must preserve the established semantics:

- A / B / equal-or-unsure only;
- proposal identities hidden from the teacher;
- no model prediction, probability, threshold, family identity, curriculum level, or prior label exposed during annotation;
- equal/unsure retained for audit and excluded from binary accuracy calculations unless a separately preregistered rule says otherwise.

Raw answer rows remain external to Git. Git may receive only aggregate evidence, seals/hashes, protocols, and non-sensitive audit summaries.

### E3-E-D — Single frozen untouched evaluation

After the sealed Teacher-GOLD batch is complete:

1. verify all manifest/answer hashes and exact task-set equality;
2. verify family disjointness again;
3. fit/finalize the entering E3-D model behavior using **development data only**;
4. apply that frozen behavior once to E3-E;
5. do not choose or revise thresholds from E3-E labels;
6. report aggregate event and family metrics, compact precision/recall, TP/FP/FN, switch rate, family win/tie/loss, and L1–L4 diagnostics;
7. export aggregate evidence with `checkpoint_retained=false` and `production_integration=false` by default.

## Gate design

E3-E must have a preregistered pass/fail gate before its Teacher-GOLD answers are opened. That gate should test both:

- transfer beyond the `always_open_low` baseline; and
- conservative switch quality, so gains are not produced by uncontrolled over-switching to `compact`.

The exact numeric gate is **not selected in this design document**. It must be frozen in a later protocol/seal PR before Teacher-GOLD answers are collected. No threshold or pass criterion may be selected after observing E3-E labels.

## Outcomes

### If E3-E is positive

A positive untouched result may authorize a later, separate checkpoint/promotion design gate. It does not itself authorize production or GuitarTab Engine integration.

### If E3-E is negative

Record the negative result. Do not tune, rescue, recalibrate, or search new thresholds on the same E3-E labels. Any new hypothesis requires a new development cycle and a new untouched validation resource.

## Current safety state

At the opening of E3-E design:

- E3-D development gate: **positive**
- E3-E Teacher-GOLD collected: **no**
- E3-E validation set sealed: **no**
- E3-E labels observed: **no**
- checkpoint retained/promoted: **no**
- production/shadow integration: **no**

The immediate next work item is E3-E-A: obtain and audit genuinely new family-disjoint source material before any validation annotation is created.
