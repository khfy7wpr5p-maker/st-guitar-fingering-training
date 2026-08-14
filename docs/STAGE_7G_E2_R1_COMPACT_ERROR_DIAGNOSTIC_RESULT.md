# Stage 7G-E2-R1 — compact preference error diagnostic result

Stage 7G-E2-R1 executes the merged diagnostic-only protocol. It does not fit or tune a new model. It regenerates the frozen Stage 7G-E1 family-isolated out-of-fold decisions and aggregates only error counts, fixed target-blind geometry strata, and family-level summaries.

## Main finding

The E1 router does learn some real compact-preference signal, but it selects `compact` too often.

Across 556 decisive Teacher-GOLD pairwise labels:

- teacher preferred `open_low`: 433
- teacher preferred `compact`: 123
- E1 predicted `compact`: 173
- compact true positives: 66
- compact false negatives: 57
- compact false positives: 107
- open-low true negatives: 326

Relative to `always_open_low`, E1 gains 66 correct decisions by recovering teacher-compact cases, but loses 107 correct decisions by switching teacher-open-low cases to compact. Net change: **-41 correct decisions**, matching the previously measured **-7.37 percentage-point** event-weighted accuracy delta.

## Fixed diagnostic strata

The strongest hypothesis-generating pattern is position reduction:

- when the compact proposal lowers mean positive fret by more than one fret, teacher compact preference is **42/50 = 84%**;
- when the two proposals' mean positive frets are within +/-1 fret, teacher compact preference is **34/169 = 20.1%**, and this region contains **70 of the 107 compact false positives**;
- when compact is more than one fret higher, teacher compact preference is only **47/337 = 13.9%**.

A second pattern concerns string topology:

- equal internal-string-gap geometry: OOF accuracy **87.6%**;
- compact has fewer internal gaps: **47.4%**;
- compact has more internal gaps: **58.6%**.

Internal-string-gap topology is not part of the Stage 7G-E1 15-feature space. This is only a future hypothesis candidate, not a validated feature-selection result.

## Family heterogeneity

The 40 families remain heterogeneous:

- open-low-majority families: 37
- compact-majority families: 2
- tie: 1
- family teacher-compact rate ranges from 0% to 78.6%
- family OOF accuracy ranges from 21.4% to 93.3%
- five families have OOF accuracy below 50%

## Interpretation

The failure is not that the router never recognizes compact preferences. It recognizes 66 of 123 such cases, but its false-positive cost is too high. The existing class-balanced logistic router is therefore unsuitable for promotion.

The observed geometry patterns may guide a later hypothesis, but they cannot be converted into a new rule or feature set and then re-evaluated on these same 556 labels as if the result were fresh evidence. Any next model hypothesis must use either new disjoint Teacher-GOLD data or a separately preregistered nested evaluation design.

## Scientific boundary

- new model fit: no
- feature selection: no
- threshold tuning: no
- hyperparameter search: no
- checkpoint retained: no
- production integration: no
- Stage 7E reused: no
- sequence context used: no
- raw teacher rows in Git: no
- event-level predictions in Git: no
