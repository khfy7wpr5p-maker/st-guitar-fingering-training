# Stage 7D-A-R1 — Real Stateless Router Result

Date: 2026-08-14

Status: **DIAGNOSTIC POSITIVE — NO MODEL PROMOTION**

## Question

Can a target-blind router choose among the four stateless Stage 7 specialists without seeing the observed target voicing and beat the strongest simple deployment baseline: always choose `open_low`?

## Data boundary

The same independently reconstructed real Guitar Pro/MusicXML corpus used in Stage 7C-R1 was used again:

- 33 unique admitted XML
- 25 broad musical families
- 1879 chord events
- 24 families / 1828 ambiguous chord events contribute to stateless routing metrics

The real XML files remain outside Git.

## Reproduction guard

Before routing, the reconstructed frozen stateless specialist bank reproduced the Stage 7C-R1 Top-1 values exactly:

| Specialist | Top-1 |
|---|---:|
| open_low | 0.7915755 |
| compact | 0.6203501 |
| mid_position | 0.1307440 |
| high_position | 0.0590810 |

This confirms the router was evaluated against the same accepted stateless specialist behavior.

## Family-isolated router result

Five deterministic family-isolated folds were used. The observed Guitar Pro voicing was used only to create specialist-success labels inside training families and to score held-out validation families. It never entered router features.

| Metric | Router | Always open_low | Delta |
|---|---:|---:|---:|
| Macro fold Top-1 | **0.8386508** | 0.7967706 | **+0.0418802** |
| Event-weighted Top-1 | **0.8309628** | 0.7915755 | **+0.0393873** |
| Macro-family Top-1 | **0.8468893** | 0.7987830 | **+0.0481064** |

Fold outcomes:

- wins: **4 / 5**
- losses: **1 / 5**

Family outcomes across the 24 evaluated families:

- wins: **16**
- ties: **7**
- losses: **1**

The only losing family was inside the fifth fold; therefore the result is positive but not yet a production-quality gate.

## Stateless oracle ceiling

The four stateless specialists jointly cover more events than the router currently captures:

- event-weighted oracle coverage: **0.9305252**
- macro-family oracle coverage: **0.9401126**

This remains an oracle upper-bound diagnostic and is not deployable accuracy.

## What the router actually learned

Out-of-fold selections across 1828 events:

- `open_low`: **1567** events (85.72%)
- `compact`: **261** events (14.28%)
- `mid_position`: **0**
- `high_position`: **0**

This is an important result: the first router did not try to rescue the two specialists that failed real transfer. It learned a useful **open_low-versus-compact gate** and improved real behavior matching by about four percentage points over always using `open_low`.

## Interpretation

Stage 7D-A-R1 is the first evidence that target-blind specialist selection can improve the real Guitar Pro transfer result without using the observed target as an input feature.

However this is still diagnostic rather than deployable because:

1. only 24 evaluated families contribute to routing CV;
2. one fold and one family still lose;
3. `common_tone` is intentionally excluded because its current real result depends on teacher-forced previous real voicing context;
4. no untouched final test corpus exists yet for router promotion.

The next scientific step should therefore be rollout-safe context routing and/or an independent held-out router test corpus, not production integration.

## Safety state

- target voicing in router features: **false**
- family-isolated CV: **true**
- physical candidate generation: **deterministic only**
- common_tone included: **false**
- checkpoint retained: **false**
- production integration: **false**
- real corpus committed to Git: **false**
