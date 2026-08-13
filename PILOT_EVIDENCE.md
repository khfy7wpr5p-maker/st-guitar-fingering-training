# First Bounded Training Evidence

Status: **EXECUTED — infrastructure validated; learned-quality advantage NOT demonstrated**.

## Scope

This was a local, bounded observed-placement ranking pilot using seven user-supplied Guitar Pro/MusicXML files. The source files remained outside Git and are not admitted as teacher-GOLD or production training data. No checkpoint was retained.

## Intake / dataset evidence

- exact source files processed: 7;
- broad musical families after leakage grouping: 6;
- normalized and physically validated guitar events: 466;
- validated chord/polyphonic events extracted but withheld from this first model: 183;
- one source stream used consistent written-guitar pitch at +12 semitones and was normalized explicitly;
- six source streams matched physical sounding pitch exactly;
- two exact Guitar Pro duplicate-note export artifacts were collapsed only because pitch/string/fret were identical;
- conflicting same-string simultaneous placements remain fail-closed.

## First training task

Task: rank physically valid single-note `(string, fret)` candidates and reproduce the corpus-observed placement.

This is **behavior cloning of observed corpus choices**, not proof of pedagogical preference and not left-hand fingering training.

Family-level split:

- train families: 4 broad families;
- validation families: 2 broad families;
- train single-note events: 159;
- validation single-note events: 124;
- train candidate rows: 680;
- validation candidate rows: 466.

No previous-event ground-truth string/fret labels were used as model features. Related excerpts of the same work were kept in one family and could not cross train/validation.

## Model result

Baseline model: deterministic-seed logistic candidate ranker.

- validation Top-1 observed-placement accuracy: `0.7580645161290323`;
- validation mean reciprocal rank: `0.875`.

## Mandatory trivial-baseline comparison

On the same validation events, the deterministic heuristic **choose the physically valid candidate with the lowest fret** achieved:

- Top-1 accuracy: `1.0`;
- MRR: `1.0`.

Family leave-one-out diagnostic across the six broad families:

- macro learned-model Top-1: `0.7852136181575434`;
- macro learned-model MRR: `0.8912840577560204`;
- macro lowest-fret heuristic Top-1: `0.7852136181575434`.

Therefore the learned model demonstrated **no advantage over the simple deterministic lowest-fret rule** on this pilot corpus.

## Decision

The first-training infrastructure gate is successful: source normalization, physical validation, family isolation, candidate generation, bounded fitting, and evaluation all executed end to end.

The model-quality gate is **not passed**. This pilot must not be promoted, integrated, or described as an intelligent fingering model. The evidence instead shows that the current corpus has strong deterministic placement bias and is insufficient by itself to teach nuanced guitar preference.

Before a later chord/voicing or teacher-preference model, the dataset must add candidate diversity and explicit teacher-GOLD preference/ranking labels. A true sealed benchmark also requires fresh material that was not inspected during development.
