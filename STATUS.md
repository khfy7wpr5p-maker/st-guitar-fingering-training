# Status

## Foundation

- Stage 0 — Safety + architecture baseline: ✅ implemented
- Stage 1 — Dataset Contract v1: ✅ implemented
- Stage 2 — Guitar Pro/MusicXML intake + normalizer: ✅ implemented
- Stage 3 — Physical validation + event extraction: ✅ implemented
- Stage 4 — Dataset Builder v1: ✅ implemented
- Stage 5 — First bounded single-note placement training: ✅ executed; no retained production checkpoint
- Stage 6 — Chord voicing specialist research: ✅ executed through stateless/context/rollout experiments

## Specialist-routing research

- Stage 7D-A — target-blind stateless specialist router: ✅ positive development evidence
- Stage 7E — untouched final evaluation: ✅ relative router advantage passed; corpus permanently consumed/evaluation-only
- Stage 7G-A → 7G-D — Teacher-GOLD contract, blind annotation, pairwise dataset: ✅ completed
  - original pairwise development corpus: 556 decisive / 40 families, plus 6 equal/unsure
  - first 38 richer full-candidate Teacher-GOLD choices remain a separate semantic label type
- Stage 7G-E1 — first Teacher-GOLD router: ✅ negative development result
  - 70.50% vs 77.88% `always_open_low`
  - no checkpoint
- Stage 7G-E2 — compact-preference diagnostic: ✅ completed
  - compact TP=66, FP=107
  - patterns remain hypothesis generators only

## E3 ergonomics research

- Stage 7G-E3-A/B/C — curriculum + 40-descriptor contract + Batch01: ✅ completed
  - 400/400 blind Teacher-GOLD responses
  - 399 decisive; `open_low=311`, `compact=88`, equal/unsure=1
- Stage 7G-E3-D-R1 — conservative `compact` gate development CV: ✅ positive development signal
  - accuracy 86.22% vs `always_open_low` 77.94% → +8.27 pp
  - macro-family delta +7.84 pp
  - compact precision / recall 77.97% / 52.27%
  - family win/tie/loss 22/13/5
  - checkpoint retained: no
- Stage 7G-E3-E — genuinely new family-disjoint untouched validation: ✅ completed and **consumed**
  - 240 responses / 24 new families; 237 decisive, 3 equal/unsure
  - accuracy 70.04% vs `always_open_low` 55.27% → +14.77 pp
  - macro-family accuracy 73.45% vs 49.46% → +23.99 pp
  - compact precision / recall 90.70% / 36.79%
  - family win/tie/loss 16/7/1
  - status: `POSITIVE_UNTOUCHED_SIGNAL_ELIGIBLE_FOR_PROMOTION_DESIGN`
  - E3-E Teacher-GOLD permanently forbidden for training/tuning/model/threshold selection
  - checkpoint retained: no; promotion authorized: no

## Quality/failure diagnostics

- Stage 7G-E3-R2 — visible-learning MLP: ✅ executed
  - clear learning signal
  - preregistered ultra-quality gate: 🔴 FAIL
  - no epoch/checkpoint selected post hoc
- Stage 7G-E3-S0 — five-fold scientific failure diagnostic: ✅ completed
  - recurrent overfit in 4/5 folds
  - substantial family/fold sensitivity
  - compact support thin
  - representation/regime-specific errors remain
- Stage 7G-E3-S0-B — event-level descriptive error attribution: ✅ completed
  - multi-axis bucket carried the majority of errors
  - position and topology strongest single-axis error groups
  - no causal specialist activation authorized

## Teacher-label reliability and decomposition

- Stage 7G-E3-S0-C — blind repeat reliability: 🔴 frozen reliability gate FAILED
  - 60 repeated tasks
  - exact semantic repeat agreement 34/60 = 56.67%
  - Cohen kappa 0.1333
  - repeat labels reliability-only and forbidden from training/tuning/model selection
