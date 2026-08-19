# Stage 7G-E3-S2-A — Batch01 diagnostic closeout

Status: **DIAGNOSTIC_ONLY_NEVER_TRAINING**

This record resolves the two open questions after the six S2-A Batch01 FIRST_PASS sessions were completed: whether Batch01 may establish fit evidence, and whether its high `EQUAL_OR_UNSURE` rate justifies changing the frozen v1 model or sampling semantics.

## 1. Source-policy decision

Batch01 reused the same 40 AnimeTAB source-family identities that had already participated in the earlier Stage 7G-E3 Teacher-preference development path. No historical answer was imported or relabeled, but source-family exposure itself matters.

The S2-A.v1 preregistration states that historical development sources do not establish new S2-A evaluation evidence. Therefore Batch01 is now permanently classified as:

`DIAGNOSTIC_ONLY_NEVER_TRAINING`

Consequences:

- its 720 responses remain preserved as diagnostic evidence;
- none of its 331 decisive A/B rows may enter S2-A fit, tuning, model selection or untouched-final evidence;
- its effective fit-row contribution is zero;
- no repeat-reliability burden is imposed on Batch01;
- no model fit is run from Batch01.

This is stricter than merely saying the numeric corpus gate failed. Even if Batch01 had contained 600 decisive labels, its source-policy role would still prevent it from becoming S2-A fit evidence.

## 2. What the 720 answers show

The response export is structurally clean: 720/720 tasks, unique task IDs, valid sealed manifests and blinded annotation.

Aggregate response counts:

- A: 164
- B: 167
- `EQUAL_OR_UNSURE`: 389
- decisive A/B: 331 / 720 = 45.97%

Among decisive choices, A and B are nearly balanced (49.55% vs 50.45%). There is therefore no obvious presentation-side imbalance in this pilot.

The main ambiguity signal is real and broad rather than confined to one session or one sampling cell:

- `FINGER_ONLY`: 139 / 360 decisive = 38.61%
- `MIXED`: 192 / 360 decisive = 53.33%
- `NEAR`: 128 / 240 decisive = 53.33%
- `MID`: 105 / 240 decisive = 43.75%
- `FAR`: 98 / 240 decisive = 40.83%

The six exact pair-type × distance cells are preserved in `evidence/stage7g_e3_s2a_batch01_diagnostic_decision.json`.

## 3. What we must NOT infer

The pilot does not authorize post-hoc manipulation of the target.

In particular:

- `EQUAL_OR_UNSURE` must not be coerced into A or B;
- `FAR` must not be redefined as a human-confidence stratum;
- L1 feature distance must not be used as a label-derived confidence threshold;
- the frozen 30D feature contract, linear Bradley–Terry-like utility model, estimator settings and development thresholds remain unchanged;
- Batch01 labels must not be used to mine preferred features or hyperparameters.

The observed decisive rate is lower in FAR than in NEAR for this pilot, so feature distance is demonstrably not a monotonic proxy for Teacher decisiveness here. The distance strata remain sampling geometry only.

## 4. Conservative continuation under S2-A.v1

There is no need to rewrite the model because a diagnostic pilot produced many abstentions. The safer continuation is to keep the preregistered v1 model unchanged and collect enough **fresh, Teacher-naive source families**.

Before any new human response is collected, freeze three disjoint source reservations from a pinned corpus:

1. **Primary development:** 80 fresh families, 1,440 tasks total, 18 tasks/family, 240 tasks in each `FINGER_ONLY/MIXED × NEAR/MID/FAR` cell.
2. **Contingency development:** 20 additional fresh families, 360 tasks total, reserved in advance. It may be opened only if the primary batch fails the frozen corpus-count minimums. The trigger may not depend on model performance or label direction.
3. **Untouched final:** 20 additional fresh families, reserved before development annotation and kept completely closed until development PASS.

All source identities and task identities must be selected target-blind and sealed before new annotation. Existing Stage 7E/E3-E final families and every previously Teacher-exposed S2-A/Stage7G development family remain excluded.

The pilot response rate may inform the *quantity* of future annotation needed, but may not drive which candidate wins, which features are selected, or which model is preferred.

## 5. Reliability timing

Do not build or answer a Batch01 repeat package.

Reliability is deferred until the new, fit-eligible development FIRST_PASS corpus itself passes every frozen corpus-count gate. The repeat set must then be built only from that fresh corpus under the existing 24–72 hour, 50% side-reversal and agreement/kappa contract.

## 6. Next gate

The next executable gate is:

`FREEZE_FRESH_SOURCE_RESERVATION_AND_BATCH02_TASK_IDENTITIES_BEFORE_COLLECTION`

No real S2-A coefficients, checkpoint, untouched-final result, shadow activation or production integration exist at this point.
