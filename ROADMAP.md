# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0–4 | safety, dataset, intake, normalization, deterministic physical engine | ✅ complete |
| 5–7E | bounded placement/routing research + untouched evaluation | ✅ research complete; untouched evidence consumed |
| 7G-E1/E2/E3 | Teacher-GOLD ergonomics research | ✅ completed through diagnostics; no production checkpoint |
| 7G-E3-S0 | failure diagnostics + reliability redesign | ✅ completed |
| 7G-E3-S1-A/B/C/D | independent-component reliability program | ✅ historical evidence path |
| 7G-E3-S1-F | fail-closed model-preparation harness | ✅ merged; real fit still hard-closed |
| 7G-E3-S1-G v1 | full-reliability preregistration | ✅ immutable merged history |
| PR #70 / S1-G v2 | obsolete STRING-only proposal | ✅ closed superseded, never merged |
| 7G-E3-S1-H-A | deterministic guitaristic plausibility | ✅ merged PR #71 |
| 7G-E3-S1-H-B | four-finger/barre resource feasibility | ✅ merged PR #73 |
| 7G-E3-S1-H-C | standard finger-assignment enumeration | ✅ merged PR #74 |
| Next | real learned fingering-ranking model | ⛔ approval gate reached; not started |
| Later | checkpoint retention / promotion | 🔒 closed |
| Later | GuitarTab Engine shadow / production | 🔒 closed |

## Current position

The deterministic pre-model pipeline is complete through **Stage 7G-E3-S1-H-C**.

The deterministic runtime baseline through H-C is `154d8d4c514849535a523ca79ea22b6fae7e77de`. Later documentation-only merges may advance the live `main` head without changing that runtime baseline.

The current pipeline is:

```text
valid_chord_voicings()
  → S1-H-A plausibility
  → S1-H-B ordinary four-finger/barre resource feasibility
  → S1-H-C complete standard finger-assignment candidate enumeration
  → REAL MODEL DEVELOPMENT GATE
```

## Completed deterministic milestones

### S1-H-A

- full authoritative candidate-set requirement;
- stable audit IDs/reason codes;
- `H001_MIN_FINGER_PROXY_GE_6` hard prune;
- no preference/ranking learned or hard-coded.

### S1-H-B

- explicit ordinary four-fretting-finger envelope;
- deterministic continuous-barre grouping;
- open/lower-fret blocking rules and higher-fret override behavior;
- `H101_MIN_STANDARD_FINGERS_GE_5` hard prune;
- no upstream-pruned candidate may be reintroduced;
- PR #73 CI #193: 236 tests PASS + compile PASS; Stage 7B-C2 step skipped by branch condition.

### S1-H-C

- all standard finger assignments enumerated for every H-B-retained voicing;
- open strings use finger 0;
- fretted groups use distinct fingers 1..4;
- increasing fret positions require increasing finger numbers;
- exact pitch/string/fret preservation;
- explicit barre metadata;
- stable SHA-256 assignment identities;
- PR #74 CI #195: 245 tests PASS + compile PASS; Stage 7B-C2 step skipped by branch condition.

## What is deliberately not solved by deterministic rules

H-A/B/C do not choose the most natural fingering and do not encode player-specific anatomy, detailed reach comfort, musical transitions, tone, resonance, or style as hard truth.

Adding arbitrary hard thresholds for those factors would move subjective guitaristic preference into the wrong architectural layer. The next justified step is therefore learned ranking, not more speculative pruning.

## Next milestone — real learned fingering ranker

This milestone has **not started**.

Before fitting any project model, freeze a separate protocol that defines:

- target: what constitutes a better S1-H-C assignment;
- exact eligible Teacher-GOLD/training provenance;
- excluded pilot/repeat/diagnostic/consumed evidence;
- assignment-level feature contract;
- family-isolated train/validation/test policy;
- baselines and metrics;
- tie/unsure handling;
- model family and hyperparameter policy;
- checkpoint-retention criteria fixed before deciding evaluation;
- fail-closed output restriction to supplied S1-H-C assignment IDs.

Real training, tuning, or checkpoint selection must not begin before the model-development gate is explicitly opened.

## Promotion gates remain separate

Even a successful future model experiment would not by itself authorize:

- checkpoint retention;
- Base Guitaristic Arbiter or refiner promotion;
- GuitarTab Engine shadow integration;
- production integration.

Each remains a later, separately evidence-backed gate.

## Evidence semantics

Frozen preregistration/evidence files remain immutable historical snapshots. Live repository status is maintained in the top-level documents.