- Stage 7G-E3-S0-D-A — five-part pairwise rubric: ✅ completed
  - 20 tasks
  - all five A/B judgments perfectly collinear on 20/20 tasks
  - conclusion: repeated pairwise subquestions are not independent specialist supervision
- Stage 7G-E3-S0-D-B — independent 1–5 per-option component scoring: ✅ completed
  - 20 new tasks / 20 distinct families
  - 160 component scores + 20 overall preferences
  - 13/20 tasks showed component separation in at least one option
  - `OPEN_STRING_UTILITY` most distinct
  - position/string/finger still strongly coupled
  - architecture design supported; specialist training and weight fitting not authorized

## Current stage — 7G-E3-S1-A

**➡ CURRENT: larger independent-component Teacher-GOLD reliability contract.**

S1-A freezes the next data-quality gate before any new component-model training.

### First-pass corpus

- 120 tasks total
- L1/L2/L3/L4 = 30/30/30/30
- maximum 4 tasks per family
- minimum 32 distinct families
- deterministic target-blind selection
- historical Teacher preference forbidden from selection
- original equal/unsure row + all S0-C/S0-D-A/S0-D-B exposed tasks excluded
- frozen 5-fold family assignment for possible later development evaluation
- four sealed 30-task sessions for fatigue control

### Frozen component rubric

Every candidate is scored independently on:

1. `POSITION_COMFORT`
2. `STRING_DISTRIBUTION`
3. `FINGER_SPREAD`
4. `OPEN_STRING_UTILITY`

A is scored and locked first; B is scored and locked second. Overall A/B/equal-or-unsure preference appears only after both independent option scores are locked.

### Blind repeat subset

- 48 tasks
- 12 per L1/L2/L3/L4
- maximum 2 repeat tasks per family
- selected and sealed before first-pass answers are opened
- minimum delay 24 hours after first-pass completion
- independently reblinded A/B sides and reordered tasks
- first-pass scores hidden
- 96 paired option ratings per component
- repeat labels permanently reliability-only

### Primary component reliability gate

Every one of the four components must satisfy:

- quadratic-weighted Cohen kappa >= 0.90
- exact score agreement >= 0.80
- within ±1 point agreement >= 0.98
- mean absolute score difference <= 0.35

Variance guard:

- at least 3 distinct first-pass scores on the repeat subset per component
- no single score >85% of ratings
- undefined kappa = fail/review, never pass

A pass opens only a **separate component-model training protocol design**. No model is trained or activated by S1-A.

### Secondary overall preference gate

Measured separately on 48 repeated task-level final choices:

- exact semantic repeat agreement >= 0.90
- three-way Cohen kappa >= 0.80
- repeat equal/unsure rate <= 0.10

If this fails while component reliability passes, component-model design may proceed but direct overall-preference / Guitaristic Arbiter target training remains closed.

## Immediate next controlled step

After S1-A is accepted on `main`, prepare **S1-B** only:

- deterministic reconstruction of prior exclusions;
- exact 120-task selection;
- exact 48-repeat subset selection;
- frozen family-fold assignment;
- teacher-facing four-session annotator;
- separate hidden audit;
- SHA-256 batch seals;
- stop before Teacher annotation for verification.

No training belongs in S1-B.

## Training quarantine / closed gates

- S1-A first-pass component labels: 🔒 quarantined until reliability PASS + separate merged training protocol
- S1-A repeat labels: 🚫 reliability-only, permanently forbidden as additional training rows
- S1-A overall preference labels: 🔒 descriptive only in S1-A
- New component specialist training: 🔒 closed
- Guitaristic Arbiter training: 🔒 closed
- Rubric-weight fitting: 🔒 closed
- Checkpoint retention/promotion: 🔒 closed
- Production / GuitarTab Engine shadow integration: 🔒 closed
- Stage 7E reuse: 🚫 forbidden
- E3-E reuse for training/tuning/model selection: 🚫 forbidden
