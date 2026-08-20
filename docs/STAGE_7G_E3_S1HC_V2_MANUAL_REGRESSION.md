# Stage 7G-E3 — S1-H-C.v2 same-fret/manual Teacher regression

This branch is a regression-only correction path. It does **not** silently mutate the frozen S1-H-C.v1/S2-A evidence.

## Defect

S1-H-B groups same-fret passable targets to compute a minimum fretting-resource lower bound. S1-H-C.v1 treated each H-B lower-bound group as a mandatory same-finger identity group, so ordinary separate-finger shapes could be absent. Example: open E minor, strings 6:0, 5:2, 4:2, 3:0, could force strings 5 and 4 into a two-string barre.

## S1-H-C.v2 correction

- H-B grouping remains a lower bound only.
- Every passable same-fret group may remain one barre group or be partitioned into contiguous target blocks.
- Partition blocks use distinct fingers.
- Total active fretting fingers remains at most four.
- Strict lower-fret/lower-finger ordering remains enforced across strictly different frets.
- Pitch/string/fret validity and upstream S1-H-A/S1-H-B pruning remain unchanged.

## Teacher Correction manual input

The regression UI adds `ELLE DÜZELT`. Teacher enters string, fret and left-hand finger for every required MIDI pitch. Validation is fail closed:

1. same pitch multiset,
2. six-string guitar range,
3. one note per string,
4. string/fret must reproduce the required MIDI pitch,
5. open string uses finger 0,
6. fretted notes use fingers 1..4,
7. the complete placement must match one exact S1-H-C.v2 assignment.

No entry is repaired, guessed, or converted into a training label when validation fails.

## Mandatory E-minor regression

Required pitches: `40, 47, 52, 55`.

The following Teacher solution must validate exactly and contain no barre:

- MIDI 40 — string 6, fret 0, finger 0
- MIDI 47 — string 5, fret 2, finger 2
- MIDI 52 — string 4, fret 2, finger 3
- MIDI 55 — string 3, fret 0, finger 0

## Migration boundary

This branch deliberately exposes `S1-H-C.v2` as a provisional parallel implementation. Existing S2-A source freezes, H-C capacity evidence, feature hashes and ranker preregistration were created against the previous authoritative H-C behavior and are not automatically reclassified. The regression test may be used for Teacher UX evaluation, but merging S1-H-C.v2 into the authoritative training path requires downstream re-audit/re-freeze.
