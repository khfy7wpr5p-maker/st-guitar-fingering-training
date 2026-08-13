# Stage 6G — Separate Transition Preference Model v1

Stage 6G returns to the successful Stage 6E branch and separates two questions that were previously mixed in one classifier:

1. unary/voicing preference: how plausible is this current physical voicing?
2. transition preference: given the previously selected physical voicing, how natural is the move into this current candidate?

The transition model uses only deterministic physical voicing candidates and the existing 10-feature transition geometry block: position-center movement, lower/upper fret movement, string overlap/Jaccard, shared-pitch same-string continuity, fret-span change, open-string change, and bass-string movement.

Training rows use the previous observed voicing only inside the training partition. Validation combined rollout is deployment-like: previous context is always the model-selected voicing, never the observed validation string/fret label. Future context remains Stage 6E pitch-only lookahead.

The two model score groups are normalized within the current chord candidate group and combined conservatively with a fixed transition weight of 0.25. There is no whole-piece DP in this stage.

Safety boundaries:

- candidate generation remains deterministic and physical;
- AI cannot create or approve impossible string/fret states;
- family-isolated 5-fold evaluation remains mandatory;
- no observed validation string/fret labels are fed back during combined rollout;
- no checkpoint is retained;
- this is Guitar Pro behavior-cloning diagnostics, not teacher-GOLD or production authority.

Promotion target: the combined model must beat the Stage 6E sequence-only rollout in at least 3 of 5 folds. The teacher-forced transition-only metric is diagnostic and cannot by itself satisfy promotion.
