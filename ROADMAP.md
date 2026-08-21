# Roadmap

## Live roadmap

Current `main` after merged PR #93: `a46f93861927342ea551e96b2a53859536e18a6f`.

| Stage / path | Package | State / gate |
|---|---|---|
| 0–4 | safety, dataset, intake, normalization, deterministic physical engine | ✅ complete |
| 5–7E | bounded placement/routing research + untouched evaluation | ✅ research complete; untouched evidence consumed |
| 7G-E1/E2/E3 | Teacher-GOLD ergonomics research | ✅ historical research complete |
| 7G-E3-S1-H-A | deterministic guitaristic plausibility | ✅ merged PR #71 |
| 7G-E3-S1-H-B | four-finger/barre resource feasibility | ✅ merged PR #73 |
| 7G-E3-S1-H-C.v1 | standard finger-assignment enumeration | ✅ authoritative baseline, merged PR #74 |
| S2-A protocol | static learned fingering-ranker preregistration | ✅ merged PR #77 |
| S2-A data/features/reliability | 30D features + blind pair/repeat machinery | ✅ merged PR #78 |
| S2-A ranker/development harness | fail-closed fit + family-isolated CV | ✅ merged PR #79 |
| S2-A untouched-final harness | fixed final comparator + family-block bootstrap | ✅ merged PR #80 |
| S2-A Batch01 | 720 blind Teacher responses | ✅ diagnostic-only, zero fit rows |
| S2-A fresh-source pairwise Batch02 | frozen/generated | ⛔ superseded before collection by PR #89 |
| Teacher Correction v1 | correction/reject pilot | ✅ merged PR #89 |
| S1-H-C.v2 | same-fret split + manual correction regression | ⏳ PR #90 open; provisional only |
| GuitarSet observed gold | safe `*_comp.jams` ingestion | ✅ merged PR #91 |
| GuitarSet split/leakage | performer-isolated `GUITARSET-SPLIT.v1` | ✅ merged PR #92 |
| GuitarSet observed-voicing prereg | 28D features + frozen model/eval protocol | ✅ merged PR #93 |
| GuitarSet development implementation | executable fit/CV/evaluation path | ⏳ NEXT ENGINEERING MILESTONE |
| GuitarSet real development fit | frozen preregistered model on DEVELOPMENT performers | 🔒 training authorization required |
| GuitarSet validation | one-shot performer 03 | 🔒 requires development PASS |
| GuitarSet untouched final | performer 02 | 🔒 requires development + validation PASS + sealed model |
| Checkpoint retention | retention/promotion review | 🔒 separate gate |
| Sequence/transition ranker | contextual fingering specialist | 🔒 later stage |
| GuitarTab Engine integration | shadow / production | 🔒 separate gate |

## Current position

The repository has moved beyond the earlier state where fresh S2-A Teacher data was the only next step. S2-A remains scientifically blocked from real fitting, but a separate real-guitar supervision path is now prepared through GuitarSet.

```text
AUTHORITATIVE PHYSICAL PATH
valid_chord_voicings()
        ↓
GuitarSet observed-gold intake             ✅ PR #91
        ↓
performer-isolated split/leakage            ✅ PR #92
        ↓
28D features + model preregistration        ✅ PR #93
        ↓
DEVELOPMENT IMPLEMENTATION                  ⏳ CURRENT ENGINEERING MILESTONE
        ↓
REAL DEVELOPMENT FIT                         🔒 training gate
        ↓
DEVELOPMENT PASS                             🔒
        ↓
VALIDATION performer 03                      🔒
        ↓
SEALED DEVELOPMENT MODEL                     🔒
        ↓
UNTOUCHED_FINAL performer 02                 🔒
        ↓
CHECKPOINT REVIEW                            🔒
        ↓
GuitarTab Engine SHADOW / PRODUCTION         🔒
```

In parallel:

