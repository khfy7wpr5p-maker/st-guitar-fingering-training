# Architecture

## Authoritative current map

Current live baseline after merged PR #93:

`a46f93861927342ea551e96b2a53859536e18a6f`

The architecture intentionally separates deterministic physical/fingering authority from learned ranking. It also keeps the two learned research targets separate: S2-A Teacher naturalness and GuitarSet observed string/fret voicing.

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
        │ AUTHORITATIVE PHYSICAL BOUNDARY
        ├───────────────────────────────────────────────────────────────┐
        │                                                               │
        ↓                                                               ↓
S1-H-A deterministic plausibility                              GuitarSet observed-gold intake
        ✅ MERGED                                                       ✅ PR #91
        ↓                                                               ↓
S1-H-B four-finger/barre resource feasibility                  GUITARSET-SPLIT.v1
        ✅ MERGED                                                       ✅ PR #92
        ↓                                                               ↓
S1-H-C.v1 standard finger-assignment enumeration               28D voicing feature contract
        ✅ AUTHORITATIVE                                                + pairwise model prereg
        │                                                               ✅ PR #93
        │                                                               ↓
        │                                                        DEVELOPMENT IMPLEMENTATION
        │                                                        + REAL FIT
        │                                                               ⏳ CURRENT GATE
        │                                                               ↓
        │                                                        DEVELOPMENT CV PASS 🔒
        │                                                               ↓
        │                                                        VALIDATION performer 03 🔒
        │                                                               ↓
        │                                                        SEALED DEVELOPMENT MODEL 🔒
        │                                                               ↓
        │                                                        UNTOUCHED_FINAL performer 02 🔒
        │                                                               ↓
        │                                                        CHECKPOINT REVIEW 🔒
        │                                                               ↓
        │                                                        GuitarTab Engine shadow/prod 🔒
        │
        ├─ S2-A static fingering naturalness
        │     ↓
        │   30D deterministic assignment features                    ✅ PR #78
        │     ↓
        │   blind pair + repeat reliability machinery                ✅ PR #78
        │     ↓
        │   fail-closed learned ranker + development CV               ✅ PR #79
        │     ↓
        │   untouched-final evaluation gate                           ✅ PR #80
        │     ↓
        │   Batch01 human evidence                                    ✅ diagnostic-only
        │     ↓
        │   Teacher Correction v1 pilot                               ✅ PR #89
        │     ↓
        │   fit-eligible fresh Teacher supervision                    🔒 unavailable
        │     ↓
        │   real S2-A fit / final / checkpoint                        🔒
        │
        └─ S1-H-C.v2 same-fret split experiment                       ⏳ PR #90 OPEN
             not authoritative; downstream audit required
