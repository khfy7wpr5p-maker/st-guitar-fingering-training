# Stage 7G-E3-A — Curriculum Contract v1

## Status

**Protocol/contract only. No E3 model training, checkpoint retention, or production integration is authorized by this stage.**

Stage 7G-E3-A freezes the easy→hard curriculum and the target-blind ergonomics representation that Stage 7G-E3-B may later use to generate tasks. It follows the negative Stage 7G-E1 Teacher-GOLD router and the Stage 7G-E2 diagnostic.

## Scientific boundary

The existing 556 decisive Teacher-GOLD pairwise labels have already been used for E1 development and E2 diagnosis. They are therefore consumed development evidence, not a fresh benchmark for any E3 performance claim.

Stage 7G-E3-A does not:
- refit the E1 model;
- tune thresholds on those 556 labels;
- turn E2 correlations into validated preference rules;
- reuse Stage 7E;
- retain a checkpoint;
- authorize GuitarTab Engine integration.

## Authority hierarchy

1. Deterministic guitar physics owns physical validity.
2. Frozen `open_low` and `compact` specialists may propose only physically valid candidates.
3. Rule-derived curriculum targets may describe measurable geometry only.
4. Blind Teacher-GOLD is the only authority for the semantic question “which proposal is more guitaristic/natural?”
5. An E3 model may later choose `compact` only after a separately preregistered validation gate. Until then, `open_low` remains the research default.

## Frozen target-blind feature contract

The raw E3 record contains exactly **40 descriptors**.

### Current chord / candidate-set context — 7

- `chord_size`
- `pitch_span`
- `mean_pitch`
- `candidate_count`
- `candidate_open_fraction`
- `candidate_mean_positive_fret_mean`
- `candidate_positive_fret_span_mean`

### Proposal geometry — 11 per proposal

For both `open_low` and `compact`:

- `open_note_count`
- `fretted_note_count`
- `min_positive_fret`
- `mean_positive_fret`
- `max_fret`
- `positive_fret_span`
- `unique_positive_frets`
- `max_same_positive_fret_count`
- `string_span`
- `adjacent_string_ratio`
- `internal_string_gaps`

The geometry semantics intentionally match the Stage 7G-E2 diagnostic descriptors so the next experiment changes the representation contract explicitly rather than silently redefining prior measurements.

### Pairwise proposal deltas — 11

For every proposal descriptor, E3 includes:

`compact - open_low`

These fields answer “how does the alternative differ from the default?” without using teacher response, family identity, source identity, observed source TAB, or Stage 7E information.

## Frozen curriculum difficulty assignment

Difficulty assignment is target-blind. It depends only on chord size, deterministic candidate count, and proposal-geometry deltas.

The following raw differences count as a **strong contrast**:

| Descriptor | Absolute threshold |
|---|---:|
| `open_note_count` | 1 |
| `fretted_note_count` | 1 |
| `mean_positive_fret` | 3 frets |
| `positive_fret_span` | 2 frets |
| `string_span` | 2 strings |
| `internal_string_gaps` | 1 gap |

These thresholds are **curriculum routing thresholds only**. They are not teacher-preference rules and do not mean that the side satisfying one threshold is automatically “better”.

Level assignment is deterministic and first-match:

### L1 — easy structural contrasts

- 2-note chord;
- deterministic candidate count ≤ 12;
- at least 2 strong contrast axes.

Purpose: expose simple, high-signal geometry before subtle preference learning.

### L2 — basic ergonomics

- chord size ≤ 3;
- deterministic candidate count ≤ 20;
- at least 1 strong contrast axis;
- not already L1.

Purpose: isolate one or a few ergonomic dimensions.

### L3 — medium chord decisions

- chord size ≤ 4;
- deterministic candidate count ≤ 40;
- not already L1/L2.

Purpose: combine multiple weaker or mixed signals.

### L4 — hard specialist disagreements

All remaining valid `open_low != compact` disagreements.

Purpose: return to the difficult research problem after simpler structural supervision.

## Supervision provenance

Two supervision types are permanently distinct.

### `RULE_DERIVED_PROPERTY`

Allowed only in **L1/L2**.

It may answer factual geometry questions such as:

- which side has more open notes;
- which side has fewer fretted notes;
- which side has lower mean positive fret;
- which side has narrower positive-fret span;
- which side has smaller string span;
- which side has fewer internal string gaps.

Output values are only:

- `OPEN_LOW`
- `COMPACT`
- `EQUAL`

This supervision must never be described as Teacher-GOLD, “best fingering”, “most natural”, or teacher preference.

### `TEACHER_GOLD`

Allowed in L1–L4, but must be blind.

Frozen semantic target:

`pairwise_guitaristic_preference`

Allowed responses:

- `OPEN_LOW`
- `COMPACT`
- `EQUAL_OR_UNSURE`

`EQUAL_OR_UNSURE` must never be silently coerced into a binary class.

## Data independence

- Source families must not cross train/development/validation boundaries.
- The previous 556 decisive Teacher-GOLD labels remain development-consumed.
- The first 38 richer full-candidate selections remain a separate label type and must not be silently mixed with pairwise labels.
- Stage 7E is permanently forbidden for E3 training, tuning, calibration, threshold selection, feature selection, or validation.
- New performance claims require new family-disjoint Teacher-GOLD evidence. Reusing the old 556 may support exploratory development only.

## Planned E3-B generator boundary

A later generator may use only:

- pitches;
- explicit six-string tuning;
- deterministic physical candidates;
- frozen `open_low` and `compact` proposals;
- the 40 frozen E3 descriptors;
- the deterministic L1–L4 assignment.

No teacher response may affect task generation inside a sealed batch.

## Future evaluation metrics

The later model protocol must compare against `always_open_low`.

At minimum report:

- event-weighted Teacher-GOLD agreement;
- macro-family Teacher-GOLD agreement;
- compact precision;
- compact recall;
- compact false-positive count/rate;
- family win/tie/loss versus `always_open_low`.

This stage does not set a checkpoint-retention threshold. That gate remains closed until a later preregistered untouched Teacher-GOLD validation package.

## Closed gates

- E3-B curriculum generation: not started
- E3 teacher annotation pilot: not started
- E3 model fit: not started
- threshold/hyperparameter search: not authorized
- checkpoint retained: no
- production integration: no
- Stage 7E reuse: forbidden
- automatic learning from teacher/user correction: not enabled
