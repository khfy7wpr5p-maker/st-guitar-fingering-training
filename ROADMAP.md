# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0 | Safety + architecture baseline | ✅ contracts + CI |
| 1 | Dataset Contract v1 | ✅ immutable schema + family split rules |
| 2 | Guitar Pro/MusicXML intake + normalizer | ✅ safe parse + stream/tuning/pitch mode |
| 3 | Physical validation + event extraction | ✅ independent pitch/string/fret veto |
| 4 | Dataset Builder v1 | ✅ family split + deterministic candidate generation |
| 5 | First bounded single-note training | ✅ executed; no retained production checkpoint |
| 6 | Chord voicing specialists + context experiments | ✅ research completed through stateless/transition experiments; failed rollout paths retained as negative evidence |
| 7D-A / 7E | Target-blind stateless specialist routing | ✅ positive research direction; relative advantage survived untouched Stage 7E, but no checkpoint retained |
| 7G-A → 7G-D | Teacher-GOLD corpus, blind annotation, pairwise transition | ✅ 556 decisive blind pairwise labels across 40 families |
| 7G-E1 | First real Teacher-GOLD pairwise router | ✅ negative development CV: 70.50% vs 77.88% `always_open_low`; no promotion |
| 7G-E2 | Compact-preference error diagnostic | ✅ dominant error identified: 107 compact false positives vs 66 recovered compact preferences |
| 7G-E3 | Guitar Ergonomics Curriculum | **NEXT — architecture approved for preparation; training not started** |
| 7G-E3-A | Curriculum/data contract | planned: easy→hard tiers, label semantics, source independence, fixed ergonomics descriptors |
| 7G-E3-B | Curriculum task generator | planned: target-blind simple/medium/hard contrast generation with family controls |
| 7G-E3-C | Teacher annotation pilot | planned: faster, simpler Teacher-GOLD collection; no automatic labels masquerading as teacher preference |
| 7G-E3-D | Nested/family-isolated development experiment | planned: test explicit ergonomics + conservative compact detector without post-hoc claims |
| 7G-E3-E | New untouched Teacher-GOLD validation | future: checkpoint criterion must be preregistered before scoring |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | future; blocked until a valid stateless Teacher-GOLD checkpoint exists |

## Current rule

The next step is **not** to retune Stage 7G-E1 on the same 556 labels. Stage 7G-E2 findings may define hypotheses, but any claimed improvement must be evaluated under a separately preregistered nested design or on new family-disjoint Teacher-GOLD data.

Stage 7E remains permanently consumed/evaluation-only and is forbidden for training, tuning, calibration, feature selection, or new validation.
