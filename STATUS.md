# Status

## Current repository truth

- Default branch: `main`
- Deterministic runtime baseline through S1-H-C: `154d8d4c514849535a523ca79ea22b6fae7e77de`
- S2-A protocol preregistration: ✅ merged PR #77
- S2-A data/features/reliability implementation: ✅ merged PR #78
- S2-A fail-closed ranker + development-CV harness: ✅ merged PR #79
- S2-A untouched-final evaluation gate: ✅ merged PR #80
- S2-A fresh assignment-level Teacher Batch01 tooling: ✅ merged PR #82
- S2-A Batch01 FIRST_PASS response seal: ✅ merged PR #83
- S2-A Batch01 scientific role: **DIAGNOSTIC_ONLY_NEVER_TRAINING**
- Real S2-A project fit: ⛔ **NOT EXECUTED — no fit-eligible fresh Teacher-naive corpus/reliability evidence yet**
- Checkpoint retention: 🔒 closed
- Shadow / production integration: 🔒 closed

## Implemented pipeline and current gate

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
Batch01: 720 human responses                  ✅ DIAGNOSTIC ONLY
        ↓
FRESH SOURCE RESERVATION                      ⏳ CURRENT GATE
        ↓
FIT-ELIGIBLE FIRST_PASS CORPUS                 🔒
        ↓
REPEAT RELIABILITY PASS                       🔒
        ↓
REAL S2-A MODEL FIT                           🔒
        ↓
DEVELOPMENT PASS                              🔒
        ↓
UNTOUCHED FINAL                               🔒
        ↓
CHECKPOINT RETENTION REVIEW                   🔒 SEPARATE GATE
```

## S2-A target and frozen model contract

Target: `STATIC_STANDARD_FINGERING_NATURALNESS` for one isolated chord under ordinary four-finger left-hand technique.

Exact provenance roles remain:

- `S2A_STATIC_NATURALNESS_FIRST_PASS` — decisive A/B rows may be fit-eligible only after source, corpus and reliability gates pass;
- `S2A_STATIC_NATURALNESS_REPEAT` — reliability-only, never training/tuning/model selection;
- `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL` — final-only, never training/tuning/model selection.

`EQUAL_OR_UNSURE` is retained as ambiguity evidence and excluded from decisive fit rows. It is never coerced into A/B.

Frozen v1 learned model remains unchanged: 30 target-blind deterministic features, no scaler, no hyperparameter search, no-intercept L2 `LogisticRegression(C=1.0, solver="lbfgs")`, family-isolated 5-fold development CV, and stable H-C assignment-ID authority at inference.

## Batch01 completed human evidence

All six FIRST_PASS sessions were completed and validation-clean:

- total tasks: 720/720;
- A: 164;
- B: 167;
- `EQUAL_OR_UNSURE`: 389;
- decisive A/B: 331 (45.97%);
- unique task IDs: 720;
- duplicate task IDs: 0;
- invalid responses: 0.

Diagnostic slice counts:

- `FINGER_ONLY`: 139 / 360 decisive (38.61%);
- `MIXED`: 192 / 360 decisive (53.33%);
- `NEAR`: 128 / 240 decisive (53.33%);
- `MID`: 105 / 240 decisive (43.75%);
- `FAR`: 98 / 240 decisive (40.83%).

Among decisive responses, A/B presentation is nearly balanced: A=164 (49.55%), B=167 (50.45%). The high abstention rate therefore must not be repaired by relabeling or side assumptions.

## Batch01 source-policy closeout

Batch01 reused the same 40 AnimeTAB source-family identities that had already participated in an earlier Teacher-preference development experiment. Historical answers themselves were not reused, but the S2-A.v1 preregistration states that historical development sources do not establish new S2-A evaluation evidence.

Therefore Batch01 is permanently classified:

`DIAGNOSTIC_ONLY_NEVER_TRAINING`

Consequences:

- effective S2-A fit rows from Batch01: **0**;
- Batch01 repeat reliability: **DO NOT RUN**;
- Batch01 model fit: **DO NOT RUN**;
- Batch01 may not become tuning, model-selection or untouched-final evidence;
- the 720 responses remain preserved as diagnostic evidence only.

The Batch01 pilot also shows that feature L1 distance is not a monotonic proxy for Teacher decisiveness: NEAR was more decisive than MID and FAR. `NEAR/MID/FAR` therefore remain label-blind sampling strata only and must not become post-hoc confidence thresholds.

## Fresh S2-A.v1 collection plan

The conservative continuation keeps the frozen v1 model, features, thresholds and response semantics unchanged. Before any new human annotation, source and task identities must be sealed label-blind.

Pre-reserve three mutually disjoint, Teacher-naive source groups from a pinned full-track corpus:

1. **Primary development:** 80 fresh families, 1,440 tasks, 18 tasks/family, exactly 240 tasks in each `FINGER_ONLY/MIXED × NEAR/MID/FAR` cell.
2. **Contingency development:** 20 additional fresh families, 360 tasks, reserved before primary labels. Open only if frozen corpus-count gates remain short after the primary batch; never because of model performance or label direction.
3. **Untouched final:** 20 additional fresh families reserved before development annotation and kept closed until development PASS.

No family previously exposed in a Teacher preference experiment may enter these reservations. Protected Stage 7E/E3-E final evidence remains excluded.

## Frozen real-fit gate

`fit_s2a_ranker()` remains closed until a fit-eligible fresh FIRST_PASS corpus satisfies at least:

- development families >= 40;
- eligible events >= 200;
- decisive pairs >= 600;
- `FINGER_ONLY` decisive >= 150;
- `MIXED` decisive >= 150;
- `NEAR`, `MID`, `FAR` decisive >= 100 each;
- repeat sample >= `max(120, 20% of annotated development tasks)`;
- three-class repeat agreement >= 0.85;
- decisive Cohen kappa >= 0.75;
- repeat interval 24–72h;
- exactly 50% A/B reversal;
- zero development/final family overlap.

Reliability is run only after the fresh development FIRST_PASS corpus passes its count gates. Repeat rows remain reliability-only.

## Development and final gates

Development PASS still requires all preregistered pairwise, macro-family, ROC-AUC, baseline-delta, family win/loss, slice and 10/10 determinism gates. Failure does not open untouched final.

Untouched final remains a separate >=20-family / >=200-decisive-pair gate with inherited comparator, family-block bootstrap and zero development-family overlap. A final PASS yields only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`; it does not retain a checkpoint or activate GuitarTab Engine integration.

## Protected historical evidence

The S2-A model path may not recycle:

- S1-E pilot/repeat labels;
- S1-G v2 first-pass/repeat evidence;
- historical repeat/reliability rows;
- Stage 7E consumed final evidence;
- E3-E Teacher-GOLD consumed final evidence;
- Batch01 diagnostic rows after this closeout.

S1-F historical project-label fit remains a separate hard-closed historical path.

## Current controlled continuation point

Next gate:

`FREEZE_FRESH_SOURCE_RESERVATION_AND_BATCH02_TASK_IDENTITIES_BEFORE_COLLECTION`

The immediate engineering work is to census the pinned AnimeTAB full-track pool, exclude every Teacher-exposed/protected family, pre-reserve primary/contingency/final families, validate their source structure, and seal all identities before asking for any new answers.

## Frozen evidence semantics

Frozen preregistration and historical evidence JSON files are not retroactively rewritten. Live status is maintained here; new decisions are added as new evidence records.
