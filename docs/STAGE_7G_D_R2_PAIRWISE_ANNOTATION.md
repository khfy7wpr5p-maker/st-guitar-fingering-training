# Stage 7G-D-R2 — Pairwise teacher annotation transition

## Why the annotation interface changes

Stage 7G-D-R1 deliberately exposed the complete deterministic physical candidate set for each selected chord. That maximizes information per answer, but the first real teacher session showed that 8–20 alternatives per chord are too expensive for reliable large-scale annotation.

The first export contains 38 blind selections. All 38 task IDs belong to the sealed 600-task manifest, all 38 selected candidate IDs exist in the corresponding deterministic physical candidate sets, and there are no duplicate task IDs. Those answers are therefore retained rather than discarded.

The raw teacher export remains outside Git. Repository evidence records only its SHA-256 and derived validation counts.

## Two label semantics, kept separate

The first 38 answers remain **full-candidate preference evidence**: the teacher chose one voicing from the complete displayed candidate set.

The remaining 562 sealed tasks switch to a separate **pairwise open_low-vs-compact preference** label. Pairwise answers must not be silently promoted to the stronger full-candidate Teacher-GOLD meaning.

Before a full-candidate choice becomes a finalized `TeacherGoldRecord`, the withheld source/family/specialist audit channel still has to be attached and the existing Teacher-GOLD validator must pass.

## Pairwise teacher view

Every remaining task was already sealed as an `open_low` vs `compact` disagreement before any teacher response. Pairwise generation therefore does not resample tasks after observing the first 38 choices.

For each remaining task:

- take frozen `open_low` top-1 and frozen `compact` top-1;
- verify the two predictions differ and both belong to the deterministic physical candidate set;
- expose exactly two physical TAB candidates to the teacher as opaque **A** and **B**;
- hide specialist identity and all model scores;
- hide source identity and observed source TAB voicing;
- choose A/B side with a deterministic task-id hash fixed before the teacher response;
- allow `A`, `B`, or `EQUAL_OR_UNSURE`.

`EQUAL_OR_UNSURE` is retained as information. It must never be coerced to A or B.

The separate internal audit maps A/B back to the frozen specialist identities and original candidate IDs only after annotation.

## Pairwise training gate

Before any pairwise model fit or Colab training, Stage 7G-D-R2 preregisters:

- at least **400 decisive A/B labels**;
- decisive labels from at least **30 independent families**;
- family-isolated validation is mandatory;
- equal/unsure answers remain excluded from forced binary targets.

The threshold is fixed before any pairwise responses are collected. Passing it authorizes only a later training proposal; it does not preapprove checkpoint retention or production integration.

## Current boundary

- validated blind full-candidate choices retained: **38**;
- finalized `TeacherGoldRecord` rows: **0** pending withheld audit attachment;
- remaining pairwise tasks: **562**;
- pairwise labels collected: **0**;
- full Teacher-GOLD corpus gate: **closed**;
- pairwise training gate: **closed**;
- Colab training: **not started**;
- checkpoint retention: **false**;
- production integration: **false**;
- Stage 7E final reuse: **false**.
