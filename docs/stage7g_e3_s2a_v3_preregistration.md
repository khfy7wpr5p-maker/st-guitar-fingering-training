# Stage 7G-E3 — S2-A.v3 consensus-quarantine tournament preregistration

Status: **FROZEN BEFORE FINAL OPEN**

This protocol exists because S2-A.v2 failed its DEVELOPMENT gate. The v2 failure is preserved and is not rewritten as a pass.

## Evidence boundary

- S2-A.v2 DEVELOPMENT export was available for diagnosis and model redesign.
- The separately exported `FINAL_SEALED` labels remain unopened for model selection, feature selection, threshold selection, or hyperparameter selection.
- S2-A.v3 may use the same untouched FINAL only because the v3 contract is frozen before that FINAL is opened/evaluated.

## Reliability / consensus handling

The v2 exact repeat gate (0.85) failed at 25/30 exact assignment-or-class agreements (0.8333). S2-A.v3 does not erase that result.

For v3:

- require same-session exact repeat agreement >= 0.80;
- any semantic task whose hidden repeat disagrees is **quarantined**;
- the original and repeat rows for a quarantined semantic task are never trainable;
- repeat rows are never trainable regardless of agreement;
- require at least 160 stable decisive DEVELOPMENT originals across at least 20 families.

This changes the role of repeat evidence from a hard exact-fingering identity gate to a noise-detection/quarantine gate. It is a new protocol, not a reinterpretation of v2.

## Frozen ranker

Pairwise preference target:

- one Teacher-selected assignment is preferred over every other exact H-C.v2 assignment for the same fixed voicing;
- mirrored pair rows are generated (`delta`, `-delta`) with labels (1, 0).

Model:

- `ExtraTreesClassifier`
- `n_estimators = 250`
- `min_samples_leaf = 4`
- `max_features = "sqrt"`
- `random_state = 0`
- `n_jobs = 1`
- `bootstrap = False`

Multiway ranking:

- evaluate every ordered candidate pair;
- accumulate pairwise preference probabilities for each assignment;
- sort descending by tournament score, then stable assignment ID.

Features remain the frozen S2-A 30D target-blind assignment features. No FINAL-derived features are permitted.

## DEVELOPMENT CV

Preserve the exact S2-A.v2 family-to-fold mapping contract. Five family-isolated folds.

PASS requires all:

- repeat consensus >= 0.80;
- all repeat disagreements quarantined;
- stable decisive DEVELOPMENT tasks >= 160;
- DEVELOPMENT families >= 20;
- preference constraints >= 200;
- CV Top-1 >= 0.60;
- CV MRR >= 0.75;
- macro-family Top-1 >= 0.60;
- macro-family Top-1 delta over deterministic comparator >= +0.05;
- family wins > family losses;
- deterministic 10/10 identical CV signatures.

Only after every DEVELOPMENT check passes may the all-DEVELOPMENT v3 model be fit and sealed.

## Untouched FINAL

The FINAL loader must not be called before the v3 DEVELOPMENT model is sealed.

FINAL PASS requires all:

- Top-1 >= 0.60;
- MRR >= 0.75;
- macro-family Top-1 >= 0.60;
- macro-family Top-1 delta over deterministic comparator >= +0.05;
- family wins > family losses.

## Authority boundary

Even a FINAL PASS does **not** authorize checkpoint retention, runtime connection, shadow authority, production mutation, or replacement of deterministic physical feasibility logic. Those remain separate review gates.
