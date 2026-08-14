# Architecture

```text
Guitar Pro / MusicXML source (quarantine)
        ↓
Safe XML intake
        ↓
Notation/TAB stream selection
        ↓
Tuning + transpose/pitch-semantics normalization
        ↓
Event/chord extraction
        ↓
Independent physical pitch ↔ string/fret validation
        ↓
Deterministic physically-valid candidate generator  ← authoritative boundary
        ↓
Frozen stateless voicing specialists
(open_low / compact / research-only alternatives)
        ↓
Blind Teacher-GOLD preference supervision
        ↓
Target-blind specialist router / preference model
        ↓
Family-isolated development validation
        ↓
Error diagnostics and hypothesis generation
        ↓
Stage 7G-E3 Guitar Ergonomics Curriculum (planned, not trained)
  ├─ L1 easy 2-note contrasts
  ├─ L2 basic ergonomic contrasts
  ├─ L3 medium 3–4 note chords
  └─ L4 hard open_low ↔ compact disagreements
        ↓
Explicit ergonomics representation (planned)
  ├─ left-hand position/span proxies
  ├─ open/fretted-note geometry
  ├─ barre-like same-fret proxy
  ├─ string span / adjacency / internal gaps
  └─ compact-minus-open_low proposal deltas
        ↓
Conservative compact detector (planned hypothesis)
  ├─ default = open_low
  └─ switch to compact only with validated evidence
        ↓
New disjoint Teacher-GOLD / separately preregistered nested evaluation
        ↓
Future checkpoint-retention gate
        ↓
Future GuitarTab Engine SHADOW integration
```

## Authority boundary

1. Deterministic guitar rules own physical validity. AI may never manufacture a valid-looking placement outside the deterministic candidate set.
2. Learned specialists, routers, curriculum models, and future ergonomics models may score/rank/route only candidates that already passed physical validation.
3. Source XML pitch is not trusted blindly. Sounding pitch is independently recomputed from tuning + string + fret whenever observed technical placement exists.
4. Standard-notation and TAB staves representing the same event are one lineage, not two labels.
5. Written-guitar octave conventions are recorded explicitly and are never silently mixed with sounding pitch.
6. Dataset families never cross train/validation/test boundaries.
7. Observed source placement and Teacher-GOLD preference are different supervision types. Pairwise Teacher-GOLD is also distinct from richer full-candidate preference labels.
8. `open_low` is the current strongest simple Teacher-GOLD baseline. The first Teacher-GOLD router is a negative development result and is not a retained checkpoint.
9. Stage 7E is permanently consumed/evaluation-only and may not be reused for training, tuning, calibration, feature selection, or new validation.
10. Findings from Stage 7G-E2 are hypothesis generators only. They may shape a preregistered E3 design, but cannot be presented as fresh validation on the same 556 decisive labels.
11. Production integration remains closed until a separately preregistered checkpoint gate passes on new untouched evidence.

## Current learning state

The system has demonstrated that target-blind specialist routing can learn useful signal from corpus behavior, including a relative advantage on an untouched Stage 7E corpus. Teacher-GOLD supervision then exposed a different objective: teacher guitaristic preference is more conservative than the existing balanced router. On 556 decisive blind pairwise labels, the E1 Teacher-GOLD router reached 70.50% event-weighted agreement versus 77.88% for `always_open_low`.

Stage 7G-E2 identified the dominant failure: the E1 router recovered 66 genuine `compact` preferences but introduced 107 `compact` false positives, a net loss of 41 correct decisions. The next architecture therefore shifts from a symmetric binary router toward curriculum learning plus explicit ergonomics and conservative fallback behavior. This is a proposed research direction, not a promoted model.
