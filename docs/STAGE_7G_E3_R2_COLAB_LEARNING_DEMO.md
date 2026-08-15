# Stage 7G-E3-R2 — Colab visible learning demonstration

## Purpose

This is a new **development-only** experiment whose purpose is to make model learning visible to the human operator in Colab.

It is not a replay of the E3-E untouched validation and it is not a promotion gate.

The operator must be able to see, after manually running the TRAIN cell:

- Train Loss by epoch;
- Validation Loss by epoch;
- Validation Macro-F1 by epoch;
- validation balanced accuracy;
- COMPACT precision and recall;
- TP / FP / FN / TN;
- always-OPEN_LOW baseline;
- final accuracy and Macro-F1 gains versus that baseline;
- train/validation learning curves.

`LocF1@2px` is deliberately reported as **not applicable** because this model predicts `OPEN_LOW` versus `COMPACT` guitaristic preference. It does not predict image pixel locations.

## Data boundary

R2 uses only the already-consumed E3 development Teacher-GOLD batch:

- 400 sealed tasks;
- 399 decisive binary rows;
- 1 `EQUAL_OR_UNSURE` row excluded from binary training;
- 40 AnimeTAB development families;
- exact frozen 40 target-blind ergonomics features.

The 240 E3-E Teacher-GOLD responses are **not accepted as an input** to the R2 training API and must not be uploaded to the notebook.

Stage7E is forbidden.

## Source reconstruction

The original external E3-B-R1 ZIP is no longer required for this demonstration.

The Colab preflight reconstructs the same label-free development feature rows from the 40 pinned AnimeTAB source identities in repository evidence. Source bytes are downloaded from `amamiya-yuuko/AnimeTAB` at commit:

`18c0993cbe0a0948cbf0b7768bcb09ff81c23a9a`

Every downloaded source must match its repository-sealed SHA-256 before parsing.

Frozen target-free parsing remains:

- part `P1`;
- staff `2`;
- `sounding_exact`;
- tuning MIDI `[64, 59, 55, 50, 45, 40]`.

The frozen Stage7B `open_low` and `compact` specialists are reconstructed in memory. Physical candidates continue to come only from deterministic `valid_chord_voicings()`.

The preflight must reproduce:

- 5,626 `open_low != compact` development disagreements;
- exact 400 task-ID-set digest `d7a45c08e5fd4bc2c4e8773f45ba1f54ab5d5794b7ca69877c8f8c7a2d4980f7`;
- 311 OPEN_LOW / 88 COMPACT / 1 equal-unsure decoded Teacher-GOLD counts;
- L1/L2/L3/L4 counts 140/120/80/60;
- exact 40-feature list hash `6e1d26e566a36e473f4f11b065df3e9eb282e06be7bdd3deb65a1160d440bfc3`.

Only after `R2_PREFLIGHT_PASS_STOP_BEFORE_MANUAL_TRAIN` may the user run TRAIN.

## Frozen learning demonstration

Before any R2 TRAIN result is observed, the experiment is frozen as:

- family-isolated `StratifiedGroupKFold`;
- 5 folds, shuffled;
- random state `20260815`;
- fold 0 is the fixed validation fold;
- StandardScaler fitted on training rows only;
- MLPClassifier with hidden layers `[32, 16]`;
- ReLU;
- Adam;
- alpha `0.0001`;
- batch size `32`;
- learning rate `0.001`;
- random state `20260815`;
- exactly 60 epochs;
- decision threshold `0.5`;
- positive class `COMPACT`.

No early stopping is used. No best epoch is selected. The final epoch is reported only as a development learning demonstration.

## Interpretation

The purpose of R2 is to answer a simple question visibly:

> Does the model reduce validation loss and improve balanced class-sensitive metrics relative to an always-OPEN_LOW baseline while learning from the 399 development labels?

A rising Macro-F1 and falling validation loss are learning diagnostics. They do not independently authorize checkpoint retention or deployment.

## Safety boundary

- E3-E Teacher-GOLD in training: **no**
- Stage7E in training: **no**
- physical-validity learning by AI: **no**
- threshold search: **no**
- hyperparameter search: **no**
- early stopping: **no**
- best-epoch checkpoint selection: **no**
- checkpoint retained: **no**
- production/shadow integration: **no**

The Colab TRAIN cell is manual. Repository CI may test the implementation on synthetic fixtures, but must not run the real 399-row Teacher-GOLD training experiment.
