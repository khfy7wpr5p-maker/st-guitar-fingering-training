# Stage 7G-E3-S1-H-B — Deterministic Fretting-Resource Feasibility

Status: **PREREGISTERED BEFORE IMPLEMENTATION**  
Rule version: `S1-H-B.v1`

## Purpose

Add a second deterministic layer after merged S1-H-A. S1-H-B asks a narrower question than full biomechanics:

> Can the already physically-valid, S1-H-A-retained voicing be covered by the ordinary four fretting fingers when same-fret notes may share a continuous barre?

This stage does **not** claim to solve comfort, reach, finger independence, wrist posture, tone, style, or the most natural fingering. It is a conservative resource-feasibility filter only.

Pipeline boundary:

`valid_chord_voicings()` → S1-H-A plausibility → **S1-H-B fretting-resource feasibility** → later deterministic reach/pose work → future learned ranking.

## Authority and scope

- `valid_chord_voicings()` remains the sole physical pitch/string/fret authority.
- S1-H-A remains authoritative for its existing plausibility/pruning result.
- S1-H-B may only remove candidates that S1-H-A retained.
- No candidate may be created, repaired, legalized, or reintroduced.
- Six-string guitar only.
- Standard fretting envelope uses fingers 1–4.
- Thumb-over fretting, right-hand tapping, two-hand fretting, capos, scordatura-specific technique rules, and other extended techniques are outside v1.
- Open strings consume no fretting finger.

## Continuous-barre model

For a positive fret `f`, two target strings at fret `f` may share one finger only when a continuous barre can span between them without changing a required lower/open note.

A string crossed by that barre is:

- **passable** when unused;
- **passable** when fretted at `f`;
- **passable** when fretted above `f` because a higher-fret finger may override the underlying barre;
- **blocking** when it must remain open;
- **blocking** when it is fretted below `f`.

For each positive fret, target strings are therefore partitioned deterministically into the minimum number of continuous barre groups separated by blocking strings.

The conservative minimum standard-finger requirement is the total number of those groups across all positive frets.

## Hard-prune rule

Exactly one new hard-prune rule is frozen in v1:

`H101_MIN_STANDARD_FINGERS_GE_5`

Condition:

`minimum_standard_fingers >= 5`

Action:

`STANDARD_FINGERING_INFEASIBLE_AND_PRUNE`

Rationale: under the declared ordinary four-finger envelope, each group requires a finger at one fret. A finger cannot simultaneously cover two different fret positions, and blocking strings split same-fret coverage into separate continuous groups.

This is stronger and more explicit than S1-H-A's lower-bound proxy. It does not assert impossibility under thumb-over or extended technique.

## Feasible result

When `minimum_standard_fingers <= 4`, the candidate is retained as `RESOURCE_FEASIBLE` and a deterministic canonical resource-assignment witness is emitted:

- groups ordered by ascending fret, then ascending first string;
- canonical finger numbers assigned 1..N in that order.

The witness proves only that the frozen resource model has enough standard fingers. It is **not** a recommendation of the most natural real fingering.

## Upstream-pruned candidates

Candidates already pruned by S1-H-A remain present in the full audit as `UPSTREAM_PRUNED`. S1-H-B does not reassess or resurrect them.

Reason code:

`U100_UPSTREAM_S1H_A_PRUNED`

## Required invariants

1. raw candidates exactly match the authoritative S1-H-A raw audit;
2. S1-H-B input state is recomputed from the same pitch set and tuning rather than trusting a caller-supplied subset;
3. final retained candidates are a subset of S1-H-A retained candidates;
4. no upstream-pruned candidate is reintroduced;
5. no new voicing is created;
6. group partitioning is deterministic;
7. canonical assignment is deterministic;
8. input/order-independent semantic output;
9. 10/10 repeated execution is identical;
10. every hard prune carries `H101_MIN_STANDARD_FINGERS_GE_5`;
11. if no final candidate remains, status is explicit as `NO_STANDARD_FINGERING_CANDIDATE`.

## Explicit non-rules in v1

S1-H-B does not prune solely on:

- absolute fret height;
- fret span / hand stretch;
- finger-order crossing;
- wrist angle;
- barre comfort;
- string skipping;
- open-string preference;
- tone/resonance/style;
- transition from a previous or to a next chord.

Those require later bounded stages and must not be smuggled into this resource rule.

## Test matrix

Implementation must cover at minimum:

- observed open-C regression remains retained;
- five distinct positive frets are newly rejected by the four-finger envelope;
- an open string blocks a same-fret continuous barre;
- a lower-fretted intervening string blocks a higher-fret barre;
- a higher-fretted intervening string may be overridden by a lower underlying barre;
- unused intervening strings do not block a barre;
- upstream S1-H-A-pruned candidates remain pruned and audited;
- final subset/no-new-voicing invariants across canonical pitch sets;
- stable canonical group/assignment order;
- 10/10 repeatability.

## Scientific boundary

- no Teacher labels are read;
- no S1-E/S1-G data is reopened;
- S1-F real model fit remains hard-closed;
- no learned component, arbiter, refiner, threshold fit, or checkpoint is created;
- no GuitarTab Engine shadow/production integration;
- this stage is deterministic technical development only.

## Next boundary

A later S1-H-C stage may study deterministic reach/pose constraints only after H-B is merged and audited. Real model development remains closed until the deterministic boundary is deliberately completed and a separate model-training gate is reached.