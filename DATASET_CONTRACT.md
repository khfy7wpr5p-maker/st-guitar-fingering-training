# Dataset Contract v1

Each normalized source event contains:

- `family_id`: source-family identity used to prevent leakage;
- `source_sha256`: exact source-byte digest;
- `musicxml_version` and producer software when available;
- `tuning`: technical string 1..N mapped to sounding open-string MIDI;
- `pitch_mode`: `sounding_exact` or `written_octave_plus_12`;
- measure, onset, duration, voice;
- one or more sounding MIDI pitches;
- observed `string` and `fret` per pitch when the source supplies technical placement;
- physical-validation result.

Observed-placement training eligibility additionally requires:

- one selected guitar/TAB stream;
- complete string/fret placement for the event;
- every placement physically matches the normalized sounding pitch;
- frets in the supported physical range;
- no unresolved pitch-mode disagreement.

## Teacher-GOLD supervision types

Teacher-GOLD data is not the same label source as observed corpus placement.

Current explicit preference types are:

1. **full-candidate preference** — a blind teacher choice from the complete displayed deterministic candidate set;
2. **pairwise preference** — a blind `A` / `B` / `EQUAL_OR_UNSURE` comparison between two frozen physically-valid proposals.

These two semantics must remain separate. Pairwise labels may not be silently promoted into full-candidate Teacher-GOLD records. `EQUAL_OR_UNSURE` is preserved and is never coerced into a binary target.

Raw teacher response rows remain outside Git; repository evidence may store pinned hashes and derived aggregate results.

## Stage 7G-E3 curriculum extension — planned

The proposed Guitar Ergonomics Curriculum adds a **difficulty/teaching tier**, not a new source of physical truth:

- `L1`: easy 2-note contrasts with clearly separated ergonomic geometry;
- `L2`: basic open-string / position / fret-span / string-topology contrasts;
- `L3`: medium 3–4 note chords with several plausible physical candidates;
- `L4`: hard frozen `open_low` ↔ `compact` specialist disagreements.

Curriculum examples may be generated or selected target-blind from pitches, tuning, deterministic candidates, and fixed geometry descriptors. A deterministic rule may be used to create synthetic/pretraining targets only if the target is explicitly marked as **rule-derived**; such a target must never be described as Teacher-GOLD.

Teacher preference supervision still requires an actual blind teacher response.

Planned E3 geometry fields may include open/fretted-note count, positive-fret position and span, same-positive-fret barre-like proxy, string span, adjacency, internal gaps, and pairwise `compact - open_low` deltas. These descriptors do not override physical validity.

## Split and evaluation contract

- family identity is the primary leakage boundary;
- train/validation/test families remain disjoint unless a separately preregistered nested-development design explicitly defines inner folds;
- the consumed 556 decisive Stage 7G pairwise labels are development material, not a new untouched final set;
- Stage 7E is permanently evaluation-only and cannot be reused for training, tuning, calibration, feature selection, or validation;
- any future checkpoint-retention claim requires new, separately controlled evidence with the gate fixed before scoring.
