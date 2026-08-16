# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0 | Safety + architecture baseline | ✅ contracts + CI |
| 1 | Dataset Contract v1 | ✅ immutable schema + family split rules |
| 2 | Guitar Pro/MusicXML intake + normalizer | ✅ safe parse + stream/tuning/pitch mode |
| 3 | Physical validation + event extraction | ✅ independent pitch/string/fret veto |
| 4 | Dataset Builder v1 | ✅ family split + deterministic candidate generation |
| 5 | First bounded single-note training | ✅ executed; no retained production checkpoint |
| 6 | Chord voicing specialists + context experiments | ✅ research completed; failed rollout paths retained as negative evidence |
| 7D-A / 7E | Target-blind stateless specialist routing | ✅ relative research advantage survived Stage 7E; Stage 7E permanently consumed |
| 7G-A → 7G-D | Teacher-GOLD corpus + blind pairwise annotation | ✅ 556 decisive labels / 40 families; 38 richer full-candidate labels separate |
| 7G-E1 | First real Teacher-GOLD pairwise router | ✅ negative: 70.50% vs 77.88% `always_open_low`; no promotion |
| 7G-E2 | Compact-preference error diagnostic | ✅ 107 compact false positives vs 66 recovered compact preferences |
| 7G-E3-A/B/C | Ergonomics curriculum + 40-feature contract + Batch01 Teacher-GOLD | ✅ 400/400 responses; 399 decisive |
| 7G-E3-D-R1 | Conservative compact-gate development experiment | ✅ positive development signal: +8.27 pp event, +7.84 pp macro; no checkpoint |
| 7G-E3-E | New-family untouched Teacher-GOLD validation | ✅ completed/consumed; positive untouched signal; no promotion/checkpoint |
| 7G-E3-R2 | Visible-learning MLP diagnostic | ✅ learned, but preregistered ultra-quality gate failed; no checkpoint |
| 7G-E3-S0 | Five-fold scientific failure diagnostic | ✅ recurrent overfit + family sensitivity + thin compact support + regime errors |
| 7G-E3-S0-B | Event-level error attribution | ✅ multi-factor errors dominant; position/topology notable descriptive axes |
| 7G-E3-S0-C | Blind Teacher-GOLD repeat reliability | 🔴 frozen reliability gate failed: 34/60 exact agreement; κ=0.1333 |
| 7G-E3-S0-D-A | Five-part pairwise rubric calibration | ✅ 20 tasks; all component A/B judgments collinear → not independent supervision |
| 7G-E3-S0-D-B | Independent per-option 1–5 component scoring | ✅ architecture-design signal: separation in 13/20 tasks; no specialist activation |
| Next architecture-design gate | Larger independent-component Teacher-GOLD + repeat reliability | **CURRENT POSITION — must be preregistered before collection** |
| Future | Component-specific analyzers | 🔒 not trained/activated |
| Future | Guitaristic Arbiter / Ranker | 🔒 design/training closed until component evidence is adequate |
| Future | Checkpoint retention | 🔒 closed |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | 🔒 future; blocked until a valid checkpoint/promotion gate passes |

## Current position

The project is no longer waiting for E3-D or E3-E. Those experiments are complete. The current problem is the **quality and structure of guitarist-preference supervision**.

The latest evidence changes the roadmap in an important way:

1. a conservative global `open_low`↔`compact` model can learn useful signal (E3-D/E3-E);
2. that signal was not strong/stable enough for promotion under the later ultra-quality analysis;
3. blind repeat testing showed that the single global A/B “more natural” label was itself insufficiently repeatable for specialist activation;
4. repeated A/B subquestions did not solve the problem because they stayed perfectly collinear;
5. independent 1–5 scoring of each candidate did create component separation and an interpretable relation with the final overall preference.

Therefore the next stage must expand **independent component supervision**, not immediately train a new model.

## Immediate next step — new preregistered component-supervision expansion

The identifier and exact numeric gate must be frozen before collection. The required design should:

