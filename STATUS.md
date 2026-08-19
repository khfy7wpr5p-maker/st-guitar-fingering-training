# Status

## Current repository truth

- Default branch: `main`
- Deterministic runtime baseline through S1-H-C: `154d8d4c514849535a523ca79ea22b6fae7e77de`
- S2-A protocol preregistration: ✅ merged PR #77
- S2-A data/features/reliability implementation: ✅ merged PR #78
- S2-A fail-closed ranker + development-CV harness: ✅ merged PR #79
- S2-A untouched-final evaluation gate: ✅ merged PR #80
- Executable S2-A implementation baseline through PR #80: `7b05c18bcde3b8ff84f77dffc25a5ced307c47a4`
- Real S2-A project fit: ⛔ **NOT EXECUTED — eligible new Teacher corpus/reliability evidence absent**
- Checkpoint retention: 🔒 closed
- Shadow / production integration: 🔒 closed

## Implemented pipeline

```text
Guitar Pro / MusicXML
        ↓
safe normalization + event/chord extraction
        ↓
valid_chord_voicings()                         ✅ AUTHORITATIVE PHYSICAL SET
        ↓
S1-H-A deterministic plausibility             ✅
        ↓
S1-H-B four-finger/barre feasibility          ✅
        ↓
S1-H-C standard finger assignments            ✅
        ↓
S2-A 30D assignment features                  ✅
        ↓
S2-A blind pair + repeat reliability tooling  ✅
        ↓
S2-A fail-closed ranker / 5-fold CV harness   ✅
        ↓
S2-A untouched-final evaluator                ✅
        ↓
NEW FIRST_PASS TEACHER CORPUS                 ⏳ REQUIRED INPUT
        ↓
REPEAT RELIABILITY PASS                       🔒 EVIDENCE GATE
        ↓
REAL S2-A MODEL FIT                           🔒 DATA GATE
        ↓
UNTOUCHED FINAL                               🔒 DEVELOPMENT-PASS GATE
        ↓
CHECKPOINT RETENTION REVIEW                   🔒 SEPARATE GATE
```

## S2-A target and provenance

Target: `STATIC_STANDARD_FINGERING_NATURALNESS` for one isolated chord under ordinary left-hand technique.

Exact provenance roles:

- `S2A_STATIC_NATURALNESS_FIRST_PASS` — decisive rows may become fit-eligible only after every corpus/reliability gate passes;
- `S2A_STATIC_NATURALNESS_REPEAT` — reliability-only, never training;
- `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL` — final-only, never training/tuning.

`EQUAL_OR_UNSURE` is retained as uncertainty evidence and excluded from decisive fit rows; it is never coerced into A/B.

## PR #78 — data/features/reliability machinery

Implemented:

- exact 30D deterministic target-blind feature vector from H-C assignments;
- feature hash: `d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`;
- fresh H-C assignment lineage validation;
- label-free `FINGER_ONLY` / `MIXED` pair construction;
- event-local `NEAR/MID/FAR` distance strata;
- deterministic blinded A/B presentation, max 6 tasks/event;
- exact provenance-aware complete response validation;
- deterministic repeat package;
- exactly 50% A/B reversal;
- three-class exact agreement + decisive Cohen-kappa reliability report;
- 24–72h repeat interval guard;
- no old-answer import surface.

Verification: CI #203 — **252 tests PASS**, compile PASS. Stage 7B-C2 workflow step skipped by branch condition and not counted as PASS.

## PR #79 — learned ranker execution harness

Implemented:

- sealed package → decisive S2-A pair rows only after fresh H-C recomputation;
- stored feature vectors must exactly match fresh recomputation;
- mirrored `phi(A)-phi(B)` / `phi(B)-phi(A)` rows for exact pair symmetry;
- frozen model constructor: no-intercept L2 `LogisticRegression`, `C=1`, `lbfgs`, no scaler, no hyperparameter search;
- real-fit gate requiring all frozen sample/slice/reliability minimums;
- tiny or forged PASS dictionaries cannot bypass sample/evidence gates;
- deterministic 5-fold `family_id`-isolated development CV;
- frozen LOW_FRET / COMPACT comparator selection from development only;
- pairwise accuracy, macro-family accuracy, ROC-AUC, log loss, Brier, family wins/ties/losses, and slice metrics;
- 10/10 development-CV reproduction check;
- inference re-generates H-C and can rank only that exact assignment-ID set.

Verification: CI #205 — **256 tests PASS**, compile PASS. Stage 7B-C2 step skipped and not counted as PASS.

Non-blocking compatibility note: scikit-learn 1.9 warns that explicit `penalty="l2"` will be deprecated in a future release. Current frozen behavior is valid and unchanged; any syntax migration must preserve the preregistered L2 semantics and be handled as a separate compatibility maintenance change.

## PR #80 — untouched-final gate

Implemented:

- exact FINAL provenance only;
- development must already be PASS;
- final comparator inherited from development and cannot be reselected on final labels;
- >=20 final families and >=200 decisive final pairs;
- development/final family overlap fails closed before model inference;
- deterministic 2000-resample family-block bootstrap, seed 0;
- final PASS requires 95% bootstrap CI lower bound for family-level improvement > 0;
- PASS returns only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`;
- no checkpoint or integration action is performed.

Verification: CI #207 — **260 tests PASS**, compile PASS. Stage 7B-C2 step skipped and not counted as PASS.

## Real-fit gate remains closed for a concrete reason

Model-development authorization is active, but authorization alone is not training data.

`fit_s2a_ranker()` cannot execute a real project fit until the new FIRST_PASS corpus reaches at least:

- 40 development families;
- 200 eligible events;
- 600 decisive pairs;
- 150 `FINGER_ONLY` decisive pairs;
- 150 `MIXED` decisive pairs;
- 100 decisive pairs in each `NEAR/MID/FAR` stratum;
- repeat sample >= `max(120, 20% of annotated development tasks)`;
- exact repeat agreement >= 0.85;
- decisive Cohen kappa >= 0.75;
- 24–72h repeat interval;
- exactly 50% A/B reversal;
- zero overlap with reserved untouched-final families.

No repository evidence currently satisfies this new S2-A contract, so no real coefficients/checkpoint exist yet.

## Protected historical evidence

The new model path may not recycle:

- S1-E pilot/repeat labels;
- S1-G v2 first-pass/repeat evidence;
- historical repeat/reliability rows;
- Stage 7E or E3-E consumed untouched evidence.

S1-F historical project-label fit remains a separate hard-closed historical path; S2-A does not reopen it.

## Current controlled continuation point

The executable S2-A model architecture is ready. The remaining blocker is **fresh human supervision**, not missing ranking code.

Next safe operational sequence:

1. assemble new events/families for S2-A without using protected evidence;
2. generate blind FIRST_PASS Teacher packages from H-C;
3. collect human A/B/EQUAL_OR_UNSURE answers;
4. run the frozen 24–72h repeat package and reliability gate;
5. only if the full corpus and reliability gates PASS, execute real development fit/CV;
6. if development PASS, collect/evaluate untouched-final data;
7. stop at checkpoint-retention review even after final PASS.

## Frozen evidence semantics

Frozen preregistration/evidence JSON files remain historical snapshots and are not retroactively rewritten. Live status is maintained here and in the other top-level documents.
