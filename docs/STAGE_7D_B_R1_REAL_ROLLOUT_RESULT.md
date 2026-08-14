# Stage 7D-B-R1 — Real common-tone self-rollout

Date: 2026-08-14

Status: **FAIL / NO PROMOTION**

## Question

Does the strong Stage 7C teacher-forced `common_tone` transfer survive when the model must use its own previous prediction rather than the observed previous Guitar Pro voicing?

## Reproduction guard

Before reading the rollout result, the external corpus and frozen specialist path reproduced the accepted Stage 7C-R1 boundary and metrics:

- 42 raw XML files
- 37 parser accepted
- 5 parser rejected
- 4 duplicate extras removed
- **33 unique admitted XML / 25 families / 1879 chord events**
- frozen `open_low` Top-1: **0.7915754923** over 1828 ambiguous events
- teacher-forced `common_tone` Top-1: **0.7473567056** over 1797 events

These match Stage 7C-R1 exactly.

## Rollout contract

The Stage 7D-B protocol on `main` was used unchanged:

1. First chord of each source: deterministic sole candidate when unambiguous, otherwise frozen `open_low` Top-1.
2. Later single-candidate chords update state deterministically.
3. Later ambiguous chords use frozen `common_tone` with the **previous system prediction**.
4. The observed previous real voicing never enters rollout features.
5. Teacher-forced `common_tone` and always-`open_low` are comparator-only metrics on the same eligible events.

No real-data fit or adaptation is performed.

## Result

| Metric | Top-1 |
|---|---:|
| `common_tone` self-rollout | **0.3155258765** |
| teacher-forced `common_tone` | 0.7473567056 |
| always `open_low` on same events | **0.7902058987** |

- self-rollout vs `open_low`: **-0.4746800223 (-47.47 pp)**
- self-rollout vs teacher-forced: **-0.4318308292 (-43.18 pp)**
- evaluated ambiguous post-seed events: **1797**
- seed events: **32**
- deterministic single-candidate context updates: **50**
- context divergence rate: **0.6677796327 (66.78%)**

Family-macro Top-1:

- self-rollout: **0.4230291730**
- teacher-forced: **0.7373320447**
- always `open_low`: **0.7918321629**

Family outcomes versus always `open_low`:

- 1 win
- 1 tie
- 22 losses

Family outcomes versus teacher-forced `common_tone`:

- 0 wins
- 2 ties
- 22 losses

Across the 24 evaluated families, family-level context divergence and self-rollout Top-1 have correlation **-0.9770**. This is a diagnostic association, not a causal estimate, but it is consistent with strong error propagation.

## Interpretation

The earlier `common_tone` signal is real as a **teacher-forced transition preference**, but it is not rollout-safe in its current form. Once a wrong previous voicing is fed back as state, the continuity specialist frequently optimizes continuity relative to the wrong context. The errors then propagate through the sequence.

This reproduces the broader lesson from the failed Stage 6 sequence experiments: a useful local transition signal does not automatically improve autoregressive whole-path behavior.

## Decision

Stage 7D-B-R1 is **rejected for promotion**.

- Do not add `common_tone` self-rollout to the accepted Stage 7D-A router.
- Do not retain a checkpoint.
- Do not integrate this path into MusicXML-to-GuitarTab-Engine production.
- Preserve the evidence as a negative research result.

The accepted positive path remains the target-blind stateless Stage 7D-A router (`open_low` / `compact` selection). A future transition-aware attempt must explicitly control state-error propagation rather than simply feeding the previous prediction back into `common_tone`.

## Safety state

- real training rows: **0**
- real fit/adaptation: **false**
- checkpoint retained: **false**
- production integration: **false**
- real XML committed to Git: **false**