```

## Authority boundaries

### Physical authority

`valid_chord_voicings()` remains the sole authoritative generator for physically exact pitch/string/fret candidates. Learned code cannot create, repair, legalize, or reintroduce a placement outside this set.

The GuitarSet observed-voicing path also starts from this physical authority. Its learned model ranks physical string/fret realizations only; it does not gain authority over physical validity.

### Deterministic ordinary-technique authority

S1-H-A/B/C.v1 transform physical candidates into auditable standard left-hand assignments:

- H-A: deterministic plausibility and conservative hard prune;
- H-B: ordinary four-finger/barre resource feasibility;
- H-C.v1: standard assignment enumeration under the frozen v1 hand model.

H-C.v1 `assignment_id` values remain the authoritative assignment objects consumed by S2-A.

PR #90 is a provisional H-C.v2 experiment. It addresses the discovered same-fret grouping issue by treating an H-B passable same-fret group as a lower bound for possible barre sharing rather than a mandatory single-finger/barre assignment. It must not replace H-C.v1 until downstream H-C capacity and S2-A evidence are explicitly re-audited.

### Learned authority: S2-A

S2-A is a ranker only. Its learned scalar score may order exact H-C assignment IDs supplied for one event, but it cannot change physical validity, H-B feasibility, or H-C assignment construction.

S2-A v1 target:

`STATIC_STANDARD_FINGERING_NATURALNESS`

This excludes previous/next chord transitions, tempo, style, tone color, right-hand pattern, extended techniques, and player-specific anatomy.

### Learned authority: GuitarSet observed voicing

GuitarSet v1 target:

`OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`

Given the exact simultaneous MIDI pitch multiset of a derived GuitarSet event, the model ranks physically exact standard-tuning string/fret realizations so that the observed guitarist placement is preferred.

This model does **not** learn:

- left-hand finger numbers;
- barre identity;
- S2-A Teacher preference;
- previous/next chord transitions;
- performer identity or style as model features;
- physical validity.

## GuitarSet observed-gold data boundary

PR #91 introduced fail-closed ingestion for the approved GuitarSet `*_comp.jams` archive.

Safety and identity rules include:

- exact archive SHA sealing;
- archive/member size limits;
- path-traversal and symlink rejection;
- duplicate-member rejection;
- excessive compression-ratio rejection;
- only `annotation/*_comp.jams` accepted;
- deterministic data-source-to-string mapping;
- deterministic MIDI rounding followed by physical fret recomputation;
- malformed, non-finite, negative-time, MIDI-range, negative-fret, and over-max-fret rows quarantined rather than repaired;
- same-string ambiguity in a 50 ms local window excludes that whole window from derived voicing gold.

Audited dataset:

- 180 recordings;
- 45,686 raw notes;
- 45,615 accepted notes;
- 71 quarantined negative-fret rows;
- accepted frets `0..19`;
- 12,556 conservative derived strum-voicing events.

Direct note observations and derived voicing clusters are distinct evidence types.

## GuitarSet split/leakage boundary

`GUITARSET-SPLIT.v1` is frozen as an `UNSEEN_PERFORMER_SEEN_REPERTOIRE` benchmark.

Roles:

- DEVELOPMENT: performers `00, 01, 04, 05`;
- VALIDATION: performer `03`;
- UNTOUCHED_FINAL: performer `02`.

Required isolation:

- performer overlap across roles = 0;
- recording overlap across roles = 0;
- note-id overlap across roles = 0;
- voicing-id overlap across roles = 0.

The same 30 backing-track identities and 15 style identities intentionally occur across performer roles. Therefore unseen-repertoire and unseen-style claims are forbidden for this split.

Development diagnostics may use leave-one-development-performer-out four-fold CV. Validation cannot enter fit. Final cannot enter fit, CV, model selection, or validation.

## GuitarSet v1 candidate boundary

For each accepted derived voicing event:

1. preserve the exact MIDI pitch multiset;
2. use standard tuning `1:E4=64, 2:B3=59, 3:G3=55, 4:D3=50, 5:A2=45, 6:E2=40`;
3. enumerate all exact pitch→string/fret assignments with one note per string;
4. require fret range `0..19`;
5. require the observed GuitarSet realization to be present;
6. exclude single-candidate events from ranking fit/metrics and report them separately.

Candidate construction is independent of H-C fingering, Teacher labels, S2-A preference, historical labels, and model scores.

## GuitarSet frozen feature/model contract

Version:

`GUITARSET-VOICING-FEATURES.v1`

Feature count: `28`

Feature SHA-256:

`05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`

Features encode only static pitch/string/fret geometry, including open-string ratio, fret position/span, string span/adjacency/gaps, mean string, six string-occupancy values, six per-string fret values, and six per-string MIDI values.

Frozen learning pipeline:

```text
observed candidate vs alternative
        ↓
phi(observed) - phi(alternative)
        ↓
mirrored pair rows
        ↓
StandardScaler()
        ↓
LogisticRegression(
    C=1.0,
    fit_intercept=False,
    class_weight=None,
    solver="lbfgs",
    max_iter=2000,
    random_state=0
)
```

No hyperparameter tuning is allowed. For fit, at most 32 alternatives/event are selected by immutable label-independent SHA ordering. Evaluation retains the full candidate set.

Frozen comparator:

`LOW_TOTAL_FRET.v1`

Ascending rank key:

`(sum_fret, max_fret, positive_fret_span, -open_count, string_span, canonical_candidate)`

Protocol SHA-256:

`1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`

## GuitarSet development gate

Development uses leave-one-development-performer-out four-fold CV.

Required:

- >=1000 ambiguous development events;
- macro event Top-1 delta vs comparator >= `+0.03`;
- macro event MRR delta >= `+0.05`;
- Top-1 wins in >=3/4 held-out performers;
- MRR wins in >=3/4 held-out performers;
- 10/10 deterministic reproduction of identities, rows, metrics, and fitted coefficients within the execution environment.

Failure stops the path and keeps validation closed.

## GuitarSet validation/final gates

Validation performer `03` is one-shot and cannot tune features, thresholds, candidate rules, or hyperparameters.

Validation requires:

- >=500 ambiguous events;
- event Top-1 delta >= `+0.02`;
- event MRR delta >= `+0.05`;
- recording-macro Top-1 delta > 0;
- recording-macro MRR delta > 0;
- 2000-repetition recording-block bootstrap, seed 0, with 95% MRR-delta lower bound > 0.

Untouched-final performer `02` remains unopened until:

`DEVELOPMENT_PASS AND VALIDATION_PASS AND MODEL_ARTIFACT_SEALED`

After final opening there is no refit and no tuning. Final PASS yields only:

`ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`

It does not authorize runtime or production.

## S2-A deterministic feature/model boundary

S2-A representation remains exactly 30 target-blind deterministic assignment features. Frozen feature-list SHA-256:

`d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`

Frozen v1 model remains a no-scaler, no-intercept L2 logistic ranker over mirrored pairwise feature differences. Its executable fit/CV/final harness is implemented, but no current corpus is fit-eligible.

Batch01 is permanently diagnostic-only. PR #89 superseded the uncollected Batch02 pairwise path with Teacher Correction v1. PR #90 remains provisional and does not retroactively change frozen S2-A evidence.

## Current authorization boundary

The GuitarSet preregistration freezes the model-development contract but explicitly leaves:

- `training_authorized = false`;
- `checkpoint_authorized = false`;
- `runtime_connection_authorized = false`;
- `final_access_authorized = false`.

Therefore model implementation and deterministic test/evaluation machinery may be developed without altering the protocol, but real project fitting must not begin until the training gate is explicitly opened.

Likewise, checkpoint retention, untouched-final opening, authoritative H-C.v2 replacement, GuitarTab Engine shadow integration, and production remain separate consequential gates.

## Verification baseline

Latest `main` after PR #93:

- CI run #274: PASS;
- unit tests: PASS;
- compile validation: PASS;
- S2-A Batch01 regression workflow run #61: PASS;
- Stage 7B-C2 comparison step: branch-skipped, not counted as PASS.

## Current continuation point

`OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT`

The architecture is ready for the implementation side of the frozen GuitarSet development path. The next model code must preserve the candidate authority, split, feature schema, comparator, model family, and evaluation thresholds exactly as preregistered.

Frozen evidence files remain immutable historical snapshots. Live architecture truth is maintained in this document and `STATUS.md`.