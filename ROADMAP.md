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
| 7G-E3 | Guitar Ergonomics Curriculum | 🟡 active research direction; training not started |
| 7G-E3-A | Curriculum/data contract | ✅ contract prepared: L1–L4, 40 target-blind descriptors, strict provenance split; merge required before authoritative |
| 7G-E3-B | Curriculum task generator | NEXT after E3-A merge: target-blind simple/medium/hard contrast generation with family controls |
| 7G-E3-C | Teacher annotation pilot | planned: faster, simpler blind Teacher-GOLD collection; rule-derived property targets remain non-preference labels |
| 7G-E3-D | Family-isolated development experiment | planned: simple-property pretraining + explicit ergonomics + conservative compact detector; old 556 labels development-only |
| 7G-E3-E | New untouched Teacher-GOLD validation | future: new family-disjoint material; checkpoint criterion must be preregistered before scoring |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | future; blocked until a valid stateless Teacher-GOLD checkpoint exists |

## Current rule

The next step is **not** to retune Stage 7G-E1 on the same 556 labels. Stage 7G-E3-A freezes a curriculum contract in which rule-derived L1/L2 supervision teaches only measurable guitar geometry; it cannot masquerade as Teacher-GOLD preference.

Any claimed preference improvement requires new family-disjoint blind Teacher-GOLD evidence. The existing 556 decisive labels may support exploratory E3 development but are already consumed for E1/E2 and are not a fresh benchmark.

Stage 7E remains permanently consumed/evaluation-only and is forbidden for training, tuning, calibration, feature selection, or new validation.
