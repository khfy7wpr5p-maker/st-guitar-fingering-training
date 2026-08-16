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

## S1 independent-component reliability

- Stage 7G-E3-S1-A — reliability contract: ✅ preregistered before collection
- Stage 7G-E3-S1-B — exact batch generator / seal: ✅ completed
  - first pass: 120 tasks, L1/L2/L3/L4 = 30/30/30/30
  - 38 distinct families, maximum 4 tasks/family
  - repeat: 48 tasks, 12 per level
  - repeat subset selected before first-pass answers, 31 families, maximum 2/family
- Stage 7G-E3-S1-C — first-pass component Teacher-GOLD: ✅ 120/120 responses completed
  - component labels remain quarantined
  - no training authorized
- Stage 7G-E3-S1-D — **➡ CURRENT: sealed blind repeat reliability**
  - minimum 24-hour delay after first-pass completion
  - first-pass scores hidden
  - repeat A/B independently reblinded and reordered
  - repeat labels reliability-only

### Frozen component rubric

Every candidate is scored independently on:

1. `POSITION_COMFORT`
2. `STRING_DISTRIBUTION`
3. `FINGER_SPREAD`
4. `OPEN_STRING_UTILITY`

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

A pass opens only a **separate component-model training protocol design**. No model is trained or activated by S1-D.

### Secondary overall preference gate

Measured separately on 48 repeated task-level final choices:

- exact semantic repeat agreement >= 0.90
- three-way Cohen kappa >= 0.80
- repeat equal/unsure rate <= 0.10

If this fails while component reliability passes, component-model design may proceed but direct overall-preference / Base Guitaristic Arbiter target training remains closed.

## DCR-inspired future refinement

A DCR-inspired **Hard Guitaristic Error Refinement** layer is now recorded as a future design candidate only.

It is not active and may not be trained during S1. Its role, if later justified, would be to refine high-confidence wrong guitaristic decisions from a valid family-isolated base model while preserving the deterministic physical candidate boundary.

Prerequisites:

- S1 component reliability PASS;
- separate component-model training protocol;
- family-isolated component/base-arbiter predictions;
- preregistered hard-error definition and confidence rule;
- preregistered hard/ordinary sample mixture and refiner model;
- base-vs-base+refiner comparison before any untouched promotion design.

Stage 7E, E3-E, S0-C repeat labels, and S1 repeat labels remain forbidden as refiner training/tuning data.

See `docs/DCR_HARD_GUITARISTIC_ERROR_REFINEMENT.md`.

## Immediate next controlled step

Complete **S1-D only**:

- wait for the frozen minimum-delay gate;
- run the already sealed 48-task blind repeat;
- validate response integrity;
- calculate only the preregistered reliability metrics;
- declare PASS/FAIL/REVIEW without changing thresholds;
- stop before any component-model or refiner training.

## Training quarantine / closed gates

- S1 first-pass component labels: 🔒 quarantined until reliability PASS + separate merged training protocol
- S1 repeat labels: 🚫 reliability-only, permanently forbidden as additional training rows
- S1 overall preference labels: 🔒 descriptive/reliability role only at this stage
- New component specialist training: 🔒 closed
- Base Guitaristic Arbiter training: 🔒 closed
- DCR-inspired refiner training: 🔒 closed
- Hard-error threshold/sample-mixture selection: 🔒 closed
- Rubric-weight fitting: 🔒 closed
- Checkpoint retention/promotion: 🔒 closed
- Production / GuitarTab Engine shadow integration: 🔒 closed
- Stage 7E reuse: 🚫 forbidden
- E3-E reuse for training/tuning/model selection: 🚫 forbidden
