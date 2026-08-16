# Stage 7G-E3 — Guitar Ergonomics Curriculum

## Status

**E3 curriculum/model research has been executed through E3-E and the subsequent R2/S0/S0-B/S0-C/S0-D diagnostics. The active architecture question is now component-supervision design, not whether E3-B generation or E3-D training should start.**

This document preserves the original E3 rationale while recording how the architecture evolved after the experiments.

## Why E3 existed

The first Teacher-GOLD router underperformed the strongest simple baseline:

- E1 router event-weighted teacher agreement: 70.50%
- `always_open_low`: 77.88%
- delta: −7.37 pp

E2 showed the dominant failure mode:

- true `compact` preferences recovered: 66
- `compact` false positives introduced: 107
- net correct decisions versus `always_open_low`: −41

The original E3 hypothesis was that explicit target-blind ergonomics descriptors plus a simple-to-hard curriculum could reduce unnecessary `compact` switches while preserving `open_low` as the default.

## E3 curriculum contract

E3-A froze:

- L1–L4 curriculum levels;
- family/split rules;
- rule-derived versus Teacher-GOLD provenance;
- a 40-descriptor target-blind representation;
- no Stage 7E reuse;
- no physical-validity authority for learned models.

E3-B generated target-blind tasks. E3-C collected a new 400-task Teacher-GOLD development batch:

- 400/400 complete;
- 399 decisive;
- `open_low=311`, `compact=88`, equal/unsure=1;
- all 40 development families represented.

## E3-D result

The frozen conservative `open_low`↔`compact` development protocol was executed manually in Colab.

Result:

- event accuracy: 86.22% vs `always_open_low` 77.94% → +8.27 pp;
- macro-family delta: +7.84 pp;
- compact precision / recall: 77.97% / 52.27%;
- family win / tie / loss: 22 / 13 / 5;
- continuation status: `POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`;
- checkpoint retained: no.

This was development CV only.

## E3-E result — consumed untouched validation

A new family-disjoint Teacher-GOLD validation set was constructed and sealed before annotation. The final evaluation used:

- 240 completed tasks;
- 24 new evaluable families;
- 237 decisive events / 3 equal-or-unsure;
- no E3-E threshold search or training.

Untouched result:

- accuracy: 70.04% vs `always_open_low` 55.27% → +14.77 pp;
- macro-family accuracy: 73.45% vs 49.46% → +23.99 pp;
- compact precision / recall: 90.70% / 36.79%;
- family win / tie / loss: 16 / 7 / 1;
- status: `POSITIVE_UNTOUCHED_SIGNAL_ELIGIBLE_FOR_PROMOTION_DESIGN`.

E3-E did **not** authorize promotion. Its Teacher-GOLD labels are now permanently consumed/evaluation-only and may not be used for training, tuning, threshold/model selection, or a new fresh-validation claim.

## Why the architecture did not stop at E3-E

A positive untouched result was not sufficient for the user's near-perfect quality requirement. R2 was introduced as a visible-learning diagnostic using the same 40-feature family and a small MLP. It learned, but failed the preregistered ultra-quality gate and showed late overfit.

S0 then tested why the model failed across five family-isolated folds. The diagnostic found:

- recurrent overfit in 4/5 folds;
- substantial family/fold variance;
- thin `compact` support;
- regime-specific errors;
- no preregistered evidence that simply adding more of the same data would solve the problem.

S0-B attributed errors descriptively and found that multi-axis cases dominated, with position and string topology the strongest single-axis error groups. This supported decomposition as a design hypothesis, not as activated specialists.

## Teacher-label reliability changed the target design

### S0-C — blind repeat reliability

The project repeated 60 previously answered pairwise tasks under fresh blind A/B presentation.

- exact semantic repeat agreement: 34/60 = 56.67%;
- original `OPEN_LOW` repeat agreement: 14/30 = 46.67%;
- original `COMPACT` repeat agreement: 20/30 = 66.67%;
- Cohen kappa: 0.1333;
- frozen ultra-reliability gate: FAIL.

This does not prove that the teacher is “wrong.” It shows that the single global pairwise question “which fingering is more natural?” is not stable enough, under this protocol, to be the sole target for high-quality specialist activation.

S0-C repeat labels are reliability evidence only and are forbidden from training/tuning/model selection.

### S0-D-A — repeated pairwise decomposition

The question was split into:

- position comfort;
- string distribution;
- finger spread / hand shape;
- open-string advantage;
- overall preference.

But asking each as another A/B choice did not provide independent supervision: all five judgments were collinear on all 20 tasks.

### S0-D-B — independent per-option scoring

The elicitation was changed so that candidate A was scored alone, then B alone, on 1–5 scales before the final A/B overall preference was shown.

Dimensions:

- `POSITION_COMFORT`;
- `STRING_DISTRIBUTION`;
- `FINGER_SPREAD`;
- `OPEN_STRING_UTILITY`.

Pilot evidence:

- 20 new tasks / 20 distinct families;
- 160 component ratings + 20 overall choices;
- 16/40 option ratings had non-identical component scores;
- 13/20 tasks showed component separation in at least one option;
- `OPEN_STRING_UTILITY` was the most distinct dimension;
- position/string/finger remained strongly coupled;
- non-tied component-score differences aligned descriptively with final overall preference on roughly 91.7–92.9% of eligible tasks.

This is the first E3-era evidence that the supervision format itself can expose substructure. It is still a small architecture-design pilot and does not authorize fitted weights, component specialist training, or an arbiter.

## Current successor architecture

```text
physically-valid candidates
        ↓
frozen proposal layer (open_low / compact)
        ↓
target-blind candidate descriptors
        ↓
independent component supervision
  ├─ position comfort
  ├─ string distribution / topology
  ├─ finger / hand spread
  └─ open-string utility
        ↓
CURRENT: larger family-isolated component Teacher-GOLD
         + repeat reliability under the decomposed rubric
        ↓
future component analyzers (only if evidence supports them)
        ↓
future Guitaristic Arbiter / Ranker
        ↓
future checkpoint gate
```

`open_low` remains the conservative fallback/default proposal. The component layer is a **design candidate**, not an activated model architecture.

## Next scientific requirement

Before any new component-model training:

1. preregister a larger independent-component Teacher-GOLD collection;
2. use new family-isolated tasks;
3. preserve the A-alone → B-alone → overall-choice elicitation order;
4. preregister a blind repeat subset and reliability metrics;
5. decide before results what reliability evidence opens model training;
6. keep Stage 7E and E3-E permanently excluded;
7. do not learn component weights from the S0-D-B 20-task pilot;
8. keep deterministic physical validation authoritative.

## Closed gates

- new component specialist training: closed;
- learned rubric weights: closed;
- Guitaristic Arbiter training: closed;
- checkpoint retention: closed;
- production/shadow integration: closed;
- Stage 7E reuse: forbidden;
- E3-E reuse for training/tuning/model selection: forbidden;
- automatic learning from user correction: not enabled.
