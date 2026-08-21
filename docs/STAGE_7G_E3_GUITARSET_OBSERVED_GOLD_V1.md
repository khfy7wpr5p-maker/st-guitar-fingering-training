# Stage 7G-E3 — GuitarSet Comp Observed Gold v1

## Purpose

Use GuitarSet `*_comp.jams` annotations as a real-guitar observation source for string/fret learning without pretending that the corpus contains left-hand finger numbers or barre labels.

This stage is a **data intake and sanitization gate only**. It does not fit a model, authorize checkpoint retention, or change S1-H-C.

## Frozen source semantics

`data_source` 0..5 is interpreted as the six hexaphonic strings from low to high:

| data_source | guitar string | open MIDI |
|---:|---:|---:|
| 0 | 6 | 40 |
| 1 | 5 | 45 |
| 2 | 4 | 50 |
| 3 | 3 | 55 |
| 4 | 2 | 59 |
| 5 | 1 | 64 |

For each `note_midi` observation:

1. MIDI is deterministically rounded half-up to the nearest semitone.
2. `fret = rounded_midi - open_midi`.
3. `fret < 0`, `fret > MAX_FRET`, malformed/non-finite values, and invalid timing are quarantined rather than repaired.
4. Accepted rows preserve the original continuous MIDI value and cents deviation as audit metadata.

## Gold levels

### Direct note gold

Accepted string-specific `note_midi` rows are classified as:

`DIRECT_STRING_SPECIFIC_NOTE_OBSERVATION_AFTER_DETERMINISTIC_SANITIZATION`

This is strong evidence for the played **string + fret** geometry.

### Derived strum-voicing gold

A second layer groups accepted note onsets using a frozen 50 ms window. A cluster is emitted only when:

- at least two notes are present;
- every note is on a distinct string;
- no same-string ambiguity occurs inside the window;
- every `(MIDI, string, fret)` placement remains physically exact.

If any same-string ambiguity occurs in the 50 ms window, that whole local window is excluded from derived voicing gold rather than being repaired or re-anchored.

This layer is explicitly **derived**, not raw human fingering annotation. The 50 ms window is frozen in v1 and must not be tuned from future model outcomes.

## What this corpus does not contain

GuitarSet JAMS does not directly provide authoritative:

- left-hand finger numbers 1..4;
- barre finger identity;
- Teacher preference between multiple valid fingerings.

Therefore this corpus must never be reclassified as left-hand fingering Teacher Gold.

## Exact audited archive

The approved source archive is sealed by SHA-256 in:

`evidence/stage7g_e3_guitarset_comp_observed_gold_v1.json`

Observed audit result for that exact archive:

- 180 comp recordings
- 6 performers
- 15 style groups
- 45,686 raw note observations
- 45,615 accepted note observations
- 71 quarantined observations
- all 71 quarantines are negative-fret violations
- 12,556 conservative derived strum-voicing events
- accepted fret range: 0..19

## Safety boundary

This stage sets:

- `training_authorized = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`

The next required gate is a **split and leakage contract**. Training may begin only after development/validation/final roles are frozen so that performer/recording/style leakage is explicitly controlled.

This work is independent of the open S1-H-C.v2 regression PR. It must not silently merge or promote that provisional H-C behavior.
