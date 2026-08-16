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
  - E3-E Teacher-GOLD is permanently forbidden for training/tuning/model/threshold selection
  - checkpoint retained: no; promotion authorized: no

## Quality/failure diagnostics after E3-E

- Stage 7G-E3-R2 — visible-learning MLP: ✅ executed
  - clear learning signal
  - preregistered ultra-quality gate: 🔴 FAIL
  - validation overfit became visible after the minimum-loss region
  - no epoch/checkpoint selected post hoc
- Stage 7G-E3-S0 — five-fold scientific failure diagnostic: ✅ completed
  - recurrent overfit in 4/5 folds
  - substantial family/fold sensitivity
  - compact support thin
  - representation/regime-specific errors remain
  - learning curve did not meet the preregistered “still rising” criterion
- Stage 7G-E3-S0-B — event-level descriptive error attribution: ✅ completed
  - multi-axis bucket carried the majority of errors
  - position and topology were the strongest single-axis error groups
  - no causal specialist activation authorized

## Teacher-label reliability and decomposition

- Stage 7G-E3-S0-C — blind repeat reliability: 🔴 frozen reliability gate FAILED
  - 60 repeated tasks, balanced 30 original `OPEN_LOW` / 30 original `COMPACT`
  - exact semantic repeat agreement: 34/60 = 56.67%
  - original `OPEN_LOW` repeat agreement: 14/30 = 46.67%
  - original `COMPACT` repeat agreement: 20/30 = 66.67%
  - Cohen kappa: 0.1333
  - repeat labels are reliability-only and forbidden from training/tuning/model selection
- Stage 7G-E3-S0-D-A — five-part pairwise rubric: ✅ completed
  - 20 tasks
  - position / string distribution / finger spread / open-string advantage / overall A/B choices were perfectly collinear on 20/20 tasks
  - conclusion: repeated pairwise subquestions are not independent specialist supervision
- Stage 7G-E3-S0-D-B — independent 1–5 per-option component scoring: ✅ completed
  - 20 new tasks / 20 distinct families
  - 160 component scores + 20 overall preferences
  - 16/40 options had non-identical component scores
  - 13/20 tasks showed component separation in at least one option
  - `OPEN_STRING_UTILITY` was the most distinct component
  - position/string/finger scores remained strongly coupled
  - architecture design supported; specialist training and weight fitting not authorized

## Current interpretation

The deterministic physical engine remains correct and authoritative. The research question has shifted from “can a global `open_low`↔`compact` gate learn preference?” to “how should guitarist preference be represented and supervised so that it is repeatable enough for high-quality component models?”

E3-D and E3-E prove that useful preference signal exists, but the later ultra-quality and reliability work shows that the old single A/B naturalness target is not sufficient for promotion. S0-D-B provides the first evidence that independent per-option component scoring can separate at least part of the decision structure.

## Current position

**➡ CURRENT: architecture-design / data-design gate before any new specialist training.**

The next scientific step must be a new preregistered stage that expands independent component Teacher-GOLD collection on new family-isolated tasks and includes blind repeat-reliability measurement under the decomposed rubric.

Only after that evidence is adequate may a separate protocol open:

- component-specific model training;
- learned or deterministic component aggregation;
- a Guitaristic Arbiter / Ranker;
- checkpoint retention.

## Closed gates

- New component specialist training: 🔒 closed
- Rubric-weight fitting: 🔒 closed
- Checkpoint retention/promotion: 🔒 closed
- Production / GuitarTab Engine shadow integration: 🔒 closed
- Stage 7E reuse: 🚫 forbidden
- E3-E reuse for training/tuning/model selection: 🚫 forbidden
- S0-C repeat-label training use: 🚫 forbidden
