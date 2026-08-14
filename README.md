# st-guitar-fingering-training

Training and evaluation lab for guitar polyphony, voicing, string/fret selection, and left-hand fingering preference models.

## Current scope

The project has moved beyond the original single-note pilot into bounded chord-voicing and Teacher-GOLD preference research. Deterministic guitar physics remains authoritative: learned components may score or route only among physically valid string/fret candidates and never create or legitimize impossible placements.

The current research core is:

1. deterministic physically-valid candidate generation;
2. frozen stateless voicing specialists, with `open_low` as the strongest simple default and `compact` as the main alternative under study;
3. blind Teacher-GOLD pairwise preference supervision;
4. family-isolated evaluation of target-blind specialist routing;
5. diagnostic analysis before any new model or checkpoint is promoted.

The first real Teacher-GOLD router did **not** beat `always_open_low`: 70.50% event-weighted teacher agreement versus 77.88% for the baseline. Stage 7G-E2 traced the main loss to excessive `compact` selection. No Teacher-GOLD checkpoint is retained and production integration remains closed.

The next planned research package is **Stage 7G-E3 — Guitar Ergonomics Curriculum**. It will investigate simpler-to-harder curriculum data, explicit string-topology and left-hand-geometry descriptors, pairwise proposal-delta features, and a conservative `compact` detector that falls back to `open_low` unless there is sufficient evidence. This is an architecture/research plan only; E3 training has not started.

The repository intentionally excludes OMR/PDF recognition, production GuitarTab Engine writes, automatic learning from user feedback, rights-unclear raw corpora in Git, and large checkpoints.

See `ARCHITECTURE.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `ROADMAP.md`, `STATUS.md`, and `docs/STAGE_7G_E3_GUITAR_ERGONOMICS_CURRICULUM.md`.
