# S2-A.v3 DEVELOPMENT-only evidence

This record was written before opening/evaluating the sealed FINAL export.

Observed S2-A.v2 DEVELOPMENT facts:

- DEVELOPMENT presentations: 230 = 200 originals + 30 hidden repeats.
- v2 repeat exact assignment-or-class agreement: 25/30 = 0.8333333333, therefore v2 reliability gate FAIL against 0.85.
- All five repeat disagreements remain evidence of instability and are quarantined in v3; they are not relabeled as agreements.
- Stable decisive original tasks after quarantine/non-decisive filtering: 192 across 24 GuitarSet families.

Frozen v3 development-only model selection result for `ExtraTreesClassifier(n_estimators=250, min_samples_leaf=4, max_features='sqrt', random_state=0, n_jobs=1, bootstrap=False)` under the unchanged v2 family-isolated fold mapping:

- CV Top-1: 0.6510416667
- CV MRR: 0.7855902778
- macro-family Top-1: 0.6566633598
- macro-family Top-1 delta over deterministic comparator: +0.208995
- family wins / losses: 16 / 1

These numbers are DEVELOPMENT evidence, not FINAL claims. The untouched FINAL remains the external acceptance gate after v3 code/CI and model seal.