```text
S1-H-C.v1 authoritative assignments
        ↓
S2-A static naturalness machinery            ✅ implemented
        ↓
Batch01                                      ✅ diagnostic-only
        ↓
Teacher Correction v1                       ✅ PR #89
        ↓
fit-eligible fresh Teacher corpus            🔒 not available

S1-H-C.v2 correction                         ⏳ PR #90 open
        ↓
mandatory downstream H-C/S2-A re-audit       🔒 before authority replacement
```

## GuitarSet milestone details

### PR #91 — observed-gold intake

Completed:

- exact approved archive identity sealing;
- fail-closed ZIP/member/path/compression limits;
- deterministic string mapping and physical fret recomputation;
- malformed/non-physical rows quarantined rather than repaired;
- audited 180 recordings / 45,686 raw notes / 45,615 accepted notes / 71 quarantined rows;
- 12,556 conservative derived strum-voicing events;
- no finger-number or barre-gold claim.

### PR #92 — split/leakage freeze

Completed:

- DEVELOPMENT performers `00,01,04,05`;
- VALIDATION performer `03`;
- UNTOUCHED_FINAL performer `02`;
- zero performer/recording/note/voicing overlap across roles;
- explicit benchmark label `UNSEEN_PERFORMER_SEEN_REPERTOIRE`;
- validation excluded from fit;
- final excluded from fit/CV/model selection/validation.

### PR #93 — model preregistration

Frozen before fit:

- target `OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`;
- physical exact candidate set, standard tuning, frets `0..19`;
- 28D static pitch/string/fret feature schema;
- pairwise observed-vs-alternative objective;
- deterministic cap of 32 alternatives/event for fit;
- `StandardScaler()` + no-intercept logistic regression;
- no hyperparameter search;
- fixed `LOW_TOTAL_FRET.v1` comparator;
- development, validation and untouched-final thresholds;
- 10/10 determinism requirement;
- checkpoint/shadow/production kept outside model-development authorization.

Feature SHA-256:

`05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`

Protocol SHA-256:

`1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`

## Next engineering milestone

Implement the preregistered GuitarSet development path without changing the frozen scientific contract:

1. regenerate/validate physical candidate sets from DEVELOPMENT events;
2. compute the exact 28D feature representation;
3. produce deterministic observed-vs-alternative mirrored pair rows;
4. implement the fixed scaler + logistic model constructor;
5. implement leave-one-development-performer-out four-fold evaluation;
6. implement the fixed `LOW_TOTAL_FRET.v1` comparison and Top-1/MRR/Recall@3 reporting;
7. implement 10/10 deterministic reproduction checks;
8. add negative security/provenance/leakage tests and full regression coverage;
9. keep real project `.fit()` fail-closed until training authorization is explicit.

## Development gate after training authorization

The frozen GuitarSet development gate requires:

- >=1000 ambiguous development events;
- macro Top-1 delta vs comparator >= `+0.03`;
- macro MRR delta >= `+0.05`;
- Top-1 wins in >=3/4 held-out performers;
- MRR wins in >=3/4 held-out performers;
- 10/10 deterministic reproduction.

Failure stops the path and validation remains closed.

## Validation/final sequence

Only a development PASS may open one-shot validation on performer `03`. Validation cannot tune the model and must satisfy the frozen event/recording/bootstrap thresholds.

Only `DEVELOPMENT_PASS AND VALIDATION_PASS AND MODEL_ARTIFACT_SEALED` may open untouched-final performer `02`. There is no refit after validation and no tuning after final opening.

Final PASS means only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY`.

## Promotion gates remain separate

None of the following is implied by model implementation or even a successful final evaluation:

- retained/promoted checkpoint;
- authoritative replacement of S1-H-C.v1 by PR #90/v2;
- sequence-level modeling;
- GuitarTab Engine shadow integration;
- production integration.

## Verification baseline

Latest `main` after PR #93:

- CI run #274: PASS;
- unit tests: PASS;
- compile validation: PASS;
- S2-A Batch01 regression workflow run #61: PASS;
- Stage 7B-C2 comparison remains branch-skipped and is not counted as PASS evidence.

Frozen preregistration/evidence files remain immutable historical snapshots. This roadmap and the other top-level live documents describe current repository truth.