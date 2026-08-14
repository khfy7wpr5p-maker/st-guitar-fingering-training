# Stage 7C — Real Guitaristic Transfer Validation

Stage 7C asks a narrow question: do the five accepted synthetic pairwise specialists transfer at all to independent observed Guitar Pro/MusicXML voicing behavior?

It does **not** train on real observations, select a production model, retain a checkpoint, or integrate with MusicXML-to-GuitarTab-Engine.

## Frozen model bank

The accepted Stage 7 specialists remain separate:

- `open_low`
- `compact`
- `mid_position`
- `high_position`
- `common_tone`

Each specialist is fitted in memory from its own synthetic `RULE_PREFERRED` families. Real observed Guitar Pro choices are evaluation labels only and are explicitly **not teacher-GOLD**.

## Domain boundary

Synthetic training families/source hashes and real evaluation families/source hashes must be disjoint. Any overlap fails closed.

Real data is never added to Git by this stage. The evaluator accepts an external real MusicXML directory plus a family map.

## Candidate boundary

Physical candidates always come from the deterministic `valid_chord_voicings()` generator. Stage 7C does not let AI invent string/fret placements.

Synthetic training is bounded to frets `0..12`, while the intake contract supports `0..24`. Real transfer evaluation therefore keeps the full physical candidate set and reports events whose observed voicing or candidate set exceeds fret 12. These events are not silently removed.

Single-candidate chord events are excluded from ranking metrics because they provide no preference decision.

## Context boundary

The four static specialists receive no previous-voicing context.

`common_tone` uses the observed previous real chord only as a teacher-forced **diagnostic** transition context. The first chord of each real source is skipped for that specialist. This is reported explicitly and is not a deployment claim.

## Metrics

For every specialist Stage 7C reports:

- event-weighted Top-1
- event-weighted MRR
- uniform-random Top-1 baseline
- macro-family Top-1
- macro-family MRR
- per-family metrics
- single-candidate exclusions
- out-of-synthetic-fret-range counts

It also reports `specialist_coverage`: the fraction of common evaluation events for which **any** of the five specialists ranks the observed voicing first. This is an oracle-like diagnostic of behavior-bank coverage, not a deployable gating policy.

## Scientific status

Repository CI can validate the Stage 7C protocol and leakage guards without containing private/rights-unclear real data. A real transfer result requires running the CLI against an approved external Guitar Pro/MusicXML corpus.

Until that external evaluation is run and reviewed, Stage 7C must remain:

`DIAGNOSTIC / REAL TRANSFER RESULT PENDING`

No checkpoint or production integration is authorized by this stage.
