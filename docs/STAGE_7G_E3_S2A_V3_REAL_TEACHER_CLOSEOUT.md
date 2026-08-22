# Stage 7G-E3 — S2-A.v3 Real Teacher Fit closeout

Status: **REAL TEACHER FIT — FINAL PASS**

## Why v3 exists

S2-A.v2 remains a recorded DEVELOPMENT failure: exact hidden-repeat agreement was 25/30 = 0.8333 against the frozen 0.85 gate, and the frozen linear ranker also missed its DEVELOPMENT CV thresholds. That result was not overwritten.

Before opening the separately exported FINAL labels, S2-A.v3 was frozen as a DEVELOPMENT-adapted protocol. Every repeat disagreement is quarantined and non-trainable; the v2 family-isolated fold mapping and frozen 30D target-blind feature contract are retained.

## DEVELOPMENT PASS

Stable corpus after quarantine/non-decisive filtering:

- 192 decisive original tasks
- 24 GuitarSet families
- 446 pairwise preference constraints

Frozen `ExtraTreesClassifier` pairwise-tournament ranker:

- 250 trees
- `min_samples_leaf=4`
- `max_features=sqrt`
- `random_state=0`
- single-threaded deterministic fit

5-fold family-isolated CV:

- Top-1 = **0.6510416667**
- MRR = **0.7855902778**
- macro-family Top-1 = **0.6566633598**
- macro-family Top-1 delta vs deterministic comparator = **+0.2089947090**
- family wins / ties / losses = **16 / 7 / 1**
- determinism = **10/10 identical**
- CV signature = `6f76dc1ed66ec274ce4410e42573de6155e487f4ee4ad5d59c3868ed5db4b9f4`

The all-stable-DEVELOPMENT model was then fit and sealed before FINAL evaluation.

- model SHA-256 = `2c2427ed9cfdf0d2e5321a96f4a0a1181b81ff35a5a157eb704515378a3457e2`
- development model artifact SHA-256 = `20afa9a7162f34b09904b1eeb0b844ad269acfdcddaabcfde8b52b42820029fd`

## UNTOUCHED FINAL PASS

Only after the model seal, the 60-task / 6-family FINAL export was evaluated once.

- Top-1 = **0.6000000000**
- MRR = **0.7644444444**
- baseline Top-1 = **0.4833333333**
- macro-family Top-1 = **0.6000000000**
- macro-family Top-1 delta = **+0.1166666667**
- family wins / ties / losses = **4 / 0 / 2**
- all frozen FINAL checks = **PASS**
- prediction signature = `86d66770f8b045832d137d200e12287e86c5e923bc11d18318cac5bac75a9886`
- FINAL result SHA-256 = `2c578a17108f7a13b29ea108763c622b76323093e68d619cb0a3a1417e3c1eac`

Three independent all-DEVELOPMENT refits reproduced the same model SHA and the same FINAL prediction signature/metrics.

## Safe checkpoint package

A non-pickle, data-only ExtraTrees checkpoint representation was generated and independently checked to reproduce the same FINAL rankings.

- checkpoint schema: `st-guitar-s2a-v3-extra-trees-checkpoint-v1`
- checkpoint SHA-256: `b5ce49867a314d77cf1c722d67f5cd76bd160a9186a3831c795f130abf0d9491`
- raw Teacher choice exports are intentionally **not committed to the public repository**.

## Authority boundary

This closes **Real Teacher Fit** scientifically. It does not by itself authorize runtime connection or production authority.

Current next gate: **CHECKPOINT RETENTION REVIEW**.
