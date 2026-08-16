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
| 7G-E3-S0-D-B | Independent per-option 1–5 component scoring | ✅ separation in 13/20 tasks; architecture-design signal only |
| 7G-E3-S1-A | Larger component Teacher-GOLD + repeat-reliability contract | **CURRENT — preregistered before collection; no training** |
| 7G-E3-S1-B | Deterministic 120-task + 48-repeat batch generator / seal | next; not implemented |
| 7G-E3-S1-C | First-pass independent component Teacher-GOLD collection | future; blocked on S1-B seal |
| 7G-E3-S1-D | Blind decomposed-rubric repeat reliability | future; frozen gates defined by S1-A |
| Future | Component-specific analyzers | 🔒 not trained/activated |
| Future | Guitaristic Arbiter / Ranker | 🔒 design/training closed until component evidence is adequate |
| Future | Checkpoint retention | 🔒 closed |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | 🔒 future; blocked until a valid checkpoint/promotion gate passes |

## Current position

The project is now at **Stage 7G-E3-S1-A**. The architecture still keeps deterministic guitar physics as the authority, but the immediate research problem is no longer candidate validity or whether a global `open_low`↔`compact` model can learn anything. The current problem is whether guitarist preference can be decomposed into component labels that are repeatable enough to support high-quality specialist models.

S1-A freezes that data-quality test before any new responses are collected.

## S1-A frozen design

The first-pass component corpus will contain **120 tasks** from the same 40-family E3 development domain:

- L1=30
- L2=30
- L3=30
- L4=30
- maximum 4 tasks per family
- minimum 32 distinct families

The following are excluded before selection:

- the original 1 equal/unsure row;
- 60 S0-C repeat tasks;
- 20 S0-D-A pairwise-rubric tasks;
- 20 S0-D-B independent-scoring pilot tasks.

Selection is deterministic and target-blind. Historical Teacher preference may not influence selection.

Each task preserves the S0-D-B elicitation order:

1. score A alone;
2. lock A's four 1–5 component ratings;
3. score B alone;
4. lock B's four ratings;
5. only then collect the final A/B/equal-or-unsure overall preference.

The frozen component dimensions are:

- `POSITION_COMFORT`
- `STRING_DISTRIBUTION`
- `FINGER_SPREAD`
- `OPEN_STRING_UTILITY`

The 120 tasks are split into four sealed 30-task sessions for fatigue control.

## S1-A blind repeat design

Before first-pass answers are opened, **48 tasks** are frozen for later blind repeat:

- L1=12
- L2=12
- L3=12
- L4=12
- maximum 2 repeat tasks per family
- minimum delay after first-pass completion: 24 hours
- A/B independently reblinded
- first-pass answers hidden

Because every repeated task contains both A and B option scores, the repeat produces **96 paired option ratings per component**.

Repeat labels are reliability-only and may never be added as extra training rows.

## Frozen primary component-quality gate

Every component must satisfy all four conditions:

- quadratic-weighted Cohen kappa >= 0.90
- exact 1–5 score agreement >= 0.80
- within ±1 point agreement >= 0.98
- mean absolute score difference <= 0.35

A variance guard also requires at least three distinct first-pass score values on the repeat subset and no single score may exceed 85% of ratings for that component. Undefined kappa is a review/fail condition.

All four components must pass. A pass only opens a **new component-model training protocol design**. It does not authorize training, specialist activation, checkpoint retention, or integration.

## Frozen secondary overall-preference gate

The final A/B/equal-or-unsure decision is measured separately:

- exact semantic repeat agreement >= 0.90
- three-way Cohen kappa >= 0.80
- repeat equal-or-unsure rate <= 0.10

This gate does not control component-model eligibility. If component ratings are reliable but overall preference remains unstable, component training design may be opened while direct Guitaristic Arbiter target training stays closed.

## Immediate next step

Proceed only to **Stage 7G-E3-S1-B** after S1-A is accepted on `main`:

1. reconstruct the frozen prior-task exclusions deterministically;
2. select the exact 120 first-pass tasks without using Teacher answers;
3. assign frozen five-fold family-isolated development folds;
4. select the exact 48-task repeat subset before answers are opened;
5. independently reblind A/B sides;
6. generate the teacher-facing four-session interface and separate hidden internal audit;
7. seal manifest/audit SHA-256 identities;
8. stop before Teacher annotation and verify the seal.

No model training belongs in S1-B.

## Key evidence state

### E3-D development

- status: `POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`
- 399 decisive events / 40 families
- accuracy 86.22% vs baseline 77.94% → +8.27 pp
- macro-family delta +7.84 pp
- compact precision / recall 77.97% / 52.27%
- checkpoint retained: no

### E3-E untouched evaluation — consumed

- 240 responses / 24 new families; 237 decisive
- accuracy 70.04% vs baseline 55.27% → +14.77 pp
- macro-family delta +23.99 pp
- compact precision / recall 90.70% / 36.79%
- family win/tie/loss 16/7/1
- positive untouched signal, but no promotion/checkpoint
- E3-E Teacher-GOLD permanently evaluation-only

### S0-C reliability

- 60 blind repeats
- exact semantic repeat agreement 56.67%
- Cohen kappa 0.1333
- frozen gate FAIL
- repeat labels permanently reliability-only

### S0-D-B independent scoring

- 20 tasks / 20 distinct families
- 160 component scores + 20 overall preferences
- component separation on 13/20 tasks
- `OPEN_STRING_UTILITY` most distinct
- position/string/finger still strongly coupled
- architecture-design signal only; no specialist training/weight fitting

## Scientific rules that remain fixed

- Deterministic guitar physics owns physical validity.
- Learned components may operate only on already-valid candidates.
- `open_low` remains the conservative fallback/default proposal until a later promotion gate changes that under new evidence.
- Stage 7E is permanently consumed/evaluation-only.
- E3-E Teacher-GOLD is permanently consumed/evaluation-only and may not be used for training, tuning, threshold/model selection, or a new validation claim.
- The original 556 E1/E2 decisive labels are consumed development evidence.
- The 399 decisive E3 Batch01 labels are development data, not untouched validation.
- S0-C repeat labels are reliability-only and forbidden from training/tuning/model selection.
- S0-D-A/B remain design/calibration evidence; they do not automatically become a specialist training corpus.
- S1-A first-pass component labels remain quarantined until the primary reliability gate passes and a separate training protocol is merged.
- S1-A repeat labels are permanently reliability-only.
- No component weights, specialist architecture, checkpoint, or production/shadow integration may be selected in S1-A.

## Development-control rule

Routine read-only analysis, branch creation, implementation inside an approved bounded stage, tests, CI checks, and PR preparation do not require separate approval messages. Code/model-behavior merges, checkpoint retention/promotion, production/shadow integration, destructive history operations, and material scope expansions remain explicit gates.

Documentation/evidence-only work covered by the user's bounded approval may be merged after diff verification and green CI.
