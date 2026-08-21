# Stage 7G-E3 — GuitarSet Teacher / Observed / Model Alignment v1

## Purpose

Compare three behaviors on the already collected **DEVELOPMENT-only** Teacher Voicing pilot:

1. blinded Teacher string/fret preference;
2. GuitarSet observed performer placement;
3. the already sealed GuitarSet DEVELOPMENT model.

This is a **diagnostic alignment analysis only**. It does not create a new model-evaluation gate and it does not authorize tuning, refit, checkpoint retention, untouched-final access, shadow integration, or production.

## Why model-vs-observed is not an independent metric here

The 24 Teacher Voicing tasks come from the GuitarSet `DEVELOPMENT` role. The sealed model was also fit on the full `DEVELOPMENT` role after the preregistered development gate passed. Therefore model-vs-observed agreement on these 24 events is explicitly:

`IN_SAMPLE_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION`

It may describe model behavior, but it must not be reported as held-out accuracy or independent validation.

The repository's independent one-shot validation remains the sealed performer `03` evidence. Untouched-final performer `02` remains a separate gate.

## Inputs

The analyzer requires:

- Teacher choices JSON exported by the blinded pilot;
- exact Teacher manifest JSON;
- separated internal audit JSON;
- sealed DEVELOPMENT model artifact JSON.

The choices file is hashed before analysis. Raw Teacher answers are **not required to be committed to Git**.

## Fail-closed boundaries

The analyzer rejects:

- wrong Teacher manifest/export provenance;
- partial candidate displays;
- candidate-ID / placement mismatches;
- validation or untouched-final pilot opening;
- modified or unsealed model artifacts;
- protocol or 28D feature-schema drift;
- non-DEVELOPMENT model artifacts;
- checkpoint/runtime-authorized model artifacts;
- non-finite model parameters or scores.

The output contains aggregate counts/rates and input hashes, but no raw Teacher task IDs or raw Teacher choices.

## Output semantics

Reported aggregate comparisons:

- Teacher ↔ observed guitarist exact agreement;
- model ↔ observed guitarist exact agreement — always marked in-sample diagnostic;
- model ↔ Teacher exact agreement;
- `LOW_TOTAL_FRET.v1` baseline ↔ observed guitarist;
- baseline ↔ Teacher;
- five-way triple-agreement category counts.

Triple categories:

- all three same;
- Teacher = observed, model differs;
- model = observed, Teacher differs;
- Teacher = model, observed differs;
- all three different.

## CLI

```bash
python scripts/analyze_guitarset_teacher_model_alignment_v1.py \
  --choices /path/to/GuitarSet_TeacherVoicing_Pilot01_choices.json \
  --manifest /path/to/ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_manifest.json \
  --internal-audit /path/to/ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_audit.json \
  --model-artifact evidence/stage7g_e3_guitarset_observed_voicing_development_model_v1.json \
  --output /tmp/guitarset_teacher_model_alignment_v1.json
```

## Scientific boundary after analysis

The analysis itself keeps:

- `validation_performer_opened_by_this_analysis = false`
- `untouched_final_performer_opened_by_this_analysis = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`
- `final_access_authorized = false`

The next consequential gate remains:

`OBSERVED_VOICING_MODEL_UNTOUCHED_FINAL_OPEN_REVIEW`
