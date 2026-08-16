# DCR-inspired hard guitaristic error refinement

## Source

Research inspiration:

Bowen Cheng, Yunchao Wei, Rogerio Feris, Jinjun Xiong, Wen-mei Hwu, Thomas Huang, Humphrey Shi, **“Decoupled Classification Refinement: Hard False Positive Suppression for Object Detection”**, arXiv:1810.04002 (2018).

The paper studies object detection, not guitar fingering. Its directly supported design idea is that a base system can be complemented by a separate classification-refinement network trained with emphasis on hard false positives. The guitar architecture below is therefore an **analogy and future research hypothesis**, not a claim established by the DCR paper.

## Project adaptation hypothesis

Possible future flow:

```text
Deterministic physically-valid candidate set
        ↓
Component analyzers
        ↓
Base Guitaristic Arbiter / Ranker
        ↓
Family-isolated out-of-fold error audit
        ↓
High-confidence wrong guitaristic decisions
        ↓
DCR-inspired Hard Guitaristic Error Refiner
        ↓
Refined ranking among the SAME physically-valid candidates
```

The refiner may never create, legalize, or select a placement that failed deterministic physical validation.

## Why this is potentially relevant

The project has already observed that a global preference model can learn useful signal while still showing family sensitivity, overfit, and regime-specific errors. A separate refinement stage could therefore be tested later as a way to focus model capacity on repeatable, high-confidence mistakes instead of forcing one model to solve every regime equally well.

Candidate future hard-error regimes include only hypotheses already suggested by project diagnostics, for example:

- position-conflict cases;
- string-topology / internal-gap cases;
- open-string utility conflicts;
- multi-axis cases where several ergonomic components disagree.

These are not specialist labels yet. They become eligible for model design only after the component Teacher-GOLD reliability gate is passed.

## Frozen safety boundaries

1. **No DCR/refinement training now.** S1 component reliability comes first.
2. Hard errors must be discovered from **family-isolated development predictions** (for example out-of-fold predictions), not from an untouched final-evaluation corpus.
3. Stage 7E and E3-E remain consumed/evaluation-only and may not be mined to train or tune a refiner.
4. S0-C repeat labels remain reliability-only and may not be reused as refiner training rows.
5. The currently sealed S1 repeat labels remain reliability-only.
6. Hard-error mining rules, confidence thresholds, sample mixture, model class, and evaluation gates must be preregistered before the corresponding labels/results are inspected for that experiment.
7. A refiner may only rerank candidates already accepted by the deterministic physical engine.
8. A refiner must have a conservative fallback to the base arbiter/ranker when its evidence is insufficient.
9. No checkpoint retention, shadow integration, or production use is authorized by this research note.

## Recommended experimental order

```text
S1 blind repeat reliability
        ↓ PASS
Separate component-model training protocol
        ↓
Component models trained manually in Colab
        ↓
Family-isolated OOF base-model predictions
        ↓
Preregistered hard-error definition
        ↓
DCR-inspired refinement experiment
        ↓
Family-isolated comparison:
base vs base+refiner
        ↓
Only if clearly positive:
new untouched promotion design
```

## Important methodological point

The future refiner should not automatically be trained on only hard mistakes. The DCR work motivates hard-example emphasis, but the exact mixture of hard errors, ordinary correct cases, and background/control cases must be fixed in advance for this project and tested scientifically. No post-hoc mixture selection is authorized.

## Current status

`DESIGN_CANDIDATE_ONLY_NO_TRAINING`
