# Status

## Current repository truth

- Default branch: `main`
- Architecture synchronization base (PR #93 merge): `a46f93861927342ea551e96b2a53859536e18a6f`
- Deterministic runtime baseline through authoritative S1-H-C.v1: `154d8d4c514849535a523ca79ea22b6fae7e77de`
- S1-H-C.v2 same-fret correction: ⏳ **OPEN / PROVISIONAL PR #90 — not authoritative**
- S2-A static fingering ranker machinery through untouched-final evaluation: ✅ implemented
- S2-A Batch01: ✅ 720/720 valid responses, permanently `DIAGNOSTIC_ONLY_NEVER_TRAINING`
- S2-A real fit: ⛔ not executed
- GuitarSet observed-gold ingestion: ✅ merged PR #91
- GuitarSet performer-isolated split/leakage contract: ✅ merged PR #92
- GuitarSet observed-voicing model preregistration: ✅ merged PR #93
- GuitarSet real model fit: ⛔ not executed
- Checkpoint retention: 🔒 closed
- GuitarTab Engine shadow / production integration: 🔒 closed

## Authoritative pipeline and current gates

```text
Guitar Pro / MusicXML
        ↓
safe normalization + event/chord extraction
        ↓
valid_chord_voicings()                         ✅ AUTHORITATIVE PHYSICAL SET
        ↓
S1-H-A deterministic plausibility             ✅
        ↓
S1-H-B four-finger/barre feasibility          ✅
        ↓
S1-H-C.v1 standard finger assignments         ✅ AUTHORITATIVE ASSIGNMENT SET
        │
        ├─ S2-A static fingering naturalness
        │     30D features + blind pair/repeat machinery      ✅
        │     fail-closed ranker / 5-fold CV harness          ✅
        │     untouched-final evaluator                       ✅
        │     Batch01                                         ✅ diagnostic-only
        │     Teacher Correction v1 pilot                     ✅ PR #89
        │     fit-eligible fresh Teacher corpus               🔒
        │     real fit / final / checkpoint                   🔒
        │
        └─ S1-H-C.v2 same-fret correction                     ⏳ PR #90 OPEN

valid_chord_voicings()
        ↓
GuitarSet `*_comp.jams` observed string/fret gold             ✅ PR #91
        ↓
GUITARSET-SPLIT.v1 performer isolation                        ✅ PR #92
        ↓
GUITARSET-VOICING-FEATURES.v1 + model preregistration         ✅ PR #93
        ↓
OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT     ⏳ CURRENT GATE
        ↓
DEVELOPMENT PASS                                              🔒
        ↓
VALIDATION performer 03                                       🔒
        ↓
SEALED DEVELOPMENT MODEL                                      🔒
        ↓
UNTOUCHED_FINAL performer 02                                  🔒
        ↓
CHECKPOINT RETENTION REVIEW                                   🔒 SEPARATE
        ↓
GuitarTab Engine SHADOW / PRODUCTION                          🔒 SEPARATE
```

## S1-H-C.v2 provisional correction

PR #90 exists because Teacher Correction exposed a same-fret grouping defect in authoritative S1-H-C.v1: an H-B same-fret passable group must not automatically imply one mandatory barre/finger in every valid assignment.

The provisional v2 branch:

- retains barre assignments;
- additionally enumerates separate-finger partitions subject to at most four active fretting fingers;
- validates manual Teacher corrections fail-closed against exact pitch/string/fret/finger constraints;
- includes an E-minor regression requiring `6:0/0, 5:2/2, 4:2/3, 3:0/0` with zero barres.

PR #90 is intentionally not merged because authoritative H-C replacement requires explicit downstream H-C-capacity/S2-A evidence re-audit. Existing v1 evidence must not be silently reclassified.

## S2-A Teacher naturalness path

S2-A v1 targets `STATIC_STANDARD_FINGERING_NATURALNESS` over exact S1-H-C assignment IDs.

Implemented and frozen:

- 30 target-blind deterministic features;
- blind pairwise A/B/`EQUAL_OR_UNSURE` machinery;
- separate repeat-reliability provenance;
- fail-closed real-fit gate;
- family-isolated five-fold development CV;
- fixed development comparator policy;
- untouched-final preflight and deterministic family-block bootstrap.

Frozen S2-A feature-list SHA-256:

`d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`

### Batch01 closeout

Batch01 is permanently `DIAGNOSTIC_ONLY_NEVER_TRAINING` because the same 40 AnimeTAB source-family identities had already participated in an earlier Teacher-preference development experiment.

Validated diagnostic result:

- total tasks: 720/720;
- A: 164;
- B: 167;
- `EQUAL_OR_UNSURE`: 389;
- decisive: 331;
- invalid responses: 0;
- duplicate task IDs: 0;
- effective fit rows: **0**.

PR #88 generated a fresh-source Batch02 pairwise package, but PR #89 superseded the uncollected Batch02 pairwise path with Teacher Correction v1. No real S2-A project coefficients have been fitted.

## GuitarSet observed-gold path

### PR #91 — observed data intake

The approved GuitarSet archive is handled fail-closed. The audited dataset contains:

- 180 comp recordings;
- 45,686 raw notes;
- 45,615 accepted notes;
- 71 quarantined notes, all negative-fret rows;
- accepted fret range `0..19`;
- 12,556 conservative derived strum-voicing events using 50 ms distinct-string onset clustering.

The importer rejects unsafe ZIP/archive behavior and malformed musical rows instead of repairing them. Direct note observations and derived voicing clusters are distinct. No finger-number or barre gold is claimed.

### PR #92 — split and leakage contract

`GUITARSET-SPLIT.v1` freezes:

- DEVELOPMENT performers: `00, 01, 04, 05` — 120 recordings / 31,699 accepted notes / 8,330 derived voicings;
- VALIDATION performer: `03` — 30 / 6,722 / 2,016;
- UNTOUCHED_FINAL performer: `02` — 30 / 7,194 / 2,210.

Performer and recording overlap across roles must be zero. Note-id and voicing-id overlap must be zero. The same repertoire/style identities appear across performer roles, so the benchmark is explicitly `UNSEEN_PERFORMER_SEEN_REPERTOIRE`; unseen-repertoire and unseen-style claims are forbidden.

### PR #93 — observed voicing preregistration

Target:

`OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`

Candidate authority:

- preserve exact simultaneous MIDI pitch multiset;
- standard tuning only;
- one note per string;
- frets `0..19`;
- observed placement must exist in the enumerated physical candidate set;
- single-candidate events are excluded from ranking fit/metrics and reported separately.

Frozen model:

- 28 static pitch/string/fret geometry features;
- `StandardScaler()`;
- pairwise observed-vs-alternative objective;
- max 32 deterministically SHA-selected alternatives/event for fit;
- `LogisticRegression(C=1.0, fit_intercept=False, class_weight=None, solver="lbfgs", max_iter=2000, random_state=0)`;
- no hyperparameter tuning;
- comparator `LOW_TOTAL_FRET.v1`.

Feature SHA-256:

`05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`

Protocol SHA-256:

`1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`

## Frozen GuitarSet evaluation gates

Development uses leave-one-development-performer-out four-fold CV and requires at least 1000 ambiguous events, macro Top-1 delta >= `+0.03`, macro MRR delta >= `+0.05`, wins in at least 3/4 held-out performers for both metrics, and 10/10 deterministic reproduction.

Validation performer `03` is one-shot and cannot tune the model. It requires at least 500 ambiguous events, event Top-1 delta >= `+0.02`, event MRR delta >= `+0.05`, positive recording-macro Top-1/MRR deltas, and a 2000-repetition recording-block bootstrap whose 95% MRR-delta lower bound is > 0.

Untouched-final performer `02` stays closed until `DEVELOPMENT_PASS AND VALIDATION_PASS AND MODEL_ARTIFACT_SEALED`. There is no refit after validation and no tuning after final opening. Final PASS yields only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`.

## Current authorization boundary

PR #93 is preregistration evidence, not training permission:

- `training_authorized = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`
- `final_access_authorized = false`

Therefore documentation changes or model-implementation code must not silently start real fitting, open validation/final labels, retain a checkpoint, or connect runtime/production.

## Verification

PR #93 merge-state evidence:

- `ci` run #274: **success**;
- unit tests: **success**;
- compile validation: **success**;
- `s2a-teacher-batch01` run #61: **success**;
- Stage 7B-C2 comparison step: skipped by branch condition and not counted as PASS.

PR #93 also records E-minor physical candidate regression, frozen protocol/evidence identity regression, pinned S2-A Batch01 regression, and zero inline review threads. External Codex review was unavailable due review-usage limits; no external-review PASS is claimed.

## Current controlled continuation point

`OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT`

Engineering may implement the frozen GuitarSet model-development path and its deterministic evaluation/test harnesses without changing the preregistered target, feature schema, split, comparator, or gates. Real `.fit()` on project data remains closed until an explicit training authorization opens it.

Checkpoint retention, untouched-final opening, S1-H-C.v2 authority replacement, GuitarTab Engine shadow integration, and production remain separate consequential gates.

## Evidence semantics

Frozen preregistration/evidence JSON files are immutable historical snapshots. Live status is maintained here; new decisions must be recorded as new evidence rather than rewriting historical records.
