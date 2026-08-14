# Stage 7G-B — Blind Teacher Annotation Task Generator

## Goal

Prepare trustworthy guitaristic preference tasks for Stage 7G Teacher-GOLD collection without using the source's observed string/fret choice as supervision or as a sampling feature.

Stage 7G-B does **not** train a model and does **not** create Teacher-GOLD labels. It only converts eligible new guitar sources into a blinded teacher queue.

## Required boundary

```text
new guitar source
      ↓
source/final-test quarantine checks
      ↓
chord pitches + six-string tuning
      ↓
deterministic valid_chord_voicings()
      ↓
frozen stateless specialist predictions
      ↓
target-blind sampling priority
      ↓
BLIND teacher task manifest
```

The observed source string/fret voicing is not read for event eligibility, specialist scoring, priority, or task selection.

## Sampling priority

Priority is fixed before Teacher-GOLD collection:

1. `open_low` vs `compact` Top-1 disagreement;
2. any other disagreement among the four stateless specialists;
3. stateless consensus events.

Within each priority tier, selection is family-balanced round-robin. Candidate-rich events are considered first inside each family, with a stable hash tie-break. This prevents one long piece from dominating the teacher queue while preserving disagreement-first sampling.

## Blinding

Two separate serializations are required:

### Teacher-facing manifest

May contain only:
- anonymous task id;
- chord pitches;
- guitar tuning;
- complete deterministic physical candidate set;
- stable candidate ids.

It withholds:
- source origin;
- source SHA-256;
- family id;
- all specialist predictions;
- observed source voicing.

### Internal sampling audit

Contains source identity, family identity, specialist Top-1 predictions, candidate count, and sampling priority. It is explicitly `teacher_facing=false` and must not be used as the annotation UI payload.

## Quarantine and fail-closed rules

- Stage 7E final source hashes are forbidden.
- Stage 7E final source origins are forbidden.
- Source-origin mapping must exactly match the supplied sources.
- Duplicate source hashes are rejected.
- Duplicate event ids are rejected.
- Exactly four stateless specialists are accepted:
  - `open_low`
  - `compact`
  - `mid_position`
  - `high_position`
- `common_tone` remains excluded from Stage 7G v1.
- Six-string guitar is the only supported Stage 7G-B v1 tuning shape.
- Events with fewer than two deterministic physical candidates are excluded because they do not require a preference label.

## Stage boundary

Stage 7G-B does not change the Stage 7G readiness gates established in Stage 7F / 7G-A:

- at least 30 independent families;
- at least 600 Teacher-GOLD ambiguous events;
- at least 100 specialist-disagreement events.

These counts apply to accepted Teacher-GOLD labels, not merely generated annotation tasks.

## Safety

- no Teacher-GOLD labels generated automatically;
- no observed Guitar Pro behavior promoted to Teacher-GOLD;
- no model fitting;
- no checkpoint retention;
- no production integration;
- Stage 7E final corpus remains permanent evaluation-only data.
