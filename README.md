# st-guitar-fingering-training

Training and evaluation lab for guitar polyphony, voicing, string/fret selection, and left-hand fingering preference models.

## Current scope

The project is in Stage 7G-E3 research, but the current focus is no longer the original monolithic `open_low`↔`compact` gate. The deterministic physical engine remains authoritative, while current research is redesigning **guitaristic preference supervision** into independently scored ergonomic components before any new specialist training.

The current architecture is:

1. safe Guitar Pro/MusicXML intake and normalization;
2. deterministic physical validation and physically-valid candidate generation;
3. frozen proposal specialists such as `open_low` and `compact`;
4. target-blind guitar geometry/ergonomics descriptors;
5. independent Teacher-GOLD component judgments;
6. future component analyzers and a future Guitaristic Arbiter/Ranker, only after new reliability evidence.

Learned components may score/rank/route only among candidates already accepted by the deterministic physical engine. AI never creates or legitimizes physically impossible placements.

## What the latest research established

The earlier Teacher-GOLD router was negative: 70.50% event-weighted agreement versus 77.88% for `always_open_low`. E3-D later produced a positive family-isolated development signal, and E3-E produced a positive signal on new family-disjoint untouched Teacher-GOLD material. E3-E is now permanently consumed/evaluation-only; no checkpoint or promotion was authorized.

The subsequent quality work changed the immediate architecture direction:

- R2 learned but failed the preregistered ultra-quality gate;
- S0 showed recurrent overfit, family sensitivity, thin `compact` support, and regime-specific errors;
- S0-B showed many failures were multi-factor;
- S0-C blind repeat reliability of the single A/B “more natural” label failed badly: 34/60 exact repeat agreement, Cohen kappa 0.1333;
- S0-D-A decomposed the question into five pairwise subquestions, but all five stayed perfectly collinear on 20/20 tasks;
- S0-D-B scored A and B independently on 1–5 component scales before revealing the overall comparison and produced genuine component separation in 13/20 tasks.

The S0-D-B components are:

- `POSITION_COMFORT`;
- `STRING_DISTRIBUTION`;
- `FINGER_SPREAD`;
- `OPEN_STRING_UTILITY`;
- followed by `OVERALL_PREFERENCE` only after both candidates are independently scored.

`OPEN_STRING_UTILITY` was the most distinct component in the pilot. Position, string distribution, and finger/hand-spread judgments were still strongly coupled, so the repository does **not** yet claim that four separate learned specialists are required.

## Current position

**The next step is data/reliability design, not model training.**

A new preregistered stage should collect a larger family-isolated independent-component Teacher-GOLD corpus and include blind repeat testing under the decomposed rubric. Only after that evidence is adequate may a separate training protocol open component-specific models or a Guitaristic Arbiter.

No component specialist is currently trained or activated. No rubric weights are fitted. No production checkpoint is retained. GuitarTab Engine shadow/production integration remains closed.

## Consumed / protected evidence

- Stage 7E: permanently evaluation-only; never train/tune/revalidate on it.
- E3-E Teacher-GOLD: permanently consumed untouched evaluation evidence; forbidden for training/tuning/model/threshold selection.
- S0-C repeat labels: reliability evidence only; forbidden for training/tuning/model selection.
- S0-D-A/B pilot labels: architecture-design evidence; they are not automatically a specialist-training corpus.

The repository intentionally excludes OMR/PDF recognition, automatic learning from user feedback, rights-unclear raw corpora in Git, production GuitarTab Engine writes, and large retained checkpoints.

See `ARCHITECTURE.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `ROADMAP.md`, `STATUS.md`, `docs/STAGE_7G_E3_GUITAR_ERGONOMICS_CURRICULUM.md`, and `docs/COLAB_MANUAL_TRAINING_CONTROL.md`.
