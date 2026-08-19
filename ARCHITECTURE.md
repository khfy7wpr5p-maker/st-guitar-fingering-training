# Architecture

## Authoritative current map

```text
Guitar Pro / MusicXML source
        ↓
Safe intake + stream/tuning/pitch normalization
        ↓
Event / chord extraction
        ↓
Independent deterministic pitch ↔ string/fret validation
        ↓
valid_chord_voicings()
        │
        │ AUTHORITATIVE PHYSICAL BOUNDARY
        ↓
S1-H-A deterministic guitaristic plausibility                 ✅ MERGED
  ├─ complete authoritative candidate-set guard
  ├─ stable audit IDs/reason codes
  └─ hard prune H001_MIN_FINGER_PROXY_GE_6
        ↓
S1-H-B deterministic four-finger/barre resource feasibility   ✅ MERGED
  ├─ continuous same-fret barre grouping
  ├─ open/lower-fret blockers, higher-fret overrides
  └─ hard prune H101_MIN_STANDARD_FINGERS_GE_5
        ↓
S1-H-C deterministic standard finger-assignment enumeration   ✅ MERGED
  ├─ open strings use finger 0
  ├─ fretted groups use distinct fingers 1..4
  ├─ monotonic finger order across increasing frets
  ├─ explicit barre metadata
  └─ stable assignment IDs; no preference/ranking
        ↓
┌─────────────────────────────────────────────────────────────┐
│ REAL MODEL DEVELOPMENT GATE                                │
│ A future learned model may rank only S1-H-C assignments.  │
│ It may not manufacture or legalize a placement/fingering. │
└─────────────────────────────────────────────────────────────┘
        ↓ only after explicit model-development approval
Future learned fingering ranker                               🔒 CLOSED
        ↓
Future checkpoint-retention / promotion gate                  🔒 CLOSED
        ↓
GuitarTab Engine shadow / production integration              🔒 CLOSED
```

## Implemented deterministic boundary

The repository now has three distinct deterministic layers after physical enumeration.

### S1-H-A — plausibility

`valid_chord_voicings()` remains the sole physical authority. H-A requires the complete authoritative set, preserves it for audit, and only conservatively prunes the declared `H001_MIN_FINGER_PROXY_GE_6` cases. Five distinct positive frets and mechanical dominance remain retained at this layer.

### S1-H-B — fretting-resource feasibility

H-B improves on H-A's coarse distinct-fret proxy without pretending to solve full biomechanics. It partitions same-fret targets into continuous barre groups under explicit blocking rules and counts the minimum ordinary fretting-finger resources required.

A barre may cross an unused string or a higher-fretted note that can override the lower barre. It may not cross a string that must remain open or must sound a lower positive fret. Under the declared ordinary four-finger envelope, `minimum_standard_fingers >= 5` is pruned by `H101_MIN_STANDARD_FINGERS_GE_5`.

H-B may only remove H-A-retained candidates and never resurrect an upstream prune.

### S1-H-C — standard finger assignments

H-C expands each H-B-retained voicing into every deterministic ordinary four-finger assignment admitted by the frozen v1 rules. It preserves pitch/string/fret exactly, uses finger `0` for open strings, assigns one distinct finger to each H-B fretting group, records barre spans, and enforces increasing finger numbers across strictly increasing fret positions.

H-C is an **enumerator, not a ranker**. It deliberately emits multiple legal standard fingering candidates when the deterministic rules do not justify choosing one.

## Why the model should come after H-C

The earlier research tried to learn guitaristic preference while the candidate representation was still coarse. H-A/B/C now move facts that can be decided safely and explainably out of the learned layer:

- physical pitch/string/fret validity;
- obvious ordinary-hand resource impossibility;
- exact standard finger-assignment candidate generation.

A future learned model therefore has a narrower job: rank already-valid, already-resource-feasible standard assignments by guitaristic quality. That makes model errors auditable and prevents preference learning from becoming a hidden physical-validity engine.

## What remains intentionally non-deterministic

The deterministic boundary does not claim to encode:

- most natural/comfortable fingering;
- player-specific hand anatomy;
- detailed stretch or wrist comfort;
- transition quality across previous/next chords;
- musical style, tone, resonance, or expressive intent.

Those are potential learned or separately validated contextual signals. They must not be converted into new hard rules merely to avoid model development.

## Historical learning boundary

- S1-F preparation code exists, but real project-label fitting remains hard-closed.
- S1-G v1 is immutable merged historical preregistration.
- S1-G v2 / PR #70 was closed as superseded without merge.
- S1-E pilot/repeat labels remain never-training.
- S1-G v2 first-pass remains diagnostic-only / never-training; its repeat is not run.
- Stage 7E and E3-E are consumed evaluation-only evidence.
- repeat/reliability labels remain separate from training labels.

## Required contract for the next learned stage

Before real model fitting, a new model-development protocol must freeze:

1. prediction target over S1-H-C assignments;
2. exact eligible label provenance and forbidden corpora;
3. target-blind/deterministic input features;
4. family-isolated training and evaluation splits;
5. baseline(s), metrics, and acceptance gates;
6. handling of ties/unsure labels;
7. checkpoint-retention policy fixed before the deciding evaluation;
8. fail-closed guarantee that model output is always one of the supplied S1-H-C assignments;
9. no production/shadow integration from training success alone.

## Evidence and status semantics

Frozen JSON preregistration/evidence records describe the state when sealed and are not retroactively rewritten after merge. Current status belongs in the live top-level documentation.

## Current continuation point

**S1-H-C is merged. The repository has reached the real model-development gate.** Do not add more learned behavior, fit a model, select a checkpoint, or begin shadow/production integration without the separate model-development approval.
