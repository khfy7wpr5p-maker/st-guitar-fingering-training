# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0–4 | Safety, dataset, intake, normalization, deterministic physical engine | ✅ complete |
| 5–7E | bounded placement / routing research and untouched evaluation | ✅ research complete; untouched evidence consumed |
| 7G-E1/E2/E3 | Teacher-GOLD ergonomics routing research | ✅ completed through positive/negative diagnostics; no production checkpoint |
| 7G-E3-S0 | failure diagnostics + reliability redesign | ✅ completed |
| 7G-E3-S1-A/B/C/D | independent-component reliability program | ✅ historical evidence path; no direct training authorization |
| 7G-E3-S1-F | fail-closed component-training preparation harness | ✅ merged; real fit hard-closed |
| 7G-E3-S1-G v1 | full-reliability preregistration | ✅ merged immutable historical record |
| PR #70 / S1-G v2 | STRING-only protocol proposal | 🟡 open draft, diverged from current `main`, not merged truth |
| 7G-E3-S1-H-A | deterministic guitaristic plausibility analyzer | ✅ merged in PR #71 |
| Next S1-H stage | stronger deterministic hand/finger feasibility | 🟠 candidate direction only; not yet preregistered |
| Learned component fitting | component-model training | 🔒 hard-closed |
| Arbiter / refiner | learned ranking / refinement | 🔒 closed |
| Checkpoint retention | model retention / promotion | 🔒 closed |
| GuitarTab Engine integration | shadow / production | 🔒 closed |

## Current position

The repository is now **after merged Stage 7G-E3-S1-H-A**.

Current `main` is `1a8acf654f21d36c928fdd45b3a21a443b6ebe5a`, the merge commit for PR #71.

S1-H-A inserted a deterministic plausibility layer directly after `valid_chord_voicings()` and before any future learned ranking path. It keeps physical validity fully deterministic and introduces only one v1 hard-prune rule: `H001_MIN_FINGER_PROXY_GE_6`.

## What is completed

### S1-F — preparation only

- frozen target-blind feature contract;
- fail-closed provenance validation;
- family-safe fold construction;
- fixed baseline model shape;
- project-label fitting remains hard-closed.

### S1-G v1

- merged and frozen as historical preregistration;
- must not be retroactively rewritten after later architecture changes.

### S1-H-A

- complete authoritative candidate set required;
- raw physically-valid set retained for audit;
- deterministic classes and stable reason codes;
- incomplete subsets fail closed;
- `IMPRACTICAL` hard prune only for minimum-finger proxy >=6;
- five-fret borderline and same-topology dominance cases retained;
- 10/10 repeatability and full-set fail-closed tests included;
- final PR head CI passed.

## Open architecture inconsistency: PR #70

PR #70 is still open/draft and was created from `ac146e9…`. Current `main` is nine commits ahead of that branch. The branch contains three commits not in `main`.

Its S1-G v2 STRING-only protocol therefore cannot be treated as current architecture without a fresh reconciliation. The merged S1-H-A contract already records a stronger boundary: S1-G v2 first-pass evidence is diagnostic-only/never-training and S1-G repeat is not to be run.

**Do not merge PR #70 mechanically.** First determine whether it should be superseded, archived, or rewritten as historical documentation.

## Next controlled milestone

No post-S1-H-A stage is merged or preregistered yet.

Recommended next milestone:

### Stage 7G-E3-S1-H-B — deterministic hand/finger feasibility design

This is a proposed next stage, not current repository truth.

Goal: replace the very coarse lower-bound `distinct positive frets` proxy with a deterministic, explainable feasibility analysis that can reason about actual finger assignment constraints without introducing learned musical preference.

A valid H-B preregistration should freeze before implementation:

- supported hand model and excluded extended techniques;
- barre representation rules;
- one-finger / one-fret and shared-fret assumptions;
- reach/span limits, if any, and their source/justification;
- deterministic reason-code precedence;
- fail-closed behavior;
- candidate-set invariants inherited from S1-H-A;
- regression matrix and repeatability requirements;
- explicit statement that musical preference remains outside the deterministic feasibility layer.

Only after that contract is frozen should runtime changes be made.

## Training and promotion gates

The following remain closed regardless of the existence of S1-F preparation code:

- S1-F real model fit;
- use of S1-E or S1-G diagnostic/repeat labels for training;
- checkpoint retention;
- Base Guitaristic Arbiter activation;
- hard-error refiner activation;
- GuitarTab Engine shadow/production integration.

## Evidence semantics

Frozen preregistration/evidence JSON files are historical snapshots. A file that says `PREPARATION_ONLY_DRAFT_PR` is not automatically stale evidence after merge; it records the state when sealed. Current live status is documented in the top-level project documents.
