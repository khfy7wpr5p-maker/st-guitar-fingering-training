# Stage 7D-B — Rollout-safe common-tone protocol

Status: **DIAGNOSTIC PROTOCOL — REAL ROLLOUT RESULT PENDING**

## Goal

Measure whether the frozen Stage 7 `common_tone` specialist retains useful real-guitar behavior when its previous-voicing context comes from the system itself rather than from the observed Guitar Pro target.

## Rollout context

For each real source:

1. The first chord establishes a target-blind seed:
   - if the physical candidate set has one candidate, use that deterministic candidate;
   - otherwise use the frozen `open_low` specialist's Top-1 prediction.
2. For every later ambiguous chord, `common_tone` receives only the **previous system prediction**.
3. A later single-candidate chord updates the rollout context deterministically.
4. The observed previous real voicing never enters the rollout feature path.

## Diagnostic comparators

On the same post-seed ambiguous events, report:

- rollout-safe common-tone Top-1;
- teacher-forced common-tone Top-1 using the observed previous real voicing;
- always-`open_low` Top-1.

Teacher-forced context is comparator-only. It cannot update or repair rollout state.

## Required report fields

- event-weighted and macro-family rollout Top-1;
- event-weighted and macro-family teacher-forced Top-1;
- event-weighted and macro-family always-open-low Top-1;
- rollout delta vs open-low;
- rollout gap vs teacher-forced;
- context-divergence rate: fraction of evaluated events whose incoming system context differs from the observed previous voicing;
- seed and deterministic single-candidate context-update counts.

## Interpretation gate

Stage 7D-B does not automatically promote `common_tone` into the Stage 7D-A router.

A later real-corpus result must first show whether common-tone continuity survives self-rollout. If rollout degrades materially relative to teacher-forced context or fails to add value over target-blind stateless behavior, `common_tone` remains diagnostic-only. Router admission requires a later target-blind held-out-family experiment.

## Safety state

- AI physical candidate generation: **none**
- observed previous real voicing in rollout features: **false**
- real model fit/adaptation: **false**
- checkpoint retained: **false**
- production integration: **false**
- real corpus committed to Git: **false**
