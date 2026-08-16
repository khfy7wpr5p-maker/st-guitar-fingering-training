# Architecture

## Current architecture map

```text
Guitar Pro / MusicXML source (quarantine)
        ↓
Safe XML intake
        ↓
Notation/TAB stream selection
        ↓
Tuning + transpose/pitch-semantics normalization
        ↓
Event/chord extraction
        ↓
Independent physical pitch ↔ string/fret validation
        ↓
Deterministic physically-valid candidate generator  ← AUTHORITATIVE PHYSICAL BOUNDARY
        ↓
Frozen proposal layer
  ├─ open_low  ← current fallback/default proposal
  ├─ compact   ← secondary proposal
  └─ mid/high/common-tone historical research alternatives
        ↓
Frozen target-blind representation
  ├─ chord/candidate-set context
  ├─ open/fretted-note geometry
  ├─ position/span proxies
  ├─ same-fret/barre-like proxy
  ├─ string span / adjacency / internal gaps
  └─ proposal-difference descriptors
        ↓
Historical preference-learning evidence
  ├─ E3-D conservative open_low↔compact gate: positive development CV
  ├─ E3-E new-family untouched evaluation: positive signal, now consumed
  ├─ R2 visible-learning MLP: learned but failed ultra-quality gate
  └─ S0/S0-B diagnostics: overfit + family sensitivity + multi-factor errors
        ↓
Teacher decision reliability redesign
  ├─ S0-C blind repeat of single A/B naturalness: reliability gate FAILED
  ├─ S0-D-A five repeated A/B subquestions: 20/20 perfectly collinear
  └─ S0-D-B independent per-option 1–5 scoring: component separation OBSERVED
        ↓
┌───────────────────────────────────────────────────────────────┐
│ CURRENT POSITION                                              │
│ Preserve independent component labels and expand them under   │
│ a new preregistered, family-isolated Teacher-GOLD stage.      │
│ Measure repeat reliability under the decomposed rubric before │
│ training or activating specialist component models.           │
└───────────────────────────────────────────────────────────────┘
        ↓
Future component-analysis layer (DESIGN CANDIDATE; NOT ACTIVE)
  ├─ Position Comfort analyzer
  ├─ String Distribution / Topology analyzer
  ├─ Finger / Hand Spread analyzer
  └─ Open-String Utility analyzer
        ↓
Future Guitaristic Arbiter / Ranker
  ├─ combines validated component evidence
  ├─ ranks only physically-valid candidates
  └─ falls back conservatively when evidence is insufficient
        ↓
Future preregistered checkpoint-retention gate
        ↓
Future GuitarTab Engine SHADOW integration
        ↓
Future MusicXML → GuitarTAB output integration
```

## What is implemented versus proposed

### Implemented / evidence-backed

- safe MusicXML/Guitar Pro intake and normalization;
- independent deterministic physical validation;
- deterministic physically-valid candidate generation;
- frozen `open_low` / `compact` proposal specialists and historical research alternatives;
- frozen 40-descriptor target-blind ergonomics representation;
- blind Teacher-GOLD collection and family-isolated evaluation machinery;
- E3-D positive development-CV evidence;
- E3-E positive untouched signal, with the E3-E Teacher-GOLD corpus now permanently consumed for evaluation;
- R2/S0/S0-B failure diagnostics;
- S0-C repeat-reliability evidence;
- S0-D-A and S0-D-B teacher-rubric experiments.

### Proposed only — not trained, activated, or promoted

- component-specific ergonomics models;
- learned weighting of component scores;
- a new Guitaristic Arbiter combining component models;
- a retained production checkpoint;
- GuitarTab Engine shadow/production integration.

## Why the architecture changed

The earlier architecture treated the hard decision mainly as a conservative `open_low` versus `compact` routing problem. E3-D showed that this representation can learn useful development-domain signal, and E3-E showed positive transfer on a genuinely new family-disjoint evaluation set. However, later quality analysis showed that this was not enough to justify promotion.

