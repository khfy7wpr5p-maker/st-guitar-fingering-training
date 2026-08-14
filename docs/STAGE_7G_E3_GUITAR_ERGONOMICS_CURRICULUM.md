# Stage 7G-E3 — Guitar Ergonomics Curriculum

## Status

**Architecture / research plan only. Training has not started.**

Stage 7G-E3 follows the negative Stage 7G-E1 Teacher-GOLD router result and the Stage 7G-E2 compact-preference diagnostic. It does not retroactively change E1 or retune the same 556 decisive labels.

## Why E3 exists

The first Teacher-GOLD router learned some minority `compact` signal but underperformed the strongest simple baseline:

- E1 router event-weighted teacher agreement: **70.50%**
- `always_open_low`: **77.88%**
- delta: **−7.37 pp**

The E2 diagnostic showed why:

- true `compact` preferences recovered: **66**
- `compact` false positives introduced: **107**
- net correct decisions versus `always_open_low`: **−41**

The current failure is therefore not “the model learns nothing.” It is that the model switches away from the strong `open_low` default too easily and does not represent guitar ergonomics/string topology explicitly enough.

E2 also found hypothesis-generating structure on the consumed development labels. Most notably, when the `compact` proposal lowered mean positive fret by more than one fret, the teacher preferred `compact` on **42/50 (84%)** events. Internal-string-gap differences were also associated with much lower E1 OOF accuracy. These observations are not validated rules and must not be hard-coded as if independently proven.

## Research hypothesis

A model should learn guitaristic preference more efficiently if it is taught from **simple, obvious ergonomic contrasts toward hard specialist disagreements**, while explicitly representing the geometric difference between the two proposals.

The proposed decision architecture is intentionally conservative:

```text
physically-valid candidates
        ↓
frozen open_low + compact proposals
        ↓
explicit guitar ergonomics representation
        ↓
conservative compact detector
        ↓
if evidence for compact is insufficient → open_low
if evidence for compact is validated       → compact
```

`open_low` remains the default because current Teacher-GOLD evidence strongly favors it. E3 is not authorized to change that default without new validation.

## Curriculum levels

### L1 — Easy two-note contrasts

Purpose: learn obvious positional/physical preference structure before subtle chord decisions.

Typical properties:

- 2-note chords;
- small deterministic candidate sets;
- large separation in mean/min/max positive fret;
- obvious string-span or internal-gap differences;
- one proposal clearly simpler by the fixed geometry descriptors.

L1 may include rule-derived synthetic/pretraining labels, but those labels must be explicitly marked as rule-derived and must never be called Teacher-GOLD.

### L2 — Basic guitar ergonomics

Purpose: learn individual ergonomic dimensions.

Contrast families may isolate:

- open-string use;
- fretted-note count;
- minimum/mean/maximum positive fret;
- positive-fret span;
- same-positive-fret barre-like proxy;
- string span;
- adjacent-string ratio;
- internal string gaps.

Actual preference labels still require blind teacher responses when Teacher-GOLD claims are made.

### L3 — Medium chord decisions

Purpose: combine multiple ergonomic signals.

Typical properties:

- 3–4 note chords;
- several plausible deterministic candidates;
- moderate `open_low`/`compact` disagreement;
- no single trivial rule necessarily determines the answer.

### L4 — Hard specialist disagreements

Purpose: return to the real difficult problem only after the simpler representation is learned.

- frozen `open_low` vs `compact` disagreements;
- subtle ergonomic trade-offs;
- family-isolated Teacher-GOLD evaluation;
- directly comparable to the Stage 7G problem class, but new validation material must be independent where a fresh performance claim is made.

## Planned target-blind ergonomics representation

The following groups are candidates for a preregistered E3 feature contract.

### Current chord / candidate-set context

- chord size;
- pitch span;
- candidate count;
- candidate-set open-string prevalence;
- candidate-set position/span summaries.

### Proposal geometry

For both `open_low` and `compact`:

- open-note count;
- fretted-note count;
- minimum positive fret;
- mean positive fret;
- maximum fret;
- positive-fret span;
- unique positive-fret count;
- maximum notes sharing one positive fret (barre-like proxy only);
- string span;
- adjacent-string ratio;
- internal string gaps.

### Pairwise proposal deltas

Explicitly represent `compact - open_low` differences for the same descriptors. This allows the learner to model **how the alternative differs from the default**, rather than only describing each proposal independently.

No teacher response, source title, family identity, observed source TAB, or Stage 7E information may enter these features.

## Why simpler data may help

The existing pairwise corpus is intentionally disagreement-enriched: both specialists already produce plausible but different solutions. That is a difficult starting point for learning the underlying ergonomics.

A curriculum can lower sample complexity by first presenting high-signal examples where one ergonomic dimension is clear, then gradually introducing mixed trade-offs. This can accelerate representation learning, but it does **not** guarantee better real-world accuracy. The benefit must be verified on family-disjoint Teacher-GOLD data.

The project therefore separates two roles:

1. **rule-derived/synthetic curriculum data** — may teach physical/ergonomic structure cheaply;
2. **blind Teacher-GOLD data** — remains the authority for actual teacher preference.

## Planned stage breakdown

### 7G-E3-A — Curriculum and data contract

Freeze before collection/training:

- L1–L4 eligibility rules;
- source/family independence rules;
- label semantics;
- exact ergonomics descriptors;
- rule-derived versus Teacher-GOLD provenance;
- evaluation design;
- checkpoint gate remains closed.

### 7G-E3-B — Target-blind curriculum generator

Generate/select tasks using only:

- pitches;
- tuning;
- deterministic physical candidates;
- frozen specialist proposals;
- preregistered geometry descriptors.

No teacher labels may influence task generation within a sealed batch.

### 7G-E3-C — Teacher annotation pilot

Test whether simpler tasks improve annotation speed/consistency while preserving blind A/B or another preregistered teacher interface.

The pilot must report annotation counts and agreement/uncertainty evidence without automatically fitting a production model.

### 7G-E3-D — Nested/family-isolated development experiment

Because E2 already exposed candidate hypotheses on the current 556 labels, any reuse of those labels for model development must be under a separately preregistered nested design. A model may not be tuned on the outer validation fold.

A cleaner alternative is new family-disjoint curriculum Teacher-GOLD development data.

### 7G-E3-E — New untouched Teacher-GOLD validation

Before scoring:

- freeze the selected model/feature contract;
- freeze the `always_open_low` baseline comparison;
- freeze checkpoint-retention criteria;
- seal new family-disjoint validation material;
- prohibit Stage 7E reuse.

Only this later gate may authorize checkpoint retention. Production integration still requires a separate gate.

## Closed gates

At the time of this architecture update:

- E3 curriculum generation: **not started**
- new E3 teacher labels: **0**
- E3 model fit: **not started**
- E3 checkpoint retained: **no**
- production integration: **no**
- Stage 7E reuse: **forbidden**
- automatic learning from user correction: **not enabled**

## Success criterion

E3 is successful only if it produces a preregistered model that improves teacher-preference decisions beyond `always_open_low` on independent evidence without weakening the deterministic physical-validity boundary. Faster learning on easy curriculum examples alone is not sufficient.
