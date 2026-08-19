# Safety

## Physical-authority invariants

- Parse untrusted XML with safe parsers; do not fetch network DTD/schema resources.
- Reject unsupported string/fret mappings, missing tuning, malformed durations, and impossible physical placements.
- Deterministic guitar rules own physical validity.
- `valid_chord_voicings()` is the authoritative physically-valid candidate generator for S1-H-A.
- Learned systems may only score/rank candidates already accepted by the deterministic physical engine.
- No learned model may create, repair, legalize, or silently reintroduce an invalid/pruned placement.

## S1-H-A plausibility safety

S1-H-A is deterministic and conservative.

- The analyzer must receive the complete authoritative candidate set for the same pitches/tuning.
- Non-authoritative candidates, duplicates, and incomplete authoritative subsets fail closed.
- Raw physically-valid candidates are preserved for audit.
- v1 hard-prune authority is limited to `H001_MIN_FINGER_PROXY_GE_6`.
- Five distinct positive fret values are retained as `BORDERLINE`.
- Same-topology mechanical dominance is diagnostic-only and retained in v1.
- Open-note count, high position, internal gaps, lower-position preference, tone, resonance, and artistic preference are not single-factor hard-prune rules.
- If the complete authoritative set is pruned, the result must be explicit as `NO_PLAUSIBLE_CANDIDATE`.

## Training and label boundaries

No user upload, teacher correction, annotation, pilot answer, or repeat answer is automatic training consent.

The current merged S1-H-A contract records:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- S1-F real project-label model fit: `HARD_CLOSED`.

Historical S1 repeat/reliability labels remain reliability-only. `EQUAL_OR_UNSURE` responses are preserved and never coerced into binary labels.

## Consumed evidence

- Stage 7E is permanently evaluation-only.
- E3-E Teacher-GOLD is permanently consumed untouched evaluation evidence.
- Historical development labels may not be relabeled as fresh validation.
- Repeat/reliability corpora may not be recycled as training or hard-error-mining data unless an explicitly newer merged protocol says otherwise; the current S1-H-A contract does not open such reuse.

## Model / promotion gates

The existence of an executable training harness does not authorize training.

The following remain closed:

- real S1-F component fitting;
- component specialist activation;
- Base Guitaristic Arbiter training/activation;
- learned hard-error refiner training/activation;
- checkpoint retention/promotion;
- GuitarTab Engine shadow integration;
- production integration.

Any later opening must be explicit, separately preregistered, reviewed, and merged before execution/retention decisions.

## Historical evidence files

Frozen preregistration/evidence JSON files are immutable historical snapshots. A field such as `PREPARATION_ONLY_DRAFT_PR` or `merge_authorized=false` may correctly describe the state when the record was sealed even after a later authorized merge.

Do not rewrite frozen evidence solely to make it match current live repository status. Live status belongs in the top-level documentation.

## Open PR #70 safety

PR #70 is open/draft and diverged from current `main`. It is not a dependency of merged S1-H-A and must not be merged mechanically.

Before any action on PR #70, reconcile its intended S1-G v2 behavior with the stronger merged S1-H-A boundary, especially the `S1-G v2 first-pass = diagnostic-only` and `S1-G repeat = do not run` rules.

## Future deterministic extensions

A future S1-H hand/finger feasibility layer may add deterministic constraints only after its contract is preregistered. It must distinguish physical/ordinary-technique feasibility from musical preference and must preserve the S1-H-A complete-authoritative-set and audit invariants.

## Development-control gates

Routine read-only analysis, bounded documentation maintenance, branch preparation, tests, CI inspection, and PR preparation are allowed inside an approved maintenance task.

Explicit approval remains required for consequential gates including runtime/model-behavior merges, checkpoint retention/promotion, shadow/production integration, destructive history operations, or material stage expansion.
