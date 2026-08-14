# Stage 7G-C — Target-Free MusicXML Intake

## Goal

Allow ordinary score-partwise MusicXML to become Stage 7G Teacher-GOLD annotation material even when the source contains no guitar TAB or technical string/fret labels.

The source supplies musical pitch/rhythm structure only. Physical guitar placements remain deterministic candidates produced by `valid_chord_voicings()`. A human teacher chooses later among those candidates in the existing blind annotation workflow.

## Safety boundary

- No source string/fret target is required.
- Technical string/fret metadata, if present, is ignored by the target-free parser.
- Six-string tuning must be supplied explicitly.
- Pitch interpretation must be supplied explicitly as either `sounding_exact` or `written_octave_plus_12`; Stage 7G-C does not guess the guitar octave relation.
- Multi-part scores require an explicit `part_id`.
- Multi-staff scores require an explicit `staff_id`.
- If MusicXML declares staff tuning, it must agree with the explicit tuning.
- Stage 7E final-test source hashes/origins remain forbidden by the existing annotation sampling quarantine.
- No Teacher-GOLD labels are created by intake.
- No model is fitted, no checkpoint is retained, and no production integration is authorized.

## Data flow

```text
ordinary MusicXML
        ↓
explicit part/staff + tuning + pitch mode
        ↓
pitch-only TargetFreeSource
        ↓
deterministic valid_chord_voicings()
        ↓
stateless specialist diagnostics
        ↓
blind Teacher-GOLD task
```

## Why pitch mode is explicit

Existing GP/TAB intake can compare MusicXML pitch with technical string/fret placement and determine whether the XML is already sounding pitch or written an octave above physical guitar pitch. A target-free source has no trusted physical target for that comparison. Guessing would silently shift every candidate by an octave, so Stage 7G-C fails closed instead.

## Next gate

After this protocol is merged, run a new independent source-intake batch using ordinary MusicXML. Measure how many independent families and ambiguous chord events become eligible before any teacher annotation or model training begins.
