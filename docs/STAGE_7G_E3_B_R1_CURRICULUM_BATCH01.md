# Stage 7G-E3-B-R1 — Curriculum Batch01 seal

## Status

**A 400-task target-blind development curriculum batch is sealed. No new Teacher-GOLD response has been collected and no model has been fitted.**

This stage executes the Stage 7G-E3-B generator against the pinned 40-family AnimeTAB Batch01 source pool. It is a development-data package, not an untouched validation corpus.

## Reconstruction guard

Before inventory or selection, the frozen Stage 7B pairwise specialists were rebuilt from the balanced 100-family synthetic corpus. The reconstruction was checked against the already sealed 562 pairwise teacher tasks:

- `open_low`: 562/562 exact option matches;
- `compact`: 562/562 exact option matches;
- both A/B options: 562/562 exact matches;
- `open_low` training: 480 synthetic events, pairwise matrix 6900 × 4;
- `compact` training: 480 synthetic events, pairwise matrix 7708 × 4.

A non-100% guard would have blocked this stage.

## Target-blind inventory

The source archive SHA-256 is `2105c0ca1f11c80fbf2a096014cee77c905e94bdc13898820ad5d6fea4298710`. The target-free staff-2 parse reproduced the existing Batch01 counts:

- 40 source files;
- 24,066 pitched events;
- 13,542 chord events;
- 12,714 ambiguous chord events;
- 5,626 frozen `open_low != compact` disagreements.

The 600 task IDs already used by the earlier Teacher-GOLD Batch01 were excluded before E3 selection. This leaves **5,026 unlabeled disagreement events**. No previous teacher response was consulted.

Frozen E3-A difficulty counts after exclusion:

| Level | Events | Families with ≥1 event |
|---|---:|---:|
| L1 | 788 | 33 |
| L2 | 1,482 | 38 |
| L3 | 1,202 | 39 |
| L4 | 1,554 | 38 |

## Quota freeze

The first curriculum pilot is intentionally weighted toward simpler ergonomic contrasts while preserving harder examples:

- L1: **140**
- L2: **120**
- L3: **80**
- L4: **60**
- total: **400**

Thus 260/400 = **65%** of the sealed tasks are L1/L2. These quotas were fixed before any new Teacher-GOLD response existed. Selection is deterministic and family-balanced inside each level.

The final batch covers all **40 source families**. Per-level family coverage is L1=33, L2=38, L3=39, L4=38. The selected task set has zero overlap with the prior 600 sealed task IDs.

## External package

The raw curriculum package remains outside Git.

`ST_Guitar_Stage7G_E3_B_R1_Curriculum_Batch01_400.zip`

SHA-256: `e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`

The package contains:

- blind 400-task Teacher-GOLD A/B manifest;
- non-teacher-facing internal audit with level/family/feature metadata;
- 1,560 L1/L2 rule-derived property records;
- batch seal;
- README.

The rule-derived records describe geometry only and are **not** Teacher-GOLD preference labels.

## Scientific boundary

- teacher responses used for generation: **no**
- new Teacher-GOLD labels created: **0**
- old 556 decisive labels used for selection: **no**
- prior 600 task IDs reused: **no**
- Stage 7E reused: **no**
- model fit: **no**
- checkpoint retained: **no**
- production integration: **no**

Because these 40 source families overlap the prior Batch01 development families, this package may support E3 development/pilot annotation but **must not be presented as a new untouched validation corpus**. A later E3-E validation must use new family-disjoint material with a preregistered gate.
