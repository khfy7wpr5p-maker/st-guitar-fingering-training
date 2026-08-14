# Stage 7G-D-R1 — Teacher-GOLD Batch01 seal

## Purpose

Seal the first real blind Teacher-GOLD annotation batch before any human preference labels are collected.

Stage 7G-C-R1 established a clean source pool of 40 independent AnimeTAB full-track families with 12,714 ambiguous chord events. The four accepted stateless specialists disagree on 12,358 of those events, and `open_low` disagrees with `compact` on 5,626 events.

No raw MusicXML is committed here. No source title, model prediction, or observed source TAB voicing is present in the teacher-facing task package.

## Pre-label annotation-effort guard

The generic Stage 7G-B selector prioritizes `open_low` vs `compact` disagreement and then balances families. Applied to the full disagreement pool, its candidate-count ordering would make the first 600 tasks unnecessarily expensive for a human teacher: approximately 67 candidates per task on average and as many as 165.

Before any Teacher-GOLD answers exist, Batch01 therefore preregisters one additional **target-blind ergonomic filter**:

- retain only highest-priority `open_low` vs `compact` disagreement events;
- retain only events with at most 20 deterministic physical voicing candidates;
- then apply the existing deterministic family-balanced round-robin selector;
- select exactly 600 tasks.

This leaves 3,011 eligible Tier-0 events. Every one of the 40 families still has at least 15 eligible events, so the sealed batch contains exactly 15 tasks per family.

The final teacher workload is:

- 600 tasks;
- 40 families;
- 15 tasks per family;
- 600/600 `open_low` vs `compact` disagreements;
- candidate count min 8;
- candidate count mean 16.788333333333334;
- candidate count max 20.

The candidate-count cap is not a musical target and does not depend on an observed Guitar Pro/TAB placement, teacher preference, validation score, or post-result model behavior. It is fixed before human labeling begins.

## Blind teacher package

The external package is not committed to Git. It contains:

- `annotate_batch01.html` — local browser annotation utility;
- `teacher_tasks_batch01.json` — blind teacher task manifest;
- `batch_seal.json` — non-sensitive package identity;
- `README.txt` — teacher instructions.

The teacher manifest contains only opaque task IDs, MIDI pitches, tuning, complete deterministic physical candidates, and candidate IDs. Candidate order is deterministic physical enumeration, not model ranking.

Pinned identities:

- teacher manifest SHA-256: `1617f7d584f22f1f357927c9cc00446f7fe95740e8987cb73fee5474cdcb1871`
- external ZIP SHA-256: `2a0c84ef3f86981c7fe162e421d762079c3b2f182d1602f5e889f6a5a7bd7852`

The browser utility stores progress locally and exports `st-guitar-stage7g-teacher-choice-export-v1` JSON. It does not transmit annotations automatically.

## Scientific boundary

At seal time:

- Teacher-GOLD labels: **0**
- Teacher-GOLD corpus gate: **closed**
- model fitting: **not authorized**
- Colab training: **not started**
- checkpoint retention: **false**
- production integration: **false**
- Stage 7E final corpus reuse: **forbidden / false**

The next scientific step after this seal is human annotation. Only after the returned choices are validated, joined to the withheld audit channel, and the Stage 7G minimum corpus gate passes may a later training stage be proposed.
