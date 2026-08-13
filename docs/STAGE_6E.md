# Stage 6E — Sequence Context v2

Stage 6E extends Stage 6D with bounded pitch-only lookahead for the next chord.

## Safety boundary

- Previous context during validation is rollout from the model's own prior prediction.
- Future context may use only the next chord's sounding pitches, tuning, and physical candidate geometry derived from them.
- The next chord's observed string/fret assignment is never used as an input feature.
- Single-candidate chord events remain excluded from ranking metrics.
- No checkpoint is retained.
- This remains observed Guitar Pro behavior cloning, not teacher-GOLD and not production authority.

## Evaluation

Run the same deterministic family-isolated 5-fold comparison against:

1. Stage 6E sequence-context rollout
2. Stage 6D previous-context rollout
3. context-free learned ranker
4. deterministic low-total-fret baseline

The primary promotion signal is fold-majority improvement over Stage 6D without degrading safety boundaries.
