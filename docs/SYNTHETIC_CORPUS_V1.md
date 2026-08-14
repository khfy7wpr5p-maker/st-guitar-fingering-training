# Synthetic Chord/TAB Corpus v1

## Purpose

Synthetic Corpus v1 produces deterministic six-string guitar MusicXML/TAB families for bounded training experiments. It is intended to expand controlled physical and rule-labeled voicing coverage without changing or relabeling the real Guitar Pro corpus.

## Admission class

Every generated event is:

- `PHYSICAL`: all pitch→string/fret placements are produced from the deterministic physical candidate generator.
- `RULE_PREFERRED`: one physically valid voicing is selected by an explicit synthetic rule.
- **not** `TEACHER_GOLD`: generated preferences must never be presented as human/teacher-approved fingering.

Synthetic and real/teacher data must remain separable by provenance.

## v1 bounds

- Standard six-string tuning only: E4 B3 G3 D3 A2 E2 (`64,59,55,50,45,40`).
- Triadic chord/polyphonic events only.
- Synthetic preferred voicings are restricted to frets `0..12`.
- Default corpus: `100 families × 24 events = 2400 chord events`.
- One MusicXML file per family.
- Families are deterministic and family IDs are explicit.
- Generated files round-trip through the repository MusicXML intake parser as `sounding_exact`.

## Rule families

v1 rotates through five explicit behavior classes:

1. `open_low` — favors open strings and lower total fret cost.
2. `compact` — favors small fret span, then lower total fret cost.
3. `mid_position` — favors compact voicings centered near fret 5.
4. `high_position` — favors compact voicings centered near fret 9.
5. `common_tone` — favors preserving shared pitch+string placements and minimizing movement from the prior selected synthetic voicing.

These rules are controlled synthetic targets, not claims about universal guitar pedagogy.

## Outputs

The generator writes:

- `*.xml` — MusicXML with explicit `<technical><string>` and `<fret>` labels.
- `family_map.json` — source filename → family ID mapping.
- `synthetic_manifest.jsonl` — event-level provenance, pitches, preferred voicing, rule ID, and physical candidate count.
- `summary.json` — corpus-level counts and bounds.

## Leakage rule

All variants from one synthetic family share the same family ID. Train/validation splitting must occur by family, never by individual event or file fragment.

## Training rule

Synthetic data may be used for pretraining, feature experiments, or controlled ablations. A model trained on Synthetic Corpus v1 alone is not production-ready and must not be called teacher-preferred. Promotion requires separate evaluation on held-out real families and, later, Teacher-GOLD data.
