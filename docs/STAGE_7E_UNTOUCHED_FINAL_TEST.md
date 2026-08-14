# Stage 7E — Untouched Final Test

Status: **SEALED / RESULT PENDING**

## Purpose

Test the accepted Stage 7D-A target-blind stateless router on a source that was not used in Stage 6, Stage 7C, or Stage 7D model development/evaluation.

The final result must not be inspected until this protocol and corpus identity are committed. No hyperparameter, specialist, router-feature, event-selection, or promotion-gate change is allowed after the final result is read.

## Sealed source

External corpus: `robust-guitar-tabs/code` at commit `f50309ad06dc734ddae5e3a0eda756fca221e2e7`.

Only the 16 files `GuitarProConversor/tabs/1.gp3` through `16.gp3` listed with exact Git blob SHA-1 and byte size in `evidence/stage7e_final_test_seal.json` are eligible.

The external repository is CC0-1.0. Raw GP3 files are not committed to this training repository.

Parser: PyGuitarPro 0.10.2, wheel SHA-256 `d9a80f4c920bb66ee0b1c7dbe797006486d04cf153c79eafb6630259fa09dac2`.

## Structural intake contract

A GP3 file is one final-test family. If a file contains multiple eligible guitar tracks they remain in the same family.

Eligible track:
- non-percussion;
- exactly six strings numbered 1..6.

Eligible chord event:
- one simultaneous beat containing at least two notes;
- all strings distinct;
- every fret within 0..24.

No event is selected or rejected based on whether any specialist/router predicts it correctly.

After extraction, deterministic physical candidate generation must contain the observed GP3 voicing. Single-candidate events are audited but excluded from Top-1 ranking.

Corpus sufficiency is preregistered:
- at least 8 final families with ambiguous events;
- at least 100 ambiguous final events.

If either threshold fails, Stage 7E ends as `INSUFFICIENT_FINAL_CORPUS`; no accuracy claim is made.

## Model freeze

The five synthetic specialists remain unchanged. Stage 7E uses only the accepted stateless specialists:
- `open_low`
- `compact`
- `mid_position`
- `high_position`

`common_tone` remains excluded because Stage 7D-B-R1 proved its current self-rollout path unsafe.

The Stage 7D-A router is refit once, in memory, on **all previously accepted development families only**. Final-test labels may not enter any fit, calibration, threshold, feature selection, or model-selection step. No evaluation router checkpoint is retained after the run.

Before final scoring, the development reconstruction must reproduce the accepted Stage 7C/7D evidence:
- 33 unique admitted XML;
- 25 development families;
- 1879 chord events;
- `open_low` real-development Top-1 `0.7915754923413567`;
- Stage 7D-A family-isolated CV macro router Top-1 approximately `0.8386507946895563`;
- Stage 7D-A CV macro always-open-low Top-1 approximately `0.7967706271049415`.

A reproduction failure aborts the final test before its accuracy result is accepted.

## Final metrics and gate

Primary metrics:
- event-weighted router Top-1;
- event-weighted always-`open_low` Top-1 baseline.

Secondary metrics:
- macro-family router Top-1;
- macro-family always-`open_low` Top-1;
- family win/tie/loss counts;
- selected specialist counts;
- stateless-oracle coverage (diagnostic only).

Promotion gate is fixed before result access:

1. event-weighted router Top-1 **must exceed** event-weighted always-`open_low` Top-1; and
2. macro-family router Top-1 **must be at least** macro-family always-`open_low` Top-1.

Failure of either gate means no promotion.

## Safety

- Final labels used for fitting: **0**
- Checkpoint retained: **false**
- Production integration: **false**
- Raw final corpus committed here: **false**
- Final result read before seal: **false**
