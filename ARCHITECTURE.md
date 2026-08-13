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
Dataset record builder
        ↓
Family-level train/validation split
        ↓
Physically-valid candidate generator
        ↓
Observed-placement ranking baseline
        ↓
Validation only
        ↓
Future teacher-GOLD preference layer
        ↓
Future GuitarTab Engine SHADOW integration
```

## Authority boundary

1. Deterministic guitar rules own physical validity.
2. The learned layer may score/rank only candidates that already passed physical validation.
3. Source XML pitch is not trusted blindly. Sounding pitch is independently recomputed from tuning + string + fret.
4. Standard-notation and TAB staves representing the same event are one lineage, not two labels.
5. Written-guitar octave conventions are recorded, not silently mixed with sounding pitch.
6. Dataset families never cross train/validation/test boundaries.
7. Teacher preference is a future explicit label source and is distinct from observed corpus behavior.
