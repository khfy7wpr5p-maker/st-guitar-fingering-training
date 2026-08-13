# Roadmap

| Stage | Package | Gate |
|---|---|---|
| 0 | Safety + architecture baseline | contracts + CI |
| 1 | Dataset Contract v1 | immutable schema + split rules |
| 2 | Guitar Pro/MusicXML intake + normalizer | safe parse + stream/tuning/pitch mode |
| 3 | Physical validation + event extraction | independent pitch/string/fret veto |
| 4 | Dataset Builder v1 | family split + candidate generation |
| 5 | First bounded training | observed single-note placement ranking |
| 6 | Chord voicing ranking | later |
| 7 | Teacher-GOLD left-hand fingering | later |
| 8 | Context/transition ranking + shadow integration | later |

First training is permitted only after Stages 0–4 pass their regression gates.
