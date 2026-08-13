# Dataset Contract v1

Each normalized event contains:

- `family_id`: source-family identity used to prevent leakage;
- `source_sha256`: exact source-byte digest;
- `musicxml_version` and producer software;
- `tuning`: technical string 1..N mapped to sounding open-string MIDI;
- `pitch_mode`: `sounding_exact` or `written_octave_plus_12`;
- measure, onset, duration, voice;
- one or more sounding MIDI pitches;
- observed `string` and `fret` per pitch;
- physical-validation result.

V1 training eligibility additionally requires:

- one selected guitar/TAB stream;
- complete string/fret placement for the event;
- every placement physically matches the normalized sounding pitch;
- frets in 0..24;
- no unresolved pitch-mode disagreement.

The first bounded baseline uses single-note events only. Chord events are extracted and counted but held for the later voicing package.
