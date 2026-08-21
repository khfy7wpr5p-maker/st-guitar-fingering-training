# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 UNTOUCHED FINAL OPEN

## Scope

This change opens the preregistered `UNTOUCHED_FINAL` role exactly once for performer `02` after the accepted DEVELOPMENT and VALIDATION gates passed and the DEVELOPMENT model artifact was sealed.

The final target remains:

`OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`

The final runner is inference-only. It does not fit or tune a model, does not change the 28D feature schema, does not change physical candidate enumeration, and does not use Teacher/S2-A labels.

## Preconditions

The runner requires the exact accepted validation evidence:

`13b706076205abea42a436d10cf019a36445035e08172054989191121ff59e51`

and the exact sealed DEVELOPMENT model artifact:

`5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869`

It also requires the sealed final-open request before performer `02` is read.

## Frozen final method

- performer: `02`
- recordings: `30`
- accepted notes expected from the frozen split: `7,194`
- derived voicings expected from the frozen split: `2,210`
- exact physical candidate enumeration: unchanged, frets `0..19`, one note/string, exact pitch multiset
- single-candidate events: reported but excluded from ranking metrics
- model: sealed DEVELOPMENT scorer only
- comparator: `LOW_TOTAL_FRET.v1`
- no refit
- no tuning
- bootstrap: recording-block resampling, 2000 repetitions, seed 0
- pre-outcome literal order statistics: lower index `49`, upper index `1949`

Final PASS requires all of the following to be strictly positive versus the comparator:

- event Top-1 delta
- event MRR delta
- recording-macro Top-1 delta
- recording-macro MRR delta
- 95% recording-block bootstrap lower bound for event MRR delta

## Safety boundary

Final PASS means only:

`ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`

It does **not** authorize checkpoint retention, runtime connection, shadow integration, or production deployment.

The result is written as a separately sealed evidence file. The final-open request is never rewritten with outcome data.
