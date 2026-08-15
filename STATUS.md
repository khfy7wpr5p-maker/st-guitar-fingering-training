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
- Stage 7G-E3-D-R1A — Colab execution harness: ✅ merged
  - loader/preflight/nested-CV execution code merged at `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`
- Stage 7G-E3-D-R1B — exact execution SHA pin: ✅ merged
  - Colab notebook pins `PINNED_EXECUTION_SHA` to R1A merge SHA `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`
- Stage 7G-E3-D-R1 — manual Colab development execution: ✅ completed with **positive development signal**
  - preflight: `PREFLIGHT_PASS_STOP_BEFORE_TRAIN`
  - exact user-exported result SHA-256: `5626a1ea70a2bc285d3585ec2f155eb86040ece6507a03dd6a477dd073ec67d3`
  - event accuracy: **86.22%** vs `always_open_low` **77.94%** → **+8.27 pp**
  - macro-family accuracy: **86.18%** vs baseline **78.34%** → **+7.84 pp**
  - compact precision / recall: **77.97% / 52.27%**
  - compact TP / FP / FN: **46 / 13 / 42**
  - family win / tie / loss: **22 / 13 / 5**
  - outer selected thresholds: `[0.5, 0.5, 0.6, 0.5, 0.5]`
  - frozen continuation status: `POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`
  - scientific scope remains **development CV, not untouched validation**
- Stage 7G-E3-E — new untouched family-disjoint Teacher-GOLD validation: 🟡 design opened
  - current substage: **E3-E-A new-family intake audit**
  - only genuinely new source families may enter
  - zero overlap required with prior Teacher-GOLD development families and consumed Stage 7E material
  - no E3-E Teacher-GOLD labels have been collected or observed
  - validation quota/pass criteria must be frozen before E3-E answers are opened
- Checkpoint retention: 🔒 closed
- Production / GuitarTab Engine integration: 🔒 closed

## Current interpretation

The architecture has moved from a symmetric `open_low`/`compact` router toward a precision-first conservative compact gate. `open_low` remains the default because Teacher-GOLD evidence showed that unnecessary compact switches were the dominant E1 failure mode.

Stage 7G-E3-D-R1 is the first frozen nested-CV test of the ergonomics-based conservative gate on the new 399-row Teacher-GOLD development batch. The preregistered continuation gate passed on every required condition: event and macro-family deltas were positive, pooled compact precision exceeded 0.5, compact TP exceeded FP, and family wins exceeded losses.

This is meaningful development evidence but is not a promotion result. The same 40-family development domain influenced earlier E1/E2/E3 reasoning, so it cannot establish untouched transfer. No checkpoint has been retained and no production or shadow integration is authorized.

The next controlled scientific step is Stage 7G-E3-E-A: acquire and audit genuinely new family-disjoint source material target-blindly, prove separation before annotation, then seal a validation batch and numeric pass/fail gate before any new Teacher-GOLD answers are opened.
