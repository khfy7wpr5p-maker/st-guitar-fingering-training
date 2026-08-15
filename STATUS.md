# Status

- Stage 0 — Safety + architecture baseline: ✅ implemented
- Stage 1 — Dataset Contract v1: ✅ implemented
- Stage 2 — Guitar Pro/MusicXML intake + normalizer: ✅ implemented
- Stage 3 — Physical validation + event extraction: ✅ implemented
- Stage 4 — Dataset Builder v1: ✅ implemented
- Stage 5 — First bounded single-note placement training: ✅ executed; no retained production checkpoint
- Stage 6 — Chord voicing specialist research: ✅ executed through stateless/context/rollout experiments
- Stage 7D-A — target-blind stateless specialist router: ✅ positive development evidence
- Stage 7E — untouched final evaluation: ✅ relative router advantage passed; corpus permanently consumed/evaluation-only
- Stage 7G-A → 7G-D — Teacher-GOLD contract, blind annotation, pairwise dataset: ✅ completed
  - original pairwise Teacher-GOLD development corpus: **556 decisive / 40 families**, plus 6 equal/unsure
  - first 38 richer full-candidate Teacher-GOLD choices remain a separate semantic label type
- Stage 7G-E1 — first Teacher-GOLD router: ✅ executed, **negative development result**
  - router agreement: **70.50%**
  - `always_open_low`: **77.88%**
  - event-weighted delta: **−7.37 pp**
  - checkpoint retained: **no**
- Stage 7G-E2 — compact-preference diagnostic: ✅ completed
  - compact true positives: **66**
  - compact false positives: **107**
  - net correct decisions vs `always_open_low`: **−41**
  - diagnostic patterns are hypothesis generators only, not validated routing rules
- Stage 7G-E3-A — Guitar Ergonomics Curriculum contract: ✅ merged
  - frozen target-blind representation: **40 descriptors**
  - L1→L4 curriculum assignment is target-blind
  - blind Teacher-GOLD remains the only authority for guitaristic preference
- Stage 7G-E3-B — target-blind curriculum generator: ✅ merged
- Stage 7G-E3-B-R1 — first sealed curriculum batch: ✅ completed
  - remaining unlabeled `open_low`↔`compact` disagreements after prior-task exclusion: **5,026**
  - inventory: L1=788, L2=1,482, L3=1,202, L4=1,554
  - sealed quota: L1=140, L2=120, L3=80, L4=60 = **400 tasks**
  - all **40 development families** represented; overlap with previous 600 tasks = 0
  - external package SHA-256: `e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`
- Stage 7G-E3-C — Teacher-GOLD Batch01 response seal: ✅ completed
  - validation: **400/400**, exact task-set match, 0 duplicate/missing/invalid
  - decoded preference: `open_low=311`, `compact=88`, `EQUAL_OR_UNSURE=1`
  - decisive rows: **399**
  - L1 compact rate: **6.43%**; L4 compact rate: **50.85%**
  - source families overlap prior development families, therefore this is **development evidence, not untouched validation**
- Stage 7G-E3-D — conservative compact-gate training protocol: ✅ merged and frozen
  - default decision: `OPEN_LOW`
  - fit corpus: only the new E3 Batch01 **399 decisive** Teacher-GOLD rows
  - old E1/E2 556 decisive rows are excluded from the E3-D fit
  - model: `StandardScaler` + `LogisticRegression(C=1, class_weight=None, lbfgs)`
  - validation: 5-fold outer / 4-fold inner family-isolated nested development CV
  - compact threshold candidates: `[0.50, 0.60, 0.70, 0.80, 0.90, 0.95]`, selected on inner OOF only
  - if no threshold satisfies the frozen precision/baseline-safety gate: `NO_SWITCH → OPEN_LOW`
  - model fit: **not yet executed**
- Current next execution — Stage 7G-E3-D-R1 manual Colab development run: 🟡 ready to prepare/run
  - pin exact merged Git SHA
  - verify external artifact hashes and split/leakage preflight
  - STOP before fit
  - user manually runs TRAIN cell
  - frozen nested-CV evaluation only
  - export aggregate evidence JSON
- Stage 7G-E3-E — new untouched family-disjoint Teacher-GOLD validation: ⏳ future; only designed if E3-D development gate is positive
- Checkpoint retention: 🔒 closed
- Production / GuitarTab Engine integration: 🔒 closed

## Current interpretation

The architecture has moved from a symmetric `open_low`/`compact` router toward a precision-first conservative compact gate. `open_low` remains the default because Teacher-GOLD evidence shows that unnecessary compact switches were the dominant E1 failure mode.

The new 400-task curriculum batch supplies additional blind Teacher-GOLD development evidence and shows the intended easy→hard pattern: L1 strongly favors `open_low`, while L4 is nearly balanced. This supports the curriculum as a useful development structure, but it is not a fresh final benchmark because the same 40 source families overlap earlier development work.

The training protocol is now frozen before any E3-D fit. No threshold has been selected, no E3-D model has been trained, no checkpoint is retained, and no production integration is authorized.
