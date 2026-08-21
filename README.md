# st-guitar-fingering-training

Training, evaluation, and deterministic guitar-fingering research for polyphony, voicing, string/fret selection, and learned guitaristic ranking.

## Core rule

Physical validity remains deterministic and authoritative. Learned systems may rank only candidates already emitted by the active deterministic authority boundary; they may never create, repair, legalize, or silently reintroduce an invalid/pruned placement.

## Live repository position

Current `main` baseline after merged PR #93:

`a46f93861927342ea551e96b2a53859536e18a6f`

The repository now has two deliberately separated learned-research paths:

1. **S2-A static fingering naturalness** over exact S1-H-C assignment IDs, using blind Teacher supervision. The executable ranker/CV/final-evaluation machinery is implemented, but no fit-eligible fresh Teacher corpus has passed the frozen evidence gate. Batch01 is diagnostic-only and contributes zero fit rows.
2. **GuitarSet observed voicing v1** over physically exact string/fret realizations for a fixed MIDI pitch multiset. Real GuitarSet observations, performer-isolated split/leakage policy, feature schema, comparator, model family, and development/validation/final gates are now preregistered through PR #93. No real model fit has been executed.

PR #90 remains open and provisional. It explores S1-H-C.v2 same-fret splitting/manual Teacher correction and must not replace authoritative S1-H-C.v1 until its downstream H-C/S2-A consequences are explicitly re-audited.

## Authoritative architecture

```text
Guitar Pro / MusicXML
  → safe normalization
  → deterministic pitch/string/fret validation
  → valid_chord_voicings()                         [authoritative physical set]
  → S1-H-A deterministic plausibility              ✅
  → S1-H-B four-finger/barre feasibility           ✅
  → S1-H-C v1 standard finger assignments          ✅ authoritative assignment set
       │
       ├─ S2-A static fingering naturalness
       │    → 30D deterministic assignment features            ✅ PR #78
       │    → blind pair/repeat machinery                      ✅ PR #78
       │    → fail-closed ranker + development CV             ✅ PR #79
       │    → untouched-final evaluator                       ✅ PR #80
       │    → Batch01 human evidence                          ✅ diagnostic-only
       │    → Teacher Correction v1 pilot                     ✅ PR #89
       │    → fit-eligible fresh Teacher supervision          🔒 not yet available
       │    → real S2-A fit / untouched final / checkpoint    🔒
       │
       └─ PR #90 S1-H-C.v2 experiment                         ⏳ OPEN / PROVISIONAL

valid_chord_voicings()
  └─ GuitarSet observed voicing v1
       → fail-closed real GuitarSet ingestion                 ✅ PR #91
       → performer-isolated split + leakage contract          ✅ PR #92
       → 28D static pitch/string/fret feature contract        ✅ PR #93
       → frozen pairwise logistic model preregistration       ✅ PR #93
       → development implementation + fit                     ⏳ NEXT GATE
       → one-shot validation performer 03                     🔒
       → sealed development model                             🔒
       → untouched-final performer 02                         🔒
       → checkpoint retention review                          🔒 separate gate
       → GuitarTab Engine shadow / production                 🔒 separate gate
```

## GuitarSet observed-gold path

PR #91 added a fail-closed importer/sanitizer for the approved GuitarSet `*_comp.jams` archive. The audited archive contains 180 recordings, 45,686 raw notes, 45,615 accepted notes, 71 quarantined negative-fret rows, and 12,556 conservative derived strum-voicing events. This path provides observed string/fret placement only; it does not claim left-hand finger-number or barre gold.

PR #92 froze `GUITARSET-SPLIT.v1` as an `UNSEEN_PERFORMER_SEEN_REPERTOIRE` benchmark:

- DEVELOPMENT performers: `00, 01, 04, 05`;
- VALIDATION performer: `03`;
- UNTOUCHED_FINAL performer: `02`;
- performer/recording/note/voicing overlap across roles must be zero;
- shared backing-track/style identities mean unseen-repertoire or unseen-style claims are forbidden.

PR #93 preregistered target `OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET` with a frozen 28D static geometry feature schema, `StandardScaler()` + no-intercept logistic regression, fixed `LOW_TOTAL_FRET.v1` comparator, deterministic alternative sampling, explicit development/validation/final gates, and no hyperparameter tuning.

Frozen GuitarSet feature SHA-256:

`05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`

Frozen GuitarSet protocol SHA-256:

`1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`

Current authorization remains fail-closed:

- `training_authorized = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`
- `final_access_authorized = false`

The next gate is `OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT`.

## S2-A static fingering path

S2-A v1 targets `STATIC_STANDARD_FINGERING_NATURALNESS` for one isolated chord under ordinary four-finger left-hand technique. It ranks only exact S1-H-C assignment IDs and cannot change physical validity or candidate construction.

Frozen S2-A feature-list SHA-256:

`d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`

Batch01 collected 720/720 valid blind responses but is permanently `DIAGNOSTIC_ONLY_NEVER_TRAINING` because its source-family identities had already participated in earlier Teacher-preference development. Effective fit-row contribution is therefore zero.

PR #89 superseded the uncollected Batch02 pairwise path with a Teacher Correction v1 pilot. PR #90 then introduced a provisional S1-H-C.v2 correction for same-fret grouping; it remains intentionally unmerged pending downstream audit.

## Verification

Latest `main` CI after PR #93 merge:

- workflow `ci` run #274: **PASS**;
- unit-test step: **PASS**;
- compile validation: **PASS**;
- `s2a-teacher-batch01` run #61: **PASS**;
- Stage 7B-C2 comparison step remains branch-skipped and is not counted as PASS evidence.

PR #93 additionally records E-minor physical-candidate regression, frozen protocol/evidence identity regression, pinned S2-A Batch01 regression, and no unresolved inline review threads. External Codex review was unavailable because the review-usage limit was exhausted; no external-review PASS is claimed.

## Current continuation point

The most advanced autonomous engineering path is now the GuitarSet observed-voicing model implementation. Development code, deterministic generation, evaluation harnesses, negative tests, regression tests, and CI can progress without changing the frozen preregistration.

Real training, checkpoint retention, untouched-final opening, GuitarTab Engine shadow connection, and production activation remain separate fail-closed gates and are not authorized by documentation synchronization.

See `ARCHITECTURE.md`, `STATUS.md`, `ROADMAP.md`, `SAFETY.md`, `DATASET_CONTRACT.md`, `docs/STAGE_7G_E3_GUITARSET_SPLIT_LEAKAGE_V1.md`, and `docs/STAGE_7G_E3_GUITARSET_OBSERVED_VOICING_MODEL_PREREG_V1.md`.