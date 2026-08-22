# GuitarSet Observed-Voicing Model v2 — 0–20 Fret Preregistration

Status: **PREREGISTERED / TRAINING AUTHORIZED / RUNTIME CLOSED**

This contract creates a new model version instead of mutating v1.

- Model: `GUITARSET-OBSERVED-VOICING-MODEL.v2`
- Candidate domain: standard tuning, frets **0..20**
- Source archive: same hash-pinned GuitarSet 1.0.1 annotations
- Split: unchanged `GUITARSET-SPLIT.v1`
- Feature schema SHA-256: `617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285`
- Protocol SHA-256: `db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02`
- Model family: frozen `StandardScaler + LogisticRegression`, no hyperparameter tuning
- Baseline: unchanged `LOW_TOTAL_FRET.v1`

## Scientific limitation

The audited GuitarSet source has observed positive fret values only in `0..19`. Therefore v2 does **not** claim direct positive-gold evidence for fret 20.

Fret 20 is admitted only to make the learned candidate domain compatible with the GuitarTab Engine authoritative `0..20` candidate space. Any future fret-20 quality claim remains forbidden until independent evidence exists.

## Gates

1. DEVELOPMENT performers `00,01,04,05`
2. one-shot VALIDATION performer `03`
3. untouched FINAL performer `02`
4. checkpoint-retention review

Validation/final remain label-isolated exactly as v1. No validation/final label may enter fitting or tuning.

## Authority

- training: authorized
- checkpoint retention: closed until final PASS review
- runtime connection: **false**
- production authority: **false**
- shadow/optimizer/TAB authority: **false**
