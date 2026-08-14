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
- Teacher-GOLD pairwise corpus: **556 decisive labels / 40 families**, plus 6 equal/unsure; first 38 richer full-candidate choices remain separate
- Stage 7G-E1 — first Teacher-GOLD router: ✅ executed, **negative development result**
  - router teacher agreement: **70.50%**
  - `always_open_low`: **77.88%**
  - event-weighted delta: **−7.37 pp**
  - checkpoint retained: **no**
- Stage 7G-E2 — compact-preference diagnostic: ✅ completed
  - compact true positives: **66**
  - compact false negatives: **57**
  - compact false positives: **107**
  - open-low true negatives: **326**
  - net correct decisions vs `always_open_low`: **−41**
  - strongest hypothesis-generating pattern: when `compact` lowers mean positive fret by more than one fret, teacher compact preference was **42/50 (84%)** on the consumed development set
  - string-topology/internal-gap differences also correlate with error structure, but are not validated routing rules
- Stage 7G-E3 — Guitar Ergonomics Curriculum: 🟡 **next architecture package; training not started**
- Checkpoint retention: 🔒 closed
- Production / GuitarTab Engine integration: 🔒 closed

## Current interpretation

The system is learning meaningful structure, but the learning objective has changed. Earlier corpus-behavior routing showed a repeatable relative advantage; real Teacher-GOLD preference is more conservative and strongly favors `open_low` unless `compact` provides a clear ergonomic benefit. The current E1 model therefore over-selects `compact`.

The next development step is not post-hoc threshold tuning on the same 556 labels. Stage 7G-E3 will test a simpler-to-harder curriculum, explicit guitar ergonomics/string topology, and a conservative `compact` detector under a separately preregistered evaluation design.
