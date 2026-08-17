# Stage 7G-E3-S1-G — Independent Full Component Reliability v1

Status: **FROZEN BEFORE S1-E PILOT REPEAT RESULT**  
Frozen at: `2026-08-17T21:07:00+03:00`  
Base main SHA: `d19de194c36675c43ec9ae07793edac2968fe0a3`

This record freezes the full-reliability design before the S1-E pilot repeat result is observed. The exact first/repeat task manifests were generated now and are committed by SHA-256. Their full contents are withheld before use to preserve blinding. The immutable Git record commits their SHA-256 hashes; hidden manifest contents are not published before use.

## Frozen values

- 40 tasks total: 20 STRING_DISTRIBUTION + 20 OPEN_STRING_UTILITY.
- Each focus: 10 triads + 10 tetrads.
- STRING pair categories: 7×0↔1 gaps, 7×0↔≥2, 6×1↔≥2; option totals 14/13/13.
- OPEN pair categories: 7×1↔1 open, 7×1↔≥2, 6×≥2↔≥2; option totals 21 exactly-one-open / 19 at-least-two-open.
- 40 distinct interval families; max 1 task/family. All S1-E pilot v2 interval families excluded.
- Selected option max fret ≤12; standard tuning `(64,59,55,50,45,40)`; all selected options revalidated against authoritative `valid_chord_voicings()`.
- Repeat: new opaque IDs/order and exactly 20/40 side reversals. Private repeat nonce committed by SHA-256, not exposed.
- Timing: <24h invalid; 24–72h preferred; >72–168h REVIEW; >168h invalid/new batch.
- PASS per micro-question: exact ≥36/40, Cohen κ ≥0.80, repeat UNSURE ≤4/40, first-pass YES ≥5 and NO ≥5.
- REVIEW: exact 35/40 or 0.70≤κ<0.80 or repeat UNSURE 5–9/40 or insufficient first-pass variance, unless hard FAIL.
- FAIL: exact ≤34/40 or κ<0.70 or repeat UNSURE ≥10/40 or integrity/timing failure.
- Global PASS requires all three micro-questions PASS + 100% manifest/physical integrity + repeat start in 24–72h.
- S1-E pilot labels and all repeat labels are never training data. Full-reliability first-pass labels remain QUARANTINED until GLOBAL PASS plus a separate reviewed+merged training protocol.

## SHA-256 commitments

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| protocol | `21a06bf5f0bca59535cf092d672c4a33e307a303667797aacc5fde0c40305ffd` | 6038 |
| source_manifest | `ccd6bce7e386be4a7cc12c279891edeeb1decac83fb14e967bba15f4f6b2a73f` | 58015 |
| first_manifest | `6670353c83ff9f7ec943a78c65d5cc62a68eeab2643be0041911d833a6a97a05` | 53806 |
| repeat_manifest | `7b8ef0acc7fa678ad9bba57bce1f4ae17a17096f6fffd424b81c0c17c33f3eca` | 53815 |
| generation_audit | `a9e4dae922188e424afa456d967ccf79a5b5de2bea7638ae0e087b979503ce09` | 10853 |
| sealed_bundle | `d4b45270bcbaf348e5e3869869f836258e4f0728d0fd3f8795a1e8c258c46128` | 101025 |
| frozen_record | `dbd6b8da4bd88a8462b909f7aa80801a1a0ea26d5ce7378ca42df0afdb28b295` | 2402 |

The repeat manifest/source alignment is intentionally not printed here. The committed SHA-256 values make any later substitution detectable without exposing the blind mapping.
