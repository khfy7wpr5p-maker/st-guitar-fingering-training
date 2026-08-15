# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0 | Safety + architecture baseline | ✅ contracts + CI |
| 1 | Dataset Contract v1 | ✅ immutable schema + family split rules |
| 2 | Guitar Pro/MusicXML intake + normalizer | ✅ safe parse + stream/tuning/pitch mode |
| 3 | Physical validation + event extraction | ✅ independent pitch/string/fret veto |
| 4 | Dataset Builder v1 | ✅ family split + deterministic candidate generation |
| 5 | First bounded single-note training | ✅ executed; no retained production checkpoint |
| 6 | Chord voicing specialists + context experiments | ✅ research completed; failed rollout paths retained as negative evidence |
| 7D-A / 7E | Target-blind stateless specialist routing | ✅ relative research advantage survived Stage 7E; Stage 7E now permanently consumed |
| 7G-A → 7G-D | Teacher-GOLD corpus + blind pairwise annotation | ✅ 556 decisive labels / 40 families; 38 richer full-candidate labels remain separate |
| 7G-E1 | First real Teacher-GOLD pairwise router | ✅ negative: 70.50% vs 77.88% `always_open_low`; no promotion |
| 7G-E2 | Compact-preference error diagnostic | ✅ 107 compact false positives vs 66 recovered compact preferences |
| 7G-E3-A | Guitar ergonomics curriculum contract | ✅ merged: L1–L4 + frozen 40 target-blind descriptors |
| 7G-E3-B | Target-blind curriculum generator | ✅ merged |
| 7G-E3-B-R1 | First sealed curriculum batch | ✅ 400 tasks, all 40 development families, prior-task overlap 0 |
| 7G-E3-C | Teacher-GOLD Batch01 response seal | ✅ 400/400 validated; 399 decisive; open_low=311, compact=88, equal=1 |
| 7G-E3-D | Conservative compact-gate training protocol | ✅ merged/frozen before fit; `open_low` default; nested family-isolated CV + inner-only threshold selection |
| 7G-E3-D-R1A | Colab execution harness | ✅ merged at `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`; no real fit executed |
| 7G-E3-D-R1B | Exact execution SHA pin | ✅ notebook pinned to R1A merge SHA; one-line pin only |
| 7G-E3-D-R1 | Manual Colab development execution | **next**: pinned notebook → hash/split preflight → STOP → manual TRAIN → frozen nested-CV evidence |
| 7G-E3-E | New untouched Teacher-GOLD validation | future: new family-disjoint material only if E3-D development gate is positive |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | future; blocked until a valid untouched-validation checkpoint gate passes |

## Immediate next step

Run the already-pinned Stage 7G-E3-D-R1 notebook manually in Google Colab. The notebook itself comes from current `main`, while its execution code is intentionally pinned to R1A merge SHA `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`.

The user-visible run sequence is:

1. open `notebooks/ST_Guitar_Stage7G_E3_D_R1_Colab.ipynb` from current `main` in Colab;
2. let the notebook clone the repository and checkout exact execution SHA `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3`;
3. install the pinned repository package and print dependency versions;
4. upload the sealed curriculum package and completed Teacher-GOLD choice export;
5. verify all preregistered SHA-256 values, 400 task IDs, 40 families, L1/L2/L3/L4 counts, 399 decisive rows, finite frozen features, and family-isolated splits;
6. STOP before training and inspect the preflight output;
7. only after preflight passes, manually execute the separate TRAIN cell;
8. run only the frozen 5×4 nested family-isolated evaluation;
9. export aggregate evidence with `checkpoint_retained=false` and `production_integration=false`.

No E3-D result has been observed yet. If preflight fails, do not run TRAIN.

## Scientific rules that remain fixed

- Deterministic guitar physics owns physical validity.
- `open_low` is the default decision; `compact` is a gated alternative.
- The E3-D fit uses only the new E3 Batch01 399 decisive pairwise Teacher-GOLD rows.
- The earlier 556 decisive E1/E2 labels are consumed hypothesis-development evidence and are excluded from the E3-D fit.
- The first 38 full-candidate Teacher-GOLD choices remain a separate semantic label type.
- Stage 7E is permanently forbidden for training, tuning, calibration, feature selection, or new validation.
- Threshold selection occurs only on inner out-of-fold predictions; outer labels cannot change thresholds.
- E3-D is development CV, not untouched validation and cannot authorize checkpoint retention or production.
- A positive E3-D result authorizes only the design of E3-E; E3-E must use new family-disjoint blind Teacher-GOLD material.

## Development-control rule

Routine read-only analysis, branch creation, implementation inside an already approved bounded stage, tests, CI checks, and PR preparation do not require separate approval messages. One explicit approval remains at meaningful risk gates rather than at every mechanical step.

Code/model-behavior merges, checkpoint retention/promotion, production or shadow integration, destructive history operations, and other materially irreversible changes still require an explicit gate. Documentation-only maintenance explicitly requested by the user may be implemented and merged under that same bounded authorization after scope and CI are verified.
