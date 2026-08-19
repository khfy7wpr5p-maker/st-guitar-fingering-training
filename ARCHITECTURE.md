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
        │ AUTHORITATIVE PHYSICAL BOUNDARY
        ↓
S1-H-A deterministic plausibility                      ✅ MERGED
        ↓
S1-H-B four-finger/barre resource feasibility          ✅ MERGED
        ↓
S1-H-C standard finger-assignment enumeration          ✅ MERGED
        │ AUTHORITATIVE ASSIGNMENT SET
        ↓
S2-A 30D deterministic assignment features             ✅ MERGED PR #78
        ↓
S2-A blind pair + repeat reliability machinery         ✅ MERGED PR #78
        ↓
S2-A fail-closed learned ranker + development CV       ✅ MERGED PR #79
        ↓
S2-A untouched-final evaluation gate                   ✅ MERGED PR #80
        ↓
NEW S2-A FIRST_PASS TEACHER CORPUS                     ⏳ REQUIRED INPUT
        ↓
REPEAT RELIABILITY / CORPUS COVERAGE GATE              🔒
        ↓
REAL S2-A FIT + FAMILY-ISOLATED DEVELOPMENT CV         🔒
        ↓
UNTOUCHED FINAL                                        🔒
        ↓
CHECKPOINT RETENTION REVIEW                            🔒 SEPARATE
        ↓
GuitarTab Engine shadow / production                   🔒 SEPARATE
```

## Authority boundaries

### Physical authority

`valid_chord_voicings()` remains the sole physical pitch/string/fret authority. Learned code cannot create, repair, legalize, or reintroduce a placement outside that set.

### Deterministic ordinary-technique authority

S1-H-A/B/C conservatively narrow and expand the physical set into auditable standard assignments:

- H-A: deterministic plausibility and conservative hard prune;
- H-B: ordinary four-finger/barre resource feasibility;
- H-C: complete standard assignment enumeration under the frozen v1 hand model.

H-C `assignment_id` values are the only objects the S2-A model may rank.

### Learned authority

S2-A is a **ranker only**. Its learned scalar score may order supplied H-C assignments, but it has no authority to change physical validity, H-B feasibility, or H-C assignment construction.

Inference re-generates the H-C set and verifies that ranked output contains exactly the same assignment IDs.

## S2-A v1 learned problem

Target:

`STATIC_STANDARD_FINGERING_NATURALNESS`

The v1 problem intentionally excludes previous/next chord transitions, tempo, style, tone color, right-hand pattern, extended techniques, and player-specific anatomy. Those require later specialist/context stages rather than contamination of the first static ranker.

Teacher supervision is blind pairwise:

- `A`
- `B`
- `EQUAL_OR_UNSURE`

Only decisive FIRST_PASS responses may become fit rows after every evidence gate passes.

## S2-A deterministic feature boundary

The assignment representation is exactly 30 target-blind deterministic features:

- for strings 1..6: used flag, normalized fret, normalized finger = 18 features;
- open-note ratio;
- mean positive fret;
- positive-fret span;
- used-string span;
- internal-string-gap ratio;
- standard-finger count;
- barre count;
- maximum barre span;
- total barre span;
- barre-override-note ratio;
- maximum finger/fret step;
- same-fret multi-finger pair ratio.

Frozen feature-list SHA-256:

`d2c6028891fe62f341463e13d946a71ecf2f506abc99789d0f963ddc1d5c87cf`

Family/source identity, Teacher answer, observed source fingering, previous/next event, prior model score, and consumed historical evidence are not model features.

## S2-A v1 model

The model remains deliberately small and interpretable:

```text
phi(A) - phi(B)
        ↓
mirrored pair rows
        ↓
LogisticRegression(
    L2,
    C=1.0,
    fit_intercept=False,
    class_weight=None,
    solver="lbfgs",
    max_iter=2000,
    random_state=0
)
        ↓
score(assignment) = w · phi(assignment)
```

No learned scaler and no hyperparameter search are allowed in v1.

## Fail-closed real-fit boundary

The existence of `fit_s2a_ranker()` does not make arbitrary data trainable. Before `.fit()` is reached, code verifies the exact FIRST_PASS provenance and the frozen minimums:

- >=40 development families;
- >=200 eligible events;
- >=600 decisive pairs;
- >=150 FINGER_ONLY;
- >=150 MIXED;
- >=100 each NEAR/MID/FAR;
- repeat sample >=max(120,20%);
- exact repeat agreement >=0.85;
- decisive Cohen kappa >=0.75;
- 24–72h repeat interval;
- exact 50% A/B reversal;
- zero development/final family overlap.

A caller-supplied `PASS` string cannot bypass missing sample or provenance requirements.

## Development evaluation

Development uses deterministic five-fold `family_id` isolation. Validation families never contribute fit rows to their fold model.

The comparator is selected only from the frozen LOW_FRET and COMPACT baselines using development macro-family accuracy; an exact comparator tie resolves to LOW_FRET.

The development gate evaluates pairwise accuracy, macro-family accuracy, ROC-AUC, log loss, Brier score, family wins/ties/losses, and FINGER_ONLY/MIXED/NEAR/MID/FAR slices. The whole CV must reproduce identically 10/10 in the same environment.

## Untouched-final boundary

The final evaluator accepts only exact `S2A_STATIC_NATURALNESS_UNTOUCHED_FINAL` provenance and remains closed until development PASS.

The final comparator is inherited from development and cannot be selected or tuned on final labels. Final additionally requires:

- >=20 disjoint final families;
- >=200 decisive final pairs;
- zero development/final family overlap;
- deterministic 2000-resample family-block bootstrap with seed 0;
- 95% bootstrap CI lower bound for model-minus-comparator family accuracy > 0;
- zero assignment-authority violations.

A final PASS yields only `ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW`; it does not serialize, retain, deploy, or integrate a checkpoint.

## Historical evidence quarantine

S2-A may not train from renamed or recycled:

- S1-E pilot/repeat labels;
- S1-G v2 first-pass/repeat evidence;
- historical repeat/reliability rows;
- Stage 7E or E3-E consumed evaluation evidence.

S1-F historical component-fit preparation remains a separate historical path and is not silently reopened by S2-A.

## Verification

- PR #78 / CI #203: 252 tests PASS + compile PASS.
- PR #79 / CI #205: 256 tests PASS + compile PASS.
- PR #80 / CI #207: 260 tests PASS + compile PASS.
- Stage 7B-C2 workflow step was skipped by branch condition and is not counted as PASS evidence.

## Current continuation point

The S2-A software architecture is implemented through untouched-final evaluation. **The next missing resource is legitimate fresh Teacher supervision.**

Real model coefficients must not be fitted until new FIRST_PASS data and its separate REPEAT reliability evidence satisfy every frozen gate. Checkpoint retention and GuitarTab Engine integration remain later, separate decisions.

## Evidence semantics

Frozen preregistration/evidence records describe the state when sealed and are not retroactively rewritten after merge. Current live status belongs in the top-level documentation.