R2 failed the preregistered ultra-quality target and S0 found recurrent overfit, family sensitivity, thin `compact` support, and regime-specific errors. S0-B then showed that many errors were multi-factor rather than attributable to one simple rule.

The most important teacher-label finding came from S0-C. Repeating 60 previously answered A/B tasks under blind reordering produced only 34/60 exact semantic agreement (56.67%) and Cohen kappa 0.1333, far below the frozen reliability gate. Those repeat labels are reliability evidence only and are forbidden from training/tuning/model selection.

S0-D-A therefore decomposed “which is more natural?” into position, string distribution, finger spread, open-string advantage, and overall preference. But asking all five as repeated A/B choices did not create independent supervision: all five judgments were collinear on all 20 tasks.

S0-D-B changed the elicitation method. A and B were scored independently on 1–5 component scales before the overall A/B choice was shown. This produced genuine component separation: 16/40 option ratings had non-identical component scores and 13/20 tasks showed separation in at least one option. `OPEN_STRING_UTILITY` was the most distinct component, while position/string/finger scores remained strongly coupled. The result supports component-oriented architecture design but explicitly does **not** authorize specialist training, rubric-weight fitting, checkpoint retention, or integration.

## Authority boundary

1. Deterministic guitar rules own physical validity. AI may never manufacture, legalize, or select a placement outside the deterministic candidate set.
2. Learned specialists, analyzers, routers, arbiters, or future rankers may only operate on candidates that already passed deterministic physical validation.
3. Source XML pitch is not trusted blindly. Sounding pitch is independently recomputed from tuning + string + fret whenever observed technical placement exists.
4. Standard-notation and TAB staves representing the same event are one lineage, not two independent labels.
5. Written-guitar octave conventions are recorded explicitly and never silently mixed with sounding pitch.
6. Dataset families never cross a declared train/held-out split.
7. Observed source placement, rule-derived property supervision, blind pairwise Teacher-GOLD, full-candidate Teacher-GOLD, repeat-reliability labels, and independent 1–5 component scores are distinct supervision types and must not be silently mixed.
8. `open_low` remains the conservative fallback/default proposal. `compact` is a secondary proposal; neither specialist is allowed to override physical validity.
9. Stage 7E is permanently consumed/evaluation-only and forbidden for training, tuning, calibration, feature selection, or new validation.
10. E3-E Teacher-GOLD is also permanently consumed/evaluation-only. Its positive result opened design work only; it did not authorize promotion.
11. The original 556 decisive E1/E2 pairwise labels are consumed development evidence. They are not fresh validation.
12. E3 Batch01 contains 400 pairwise Teacher-GOLD responses from the 40-family development domain: 399 decisive and 1 equal/unsure. These are development evidence, not untouched validation.
13. S0-C repeat labels are reliability evidence only and may not be used for training, threshold tuning, or model selection.
14. S0-D-A/B pilot labels are architecture-design evidence. They are not automatically a specialist-training corpus; any future training use requires a new preregistered data/training protocol.
15. No simple or fitted weighting of the four S0-D-B component dimensions is authorized from the 20-task pilot.
16. A future component architecture must measure repeat reliability under the decomposed rubric before specialist activation.
17. Production/shadow integration remains closed until a separately preregistered checkpoint/promotion gate passes.

## Current learning state

The project has evidence that guitarist preference is learnable, but also evidence that a single global A/B “naturalness” target is too unstable to be treated as the sole specialist target. The current architecture therefore separates **physical validity**, **candidate proposals**, **guitaristic component judgments**, and a future **arbiter**.

The next executable scientific step is **not model training**. It is to preregister a larger, family-isolated independent-component Teacher-GOLD collection and a repeat-reliability test using the S0-D-B style rubric. Only after that evidence is adequate should component-model training or arbiter design be opened.
