# st-guitar-fingering-training

Training and evaluation lab for guitar polyphony, voicing, string/fret selection, and left-hand fingering preference models.

## Current scope

The project is now in Stage 7G-E3, where deterministic physically valid guitar candidates are combined with blind Teacher-GOLD preference learning. Deterministic guitar physics remains authoritative: learned components may score or route only among candidates already accepted by the physical engine and never create or legitimize impossible placements.

The current research core is:

1. deterministic physically-valid candidate generation;
2. frozen stateless `open_low` and `compact` specialists;
3. a frozen 40-descriptor target-blind guitar-ergonomics representation;
4. blind pairwise Teacher-GOLD preference supervision;
5. a conservative `compact` gate with `open_low` as the default;
6. family-isolated nested development evaluation before any untouched validation or checkpoint decision.

The first Teacher-GOLD router was negative: 70.50% event-weighted agreement versus 77.88% for `always_open_low`. Stage 7G-E2 showed that excessive `compact` switching was the dominant error source: 66 true compact recoveries versus 107 false compact switches.

Stage 7G-E3 has since advanced through data and protocol preparation:

- E3-A curriculum/feature contract: merged;
- E3-B target-blind generator: merged;
- E3-B-R1 first sealed curriculum batch: 400 tasks across all 40 development families;
- E3-C blind Teacher-GOLD responses: 400/400 validated, with `open_low=311`, `compact=88`, `EQUAL_OR_UNSURE=1`;
- E3-D conservative training protocol: merged and frozen before fit.

The E3-D fit will use only the new 399 decisive E3 Batch01 Teacher-GOLD rows. The earlier 556 decisive E1/E2 rows are consumed hypothesis-development evidence and are excluded from the E3-D fit. Stage 7E remains permanently consumed and forbidden for training/tuning/new validation.

## Immediate next step

Prepare and manually execute Stage 7G-E3-D-R1 in Google Colab under the merged protocol:

`exact Git SHA → artifact SHA-256 preflight → family/leakage checks → STOP → manual TRAIN → frozen nested-CV evaluation → aggregate evidence export`

No E3-D model has been fitted yet. No threshold has been selected from results, no checkpoint is retained, and production/GuitarTab Engine integration remains closed.

The repository intentionally excludes OMR/PDF recognition, automatic learning from user feedback, rights-unclear raw corpora in Git, production GuitarTab Engine writes, and large retained checkpoints.

See `ARCHITECTURE.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `ROADMAP.md`, `STATUS.md`, `docs/STAGE_7G_E3_D_CONSERVATIVE_TRAINING_PROTOCOL.md`, and `docs/COLAB_MANUAL_TRAINING_CONTROL.md`.
