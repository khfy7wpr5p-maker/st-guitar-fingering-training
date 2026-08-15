# Stage 7G-E3-E-B — Blind untouched validation batch seal

## Purpose

E3-E-B freezes the Teacher-GOLD validation workload and the one-shot untouched evaluation rule **before any E3-E Teacher answers exist**.

The input is the merged E3-E-A3 target-blind pool of 1,937 events where the frozen `open_low` and `compact` specialists disagree across 24 new disagreement families. E3-E-B does not inspect preference labels and does not fit the E3-D router.

## Frozen Teacher workload

The validation batch contains exactly **240 tasks**.

Selection is deterministic and target-blind:

1. use exactly the A3-sealed 1,937 disagreement events;
2. order families by a stable SHA-256 family ordering;
3. order events within family by stable event-ID SHA-256;
4. select in family-balanced round-robin rounds until 240 tasks are reached;
5. require all 24 disagreement families to appear.

The design is nominally 10 tasks per disagreement family. Families with fewer available disagreements are exhausted and later rounds fill the remaining slots from other families. The resulting sealed family contribution range is 1–12 tasks. This is recorded rather than corrected after seeing labels.

Selected target-blind diagnostic strata are:

- L1: 25
- L2: 135
- L3: 43
- L4: 37

L1–L4 are reporting diagnostics only. They are not model features and did not determine the 240-task selection.

Selected event-ID set SHA-256:

`293ac5116a9c4b94993f150640c5113deaf213b7d59ddd6cebfdbec82cc9c7d7`

## Teacher blinding

The Teacher-facing package contains a self-contained offline HTML A/B interface plus a blank JSON response template and blind manifest.

The Teacher view exposes only the pitches and the two physical string/fret proposals. It withholds:

- source identity;
- family identity;
- specialist identity;
- curriculum level;
- 40 feature values;
- router/model prediction;
- threshold.

Responses are exactly `A`, `B`, or `EQUAL_OR_UNSURE`.

The internal audit containing proposal-to-specialist mapping, family/source identity, L1–L4, and features is a separate non-Teacher artifact and is not included in the Teacher ZIP.

## Sealed artifact identities

- Teacher manifest SHA-256: `17cf5513d1068b18b975a579da591540126e50c8fd9c89b59baaaee3e22ae352`
- Internal audit SHA-256: `75440e8e97c1ab80c27d93f8f37d1545a776e7fc8d9d0ddc6de5fdad9d98f7ee`
- Blank response template SHA-256: `00054dc4b669822ba885d5db7c8f2dcb46e29667b0b793148029006d23ffa550`
- Teacher package filename: `ST_Guitar_E3E_Teacher_GOLD_240.zip`
- Teacher package bytes: `373739`
- Teacher package SHA-256: `d9c74e247d9fcab684b4965a7c0018ccb8beafb8fbfc92c09687ff3d494c858f`

The Teacher package and internal audit remain external to Git. Git stores only protocol/evidence/hashes.

## Preregistered one-shot untouched gate

All 240 tasks must first be completed. `EQUAL_OR_UNSURE` responses are retained for audit and excluded from binary metrics.

An **evaluable family** is a family with at least one decisive A/B response.

Before any performance conclusion, the answer set must contain at least:

- 200 decisive A/B events; and
- 20 evaluable families.

If either minimum is not met, the result is:

`INSUFFICIENT_UNTOUCHED_EVIDENCE_NO_PROMOTION`

This does not authorize extra outcome-driven sampling, threshold rescue, calibration, or retuning on E3-E.

### Frozen model finalization

The one-shot E3-E evaluation will fit/finalize from the **399 decisive E3-D development rows only** using the already-frozen 40 features and model:

- `StandardScaler`
- `LogisticRegression(max_iter=2000, class_weight=None, C=1.0, solver="lbfgs", random_state=0)`
- positive class: `COMPACT`
- default: `OPEN_LOW`

The compact probability threshold is preregistered here as **0.5** using a development-only inheritance rule: 0.5 is the mode of the already-consumed E3-D outer-fold selected thresholds `[0.5, 0.5, 0.6, 0.5, 0.5]`.

This is an E3-E-B preregistration decision made before E3-E labels. It is **not** claimed to have been a single global threshold already fixed by E3-D, and E3-E labels may not alter or search it.

### Positive untouched signal

After the sufficiency gate passes, `POSITIVE_UNTOUCHED_SIGNAL_ELIGIBLE_FOR_PROMOTION_DESIGN` requires **all** of:

- event accuracy delta versus always-`open_low` > 0;
- macro-family accuracy delta versus always-`open_low` > 0;
- compact precision >= 2/3;
- compact TP > compact FP;
- family wins > family losses.

For family metrics, equal/unsure rows are excluded. A family win/tie/loss compares frozen-model binary accuracy against always-`open_low` binary accuracy inside that evaluable family. Macro-family accuracy is the mean binary accuracy over evaluable families.

If sufficiency passes but any positive requirement fails, the result is:

`NEGATIVE_UNTOUCHED_VALIDATION_NO_PROMOTION`

No post-hoc rescue, feature change, threshold search, calibration, class-weight change, or model-family search is allowed on these E3-E labels.

## Safety state at seal

- Teacher answers read: **no**
- E3-E model fit: **no**
- E3-E threshold tuned from labels: **no**
- checkpoint retained: **no**
- production/shadow integration: **no**
- Stage7E reused for modeling: **no**
- MuseTrainer source clearance: **research-only; commercial/production clearance not established**

A positive E3-E result may only open a later separate promotion-design gate. It does not authorize checkpoint retention or production integration.

## Next step

After this seal is merged and post-main CI is verified, the exact hashed Teacher package may be delivered for Stage 7G-E3-E-C blind annotation. The exported 240-choice JSON must be validated for exact task-set equality before any untouched model evaluation is run.
