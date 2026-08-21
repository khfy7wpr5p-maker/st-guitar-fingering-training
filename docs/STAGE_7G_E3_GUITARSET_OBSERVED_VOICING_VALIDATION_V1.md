# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 VALIDATION

## Pre-outcome scope

This stage opens the preregistered validation performer `03` exactly for the one-shot no-tuning gate of `GUITARSET-OBSERVED-VOICING-MODEL.v1`.

The outcome is not known at the time this protocol file is committed.

The following remain forbidden during this stage:

- any model refit;
- any feature/schema change;
- any hyperparameter or threshold change;
- any use of Teacher Correction or S2-A labels;
- any read of untouched-final performer `02` JAMS bytes;
- checkpoint retention or runtime/production integration.

## Fixed inputs

- source: Zenodo GuitarSet v1.0.1 record `1422265`, `GuitarSet_annotation_only.zip`;
- source SHA-256: `06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe`;
- preregistration SHA-256: `1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`;
- feature schema SHA-256: `05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`;
- sealed DEVELOPMENT model artifact SHA-256: `5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869`;
- validation performer: `03`;
- untouched-final performer: `02`.

The validation implementation reconstructs an inference-only linear scorer from the sealed model's hexadecimal `StandardScaler` and logistic coefficients. It contains no estimator `.fit()` path.

## Candidate/evaluation contract

For each validation onset cluster:

1. preserve the observed pitch multiset exactly;
2. enumerate all physically exact standard-tuning string/fret assignments within frets `0..19`;
3. require one note per string;
4. exclude single-candidate events from ranking metrics and report them separately;
5. rank the full candidate set with the sealed model;
6. compare against frozen `LOW_TOTAL_FRET.v1`.

No validation label is used to choose candidates, features, model parameters, or thresholds.

## Frozen one-shot PASS gate

All preregistered conditions must pass:

- ambiguous validation events `>= 500`;
- event Top-1 delta vs baseline `>= +0.02`;
- event MRR delta vs baseline `>= +0.05`;
- recording-macro Top-1 delta `> 0`;
- recording-macro MRR delta `> 0`;
- 2000x recording-block bootstrap, seed `0`, 95% MRR-delta lower bound `> 0`.

Bootstrap implementation is fixed before outcome:

- resample whole recordings with replacement;
- pool all ambiguous event MRR deltas from each sampled recording block;
- 2000 repetitions using Python `random.Random(0)`;
- lower 95% bound = sorted bootstrap value at zero-based index `49`;
- upper descriptive bound = zero-based index `1949`.

## One-shot workflow guard

The pull-request workflow executes performer `03` only while the final validation evidence file is absent. Once that evidence is committed, later PR synchronization runs skip the data-open step entirely.

The workflow downloads only the official v1.0.1 annotation archive and checks the exact frozen SHA-256 before JAMS content is read. The validation loader verifies the full split from archive metadata, then reads JAMS bytes only for performer `03`.

If the gate fails, the stage stops and performer `02` remains closed. If the gate passes, the only next state is an explicit untouched-final open review; final is not opened automatically by this stage.
