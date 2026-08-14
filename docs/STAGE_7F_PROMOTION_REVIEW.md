# Stage 7F — Promotion Review

Status: **PROMOTE RESEARCH DIRECTION — NO CHECKPOINT / NO PRODUCTION INTEGRATION**

## Decision

The accepted evidence supports promotion of the **target-blind stateless routing architecture** into the next research stage. It does **not** support retaining the current router as a production checkpoint.

The current specialist state is:

- `open_low`: active core research specialist;
- `compact`: active secondary research specialist;
- `mid_position`: research-only, not promoted;
- `high_position`: research-only, not promoted;
- `common_tone` self-rollout: rejected after Stage 7D-B-R1.

## Why the architecture advances

Stage 7E-R1 used an untouched sealed corpus with 3959 ambiguous events in 13 families. The router beat `always-open_low` on both preregistered comparison metrics:

- event-weighted Top-1: `0.456681` vs `0.431169` (`+2.55 pp`);
- macro-family Top-1: `0.434132` vs `0.395052` (`+3.91 pp`).

This reproduces a positive relative routing advantage outside the development corpus.

## Why the checkpoint does not advance

The absolute final Top-1 is materially below the Stage 7D-A development result, demonstrating domain shift. The Stage 7E gate was explicitly a gate into promotion review, not an automatic checkpoint or production gate. No absolute checkpoint threshold was preregistered before the final result, so Stage 7F will not invent a post-hoc threshold and claim a deployment decision from it.

The final stateless-oracle coverage was `0.910583`, while the actual router achieved `0.456681`. The oracle is not deployable because it depends on knowing which specialist matched the observed outcome, but the gap shows that target-blind arbitration remains the main research opportunity.

The current router selected:

- `open_low`: 3845 events;
- `compact`: 114 events;
- `mid_position`: 0;
- `high_position`: 0.

So the deployed behavior represented by the current research router is effectively an `open_low` policy with a sparse `compact` gate. `mid/high` are not promoted, but they remain available for future research if a target-blind gate can identify genuine niche usefulness.

## Permanent Stage 7E quarantine

The untouched final corpus is now permanently evaluation-only. It must not be used for:

- training;
- tuning;
- calibration;
- feature selection;
- hyperparameter selection.

Any later final validation must use another source/family/hash-disjoint corpus.

## Next stage: Stage 7G — Teacher-GOLD Preference Corpus V1

Stage 7G will create a new real guitaristic development corpus with labels that mean **teacher-preferred guitaristic choice**, not merely observed Guitar Pro behavior.

Minimum design target:

- at least 30 independent families;
- at least 600 teacher-labeled ambiguous events;
- at least 100 specialist-disagreement events;
- family-isolated validation;
- zero reuse of Stage 7E final sources or hashes;
- sequence context remains deferred;
- no checkpoint or production integration is preapproved.

Sampling priorities:

1. `open_low` vs `compact` disagreement;
2. events where stateless specialists disagree;
3. high candidate-count or large position-choice events;
4. diverse chord size, pitch span, and register;
5. candidate sets extending above synthetic fret 12, without assuming that high positions are preferred.

## Safety state

- model algorithm changed: **false**
- checkpoint retained: **false**
- production integration: **false**
- Stage 7E final reused for training: **false**
