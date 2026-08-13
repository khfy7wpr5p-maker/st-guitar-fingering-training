# Stage 6F.1 — Group-Normalized Path Scores

Stage 6F.1 tests whether per-chord candidate normalization fixes the raw-score accumulation failure observed in Stage 6F.

Safety and scope:

- same Stage 6E learned ranker;
- same deterministic family-isolated 5-fold split;
- same physically valid voicing candidates;
- no observed validation string/fret labels are used by decoding;
- model positive-class scores are normalized within each current chord candidate group before log path accumulation;
- Stage 6F state and transition budgets remain fail-closed;
- no checkpoint is retained;
- diagnostic Guitar Pro behavior cloning only, not teacher-GOLD and not production authority.

Primary comparison: group-normalized path decoding versus the same Stage 6E greedy rollout. Promotion requires at least 3 of 5 fold wins without violating the safety boundaries.
