# Stage 7G-E3 — GuitarSet Split & Leakage Contract v1

## Purpose

Freeze the data roles for `GUITARSET-OBSERVED-GOLD.v1` before any model fit.

The corpus contains 6 performers. Each performer recorded the same 30 backing-track identities covering the same 15 style identities. Therefore the primary benchmark is explicitly:

`UNSEEN_PERFORMER_SEEN_REPERTOIRE`

This contract does **not** claim unseen-repertoire or unseen-style generalization.

## Frozen performer roles

The split uses no Teacher labels, model scores, voicing quality metrics, note counts, or quarantine rates.

Performers are ranked only by:

`SHA256("GUITARSET-SPLIT.v1|" + source_archive_sha256 + "|" + performer_id)`

For the sealed archive the rank is:

1. `02` — UNTOUCHED_FINAL
2. `03` — VALIDATION
3. `05`
4. `04`
5. `00`
6. `01`

The remaining four performers are DEVELOPMENT, stored canonically as `00, 01, 04, 05`.

| Role | Performers | Recordings | Accepted notes | Derived voicings |
|---|---|---:|---:|---:|
| DEVELOPMENT | 00, 01, 04, 05 | 120 | 31,699 | 8,330 |
| VALIDATION | 03 | 30 | 6,722 | 2,016 |
| UNTOUCHED_FINAL | 02 | 30 | 7,194 | 2,210 |

## Hard leakage boundaries

The following must be zero across roles:

- performer overlap;
- recording/member overlap;
- direct note-id overlap;
- derived voicing-id overlap.

A row from VALIDATION cannot be used for model fit. A row from UNTOUCHED_FINAL cannot be used for fit, development CV, threshold/model selection, feature selection, or validation.

Development-only diagnostics may use leave-one-development-performer-out 4-fold CV.

## Intentional repertoire/style matching

All roles contain the same 30 backing-track identities and the same 15 styles. This is intentional covariate matching so the final question is narrowly:

> Given repertoire/style conditions seen during development, does the string/fret model generalize to a guitarist whose performances were never available to fit or model selection?

Therefore:

- shared track identity count across roles = 30;
- shared style identity count across roles = 15;
- `unseen repertoire` claim = forbidden;
- `unseen style` claim = forbidden.

This overlap must never be described as fully independent repertoire validation.

## Why not random event/recording splitting?

Randomly splitting events or recordings would put performances from the same guitarist into multiple roles and would substantially overstate generalization. The performer is therefore the top-level blocking unit.

A simultaneously performer-disjoint and backing-track-disjoint split is not used here because every performer covers the same 30 tracks; forcing both axes into one small final set would discard most of the corpus and change the primary benchmark. Unseen-repertoire generalization requires a separately preregistered audit or an external corpus.

## Scientific boundary

This stage freezes roles only. It does not train a voicing model and does not authorize:

- training;
- checkpoint retention;
- runtime connection;
- untouched-final access.

The next gate is `OBSERVED_VOICING_MODEL_PREREGISTRATION`, where the prediction target, candidate set, model family, metrics, validation threshold and final opening rule must be frozen before any fit.
