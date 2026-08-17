# st-guitar-fingering-training

Training and evaluation lab for guitar polyphony, voicing, string/fret selection, and guitaristic fingering preference models.

## Project purpose

The project does **not** ask AI to decide whether a guitar placement is physically possible. Physical validity remains deterministic and authoritative.

The intended pipeline is:

1. safe Guitar Pro / MusicXML intake and normalization;
2. deterministic physical pitch ↔ string/fret validation;
3. deterministic physically-valid candidate generation;
4. frozen proposal specialists such as `open_low` and `compact`;
5. target-blind guitar geometry / ergonomics descriptors;
6. independently scored Teacher-GOLD ergonomic components;
7. future component analyzers;
8. future Base Guitaristic Arbiter / Ranker;
9. optional future DCR-inspired Hard Guitaristic Error Refinement;
10. separately gated checkpoint retention and GuitarTab Engine shadow integration.

Learned components may score, rank, route, or refine only candidates already accepted by the deterministic physical engine. AI never creates, legitimizes, or selects a physically impossible placement.

## What the research established

The original single global `open_low` ↔ `compact` decision was useful as a research target but is no longer treated as sufficient supervision by itself.

Important evidence:

- Stage 7G-E3-D-R1 produced a positive family-isolated development signal: 86.22% event accuracy versus 77.94% for `always_open_low`, with +7.84 pp macro-family delta.
- Stage 7G-E3-E produced a positive signal on genuinely new family-disjoint untouched Teacher-GOLD material: 70.04% accuracy versus 55.27% `always_open_low`, +23.99 pp macro-family delta, and 90.70% compact precision. E3-E is now permanently consumed/evaluation-only and authorized no checkpoint or promotion.
- R2 learned but failed the preregistered ultra-quality gate.
- S0/S0-B showed recurrent overfit, family sensitivity, thin `compact` support, regime-specific errors, and many multi-factor failures.
- S0-C showed that the single A/B “more natural” label was not repeatable enough: 34/60 exact repeat agreement and Cohen kappa 0.1333.
- S0-D-A decomposed the judgment into multiple pairwise questions, but all five remained perfectly collinear on 20/20 tasks.
- S0-D-B changed the elicitation method: A and B were scored independently on 1–5 component scales before the overall choice. This produced genuine component separation in 13/20 tasks.

The current component rubric is:

- `POSITION_COMFORT`
- `STRING_DISTRIBUTION`
- `FINGER_SPREAD`
- `OPEN_STRING_UTILITY`

`OPEN_STRING_UTILITY` was the most distinct component in the pilot. Position, string distribution, and finger spread remained strongly coupled, so the repository does **not** yet claim that four separate learned specialists are required.

## Current position — Stage 7G-E3-S1-D

S1 scaled the independent-component rubric under a preregistered reliability contract:

- S1-A reliability protocol: ✅ frozen before collection;
- S1-B exact first-pass / repeat batches: ✅ generated and sealed;
- S1-C first-pass Teacher-GOLD: ✅ 120/120 responses completed;
- S1-D blind repeat reliability: **CURRENT**.

The S1 first-pass set contains 120 tasks, balanced L1–L4 at 30 each. Before first-pass answers were opened, a 48-task blind repeat subset was sealed, balanced at 12 tasks per level.

The immediate scientific question is whether the four independent component ratings are repeatable enough to support future learned component models.

Every component must satisfy all frozen primary reliability conditions:

- quadratic-weighted Cohen kappa >= 0.90;
- exact 1–5 score agreement >= 0.80;
- within ±1 point agreement >= 0.98;
- mean absolute score difference <= 0.35;
- variance guard: at least three distinct first-pass scores and no single score above 85% of ratings.

The final A/B/equal-or-unsure choice is evaluated separately with its own repeat gate.

**No component model is currently trained or activated. No component weights are fitted. No Base Guitaristic Arbiter is trained. No DCR-inspired refiner is trained. No production checkpoint is retained. GuitarTab Engine shadow/production integration remains closed.**

A S1-D component-reliability PASS would open only a **separate preregistered component-model training protocol design**. It would not itself authorize training, checkpoint retention, or integration.

## Future DCR-inspired refinement

The architecture records a future **Hard Guitaristic Error Refinement** layer inspired by the decoupled-classification / hard-error idea from DCR research.

This is a project-specific research hypothesis, not evidence that DCR is already proven for guitar fingering.

If later justified, the refiner would:

- operate only after a valid family-isolated Base Guitaristic Arbiter exists;
- identify high-confidence wrong guitaristic decisions from preregistered development predictions;
- rerank only the same physically-valid candidate set;
- remain bypassable so the base arbiter is the conservative fallback.

Stage 7E, E3-E, S0-C repeat labels, and S1 repeat labels may not be mined for refiner training or tuning.

## Protected evidence

- Stage 7E: permanently evaluation-only; never train/tune/revalidate on it.
- E3-E Teacher-GOLD: permanently consumed untouched evaluation evidence; forbidden for training, tuning, threshold/model selection, or another fresh validation claim.
- Original 556 decisive E1/E2 labels: consumed development evidence.
- E3 Batch01: 400 Teacher-GOLD responses from the development domain, 399 decisive and 1 equal/unsure.
- S0-C repeat labels: reliability-only; forbidden for training/tuning/model selection.
- S0-D-A/B pilot labels: architecture-design/calibration evidence unless a later protocol explicitly admits them.
- S1 first-pass component labels: quarantined until S1-D reliability PASS and a separate merged training protocol.
- S1 repeat labels: permanently reliability-only and may not be added as extra training rows.

The repository intentionally excludes OMR/PDF recognition, automatic learning from user feedback, rights-unclear raw corpora in Git, production GuitarTab Engine writes, and large retained checkpoints.

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `docs/DCR_HARD_GUITARISTIC_ERROR_REFINEMENT.md`, `docs/STAGE_7G_E3_GUITAR_ERGONOMICS_CURRICULUM.md`, and `docs/COLAB_MANUAL_TRAINING_CONTROL.md`.