1. collect a substantially larger set of **new family-isolated** tasks using the S0-D-B elicitation order;
2. score candidate A independently, then candidate B independently, on:
   - `POSITION_COMFORT`;
   - `STRING_DISTRIBUTION` / topology;
   - `FINGER_SPREAD` / hand shape;
   - `OPEN_STRING_UTILITY`;
3. reveal A and B together only after independent scores are locked, then collect `OVERALL_PREFERENCE`;
4. keep physical validity deterministic and target-blind;
5. preregister a blind repeat subset to measure reliability of each component scale and the final overall choice;
6. preserve source family boundaries and prohibit Stage 7E/E3-E reuse;
7. decide **before model training** what evidence would be sufficient to open component-model training;
8. do not fit rubric weights or an arbiter on the 20-task S0-D-B pilot.

Only after the larger component corpus and reliability evidence are adequate should a separate training protocol decide whether to train one or more component analyzers.

## Key evidence state

### E3-D development

- result status: `POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`
- 399 decisive development events / 40 families
- event accuracy: 86.22%
- `always_open_low` baseline: 77.94%
- event delta: +8.27 pp
- macro-family delta: +7.84 pp
- compact precision / recall: 77.97% / 52.27%
- checkpoint retained: no

### E3-E untouched evaluation — now consumed

- 240 completed Teacher-GOLD tasks / 24 new families
- 237 decisive events / 3 equal-or-unsure
- accuracy: 70.04% vs `always_open_low` 55.27% → +14.77 pp
- macro-family accuracy: 73.45% vs 49.46% → +23.99 pp
- compact precision / recall: 90.70% / 36.79%
- family win / tie / loss: 16 / 7 / 1
- status: `POSITIVE_UNTOUCHED_SIGNAL_ELIGIBLE_FOR_PROMOTION_DESIGN`
- E3-E Teacher-GOLD is now permanently consumed for evaluation
- checkpoint retained: no
- promotion authorized: no

### S0-C reliability

- blind repeat tasks: 60, balanced 30 original `OPEN_LOW` / 30 original `COMPACT`
- exact semantic repeat agreement: 34/60 = 56.67%
- original `OPEN_LOW` repeat agreement: 14/30 = 46.67%
- original `COMPACT` repeat agreement: 20/30 = 66.67%
- Cohen kappa: 0.1333
- frozen ultra-reliability gate: **FAIL**
- repeat labels are forbidden from training/tuning/model selection

### S0-D-B independent scoring

- 20 new tasks / 20 distinct families
- 160 component scores + 20 overall preferences
- component separation in 16/40 option ratings
- at least one separated option in 13/20 tasks (65%)
- `OPEN_STRING_UTILITY` was the most distinct component
- position/string/finger remained strongly coupled
- sign of non-tied component difference matched overall preference on roughly 91.7–92.9% of eligible tasks
- historical overall preference matched 19/20, but this is **not** a reliability proof
- specialist training / rubric-weight fitting: not authorized

## Scientific rules that remain fixed

- Deterministic guitar physics owns physical validity.
- Learned components may operate only on already-valid candidates.
- `open_low` remains the conservative fallback/default proposal until a later promotion gate says otherwise.
- Stage 7E is permanently consumed/evaluation-only.
- E3-E Teacher-GOLD is permanently consumed/evaluation-only and may not be used for training, tuning, threshold/model selection, or a new validation claim.
- The original 556 E1/E2 decisive labels are consumed development evidence.
- The 399 decisive E3 Batch01 labels are development data, not untouched validation.
- S0-C repeat labels are reliability-only and forbidden from training/tuning/model selection.
- S0-D-A/B are design/calibration evidence; they do not automatically become a specialist training corpus.
- No component weights, specialist architecture, checkpoint, or production/shadow integration may be selected post hoc from the 20-task S0-D-B pilot.

## Development-control rule

Routine read-only analysis, branch creation, implementation inside an already approved bounded stage, tests, CI checks, and PR preparation do not require separate approval messages. Code/model-behavior merges, checkpoint retention/promotion, production/shadow integration, destructive history operations, and material scope expansions remain explicit gates.

Documentation/evidence-only maintenance explicitly requested by the user may be implemented and merged under that bounded authorization after the diff is verified and CI is green.
