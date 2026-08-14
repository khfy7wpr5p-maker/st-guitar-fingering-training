# Stage 7C-R1 — Real Guitaristic Transfer Result

Date: 2026-08-14

Status: **DIAGNOSTIC / MIXED TRANSFER — NO MODEL PROMOTION**

## Corpus identity

The external Google Drive corpus was reconstructed from the same two source groups used during the Stage 6 Guitar Pro work.

- 42 raw XML files discovered
- 37 pass the deterministic MusicXML intake contract
- 5 fail intake
- 4 additional byte-identical duplicates are removed by source SHA-256
- **33 unique admitted XML**
- **25 broad musical families**
- **1879 chord events**

The 1879 chord-event count independently matches the historical Stage 6 evidence: 1561 raw training chord events + 318 raw validation chord events.

No XML corpus file is committed to Git.

## Reproduction guard

Before reading the real-transfer result, the Stage 7 synthetic generator/ranker path was independently reconstructed and checked against the accepted Stage 7B-C2 evidence. Macro Top-1 reproduced exactly:

| Specialist | Reproduced C2 Top-1 |
|---|---:|
| open_low | 1.0000 |
| compact | 1.0000 |
| mid_position | 0.9458333 |
| high_position | 0.9541667 |
| common_tone | 0.9217391 |

This guards against evaluating the real corpus with a different ranking objective or feature definition.

## Frozen specialist transfer

Real observed voicings are evaluation-only behavior labels. They are never used for fit or adaptation.

| Specialist | Events | Event Top-1 | Event MRR | Macro-family Top-1 | Random Top-1 |
|---|---:|---:|---:|---:|---:|
| open_low | 1828 | **0.7916** | 0.8684 | **0.7988** | 0.1125 |
| compact | 1828 | **0.6204** | 0.7825 | **0.5987** | 0.1125 |
| mid_position | 1828 | 0.1307 | 0.3094 | 0.1113 | 0.1125 |
| high_position | 1828 | 0.0591 | 0.1888 | 0.0908 | 0.1125 |
| common_tone | 1797 | **0.7474** | 0.8309 | **0.7373** | 0.1128 |

`common_tone` remains diagnostic because it uses the observed previous real voicing as teacher-forced previous context and skips the first chord of each source.

## Range audit

The real candidate set is not clipped to the synthetic 0..12-fret training envelope.

- 1680 / 1879 real chord events contain at least one physically valid candidate above fret 12.
- Only 3 observed real voicings themselves exceed fret 12.

This prevents hidden inflation of transfer accuracy by deleting hard high-fret alternatives.

## Specialist coverage

Across the 1797 ambiguous events common to all five specialist evaluations, at least one specialist places the observed voicing Top-1 on 1740 events:

- diagnostic coverage: **0.9682804674 (96.83%)**

This number is **not deployable accuracy**. It is oracle-like coverage because determining which specialist matched requires knowing the observed outcome. It only shows that the specialist bank spans a large portion of the observed behavior space.

## Interpretation

Transfer is heterogeneous:

- `open_low` transfers strongly.
- `common_tone` transfers strongly under its teacher-forced diagnostic context.
- `compact` transfers moderately.
- `mid_position` is approximately random in Top-1.
- `high_position` is below random in Top-1.

Therefore Stage 7C-R1 does **not** justify a checkpoint, a universal specialist, a learned router, or production integration. The next scientific problem is specialist selection/gating without using the observed target voicing.

## Safety state

- real training rows: **0**
- real model fit/adaptation: **false**
- checkpoint retained: **false**
- production integration: **false**
- real corpus committed to Git: **false**
