# Stage 7G-E3 — S2-A.v2 GuitarSet Fixed-Voicing Single-Session Teacher Fit

## Decision

S2-A.v1 remains immutable historical preregistration/evidence, but its high-volume pairwise real-Teacher collection path is superseded for new real-fit work.

S2-A.v2 asks one narrower question:

> Given one already-fixed, physically valid guitar string/fret voicing, which exact ordinary left-hand fingering is most natural?

GuitarSet supplies observed real-guitar **string/fret geometry only**. It supplies no finger-number or barre label. The Teacher therefore does not repeat the already-solved voicing-selection problem.

## One human session

The package contains exactly:

- 200 DEVELOPMENT original tasks;
- 30 hidden same-session reliability repeats;
- 60 UNTOUCHED_FINAL tasks;
- 290 total presentations.

Every task shows the fixed string/fret placement and **all** S1-H-C.v2 assignments when there are 2..8 manageable alternatives. There is no A/B pair spam and no manual numeric entry.

Allowed answers:

- select one exact assignment;
- `EQUAL_OR_UNSURE`;
- `REJECT_TASK`.

One selected assignment produces selected-vs-every-other pairwise training constraints internally. Repeat rows are reliability-only. Final rows are evaluation-only.

At the end of the same HTML session the browser exports two separate files:

1. `DEVELOPMENT` — originals plus hidden repeats;
2. `FINAL SEALED` — untouched-final answers.

The final file must not be inspected by the fit path until DEVELOPMENT PASS and the all-development model artifact is sealed.

## H-C.v2 safety boundary

The old provisional PR #90 exposed a real same-fret grouping defect in H-C.v1. H-C.v2 treats an H-B same-fret group as a resource lower bound, not a mandatory barre identity, and enumerates separate-finger partitions under the four-finger limit.

This work ports that corrected enumerator onto current `main` but scopes its authority to the new S2-A.v2 fixed-voicing research path. It does **not** silently rewrite old H-C.v1/S2-A.v1 evidence or globally replace the current authoritative runtime assignment contract.

The old PR #90 manual-entry UI is not reused. Its review finding that blank numeric fields could become JavaScript zeroes is removed by design: S2-A.v2 accepts only selections from prevalidated exact assignments.

## GuitarSet boundary

Only the exact approved annotation archive is accepted:

`06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe`

The builder preserves existing fail-closed archive/JAMS sanitization. GuitarSet observed placement is used only to anchor a fixed pitch/string/fret voicing. Performer, recording, track/style identity, model scores, baseline scores, and historical Teacher answers are withheld from the Teacher package.

## Family-isolated Teacher split

The 30 GuitarSet backing-track identities are the leakage unit for this new Teacher target.

A deterministic pre-label SHA split assigns:

- 24 track families to DEVELOPMENT;
- 6 disjoint track families to UNTOUCHED_FINAL.

Development/final track-family overlap and semantic fixed-voicing overlap must both be zero. The final claim is therefore an unseen-repertoire Teacher test for fixed-voicing fingering preference; it is not the earlier GuitarSet performer-split claim.

## Features and model

S2-A.v2 reuses the exact deterministic target-blind 30D assignment feature formulas. It does not reuse any old Teacher labels.

The model is frozen before collection:

```text
selected assignment vs each unselected assignment
        ↓
phi(selected) - phi(other)
        ↓
exact mirrored positive/negative rows
        ↓
LogisticRegression(
    penalty="l2",
    C=1.0,
    fit_intercept=False,
    class_weight=None,
    solver="lbfgs",
    max_iter=2000,
    random_state=0
)
```

No scaler and no hyperparameter search are allowed.

Comparator `MIN_MECHANICAL_COMPLEXITY.v1` orders assignments by barre count, total barre span, distinct positive-finger count, summed finger IDs, max finger ID, then stable assignment ID.

## Reliability gate

Thirty hidden repeats are interleaved in the same session with independently shuffled option order. Their previous answers are not shown.

PASS requires exact assignment-or-response-class agreement >= 0.85. Repeat rows never become training rows.

## DEVELOPMENT gate

Only selected DEVELOPMENT originals are fit-eligible. Required before final may open:

- >=160 decisive original tasks;
- >=20 development track families;
- >=200 selected-vs-other preference constraints;
- reliability PASS;
- deterministic five-fold family-isolated CV;
- Top-1 >= 0.60;
- MRR >= 0.75;
- macro-family Top-1 >= 0.60;
- macro-family Top-1 delta vs comparator >= +0.05;
- family wins > losses;
- 10/10 identical deterministic CV reproduction.

Only a DEVELOPMENT PASS permits one all-development fit and sealed model artifact.

## UNTOUCHED_FINAL gate

The sealed final export is accepted only with the exact sealed DEVELOPMENT artifact.

Required:

- >=50 decisive final tasks;
- all 6 reserved final track families represented;
- Top-1 >= 0.60;
- MRR >= 0.75;
- macro-family Top-1 delta vs comparator >= +0.05;
- family wins > losses;
- 2000-repeat family-block bootstrap, seed 0, with the 95% MRR-delta lower bound > 0.

Final PASS means only `ELIGIBLE_FOR_SEPARATE_CHECKPOINT_RETENTION_REVIEW`. It does not authorize runtime or production.

## Historical evidence rule

No existing evidence is reclassified:

- Batch01 stays `DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- Teacher Correction v1 pilot stays non-training;
- GuitarSet Teacher Voicing pilot stays non-training;
- old S2-A.v1 final/evidence remains immutable;
- old H-C.v1 identities are not rewritten.

S2-A.v2 starts a new, predeclared supervision contract instead of laundering historical labels into training.
