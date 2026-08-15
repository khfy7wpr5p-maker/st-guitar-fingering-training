# Stage 7G-E3-E-A1 — New-family source intake harness

## Purpose

E3-E-A1 is the first implementation step of the untouched family-disjoint validation design. It prepares a target-free source/provenance audit **before** any E3-E Teacher-GOLD response exists and before any specialist/router score is computed on the new material.

This PR is an intake/audit harness, not an E3-E validation-set seal.

## Candidate external corpus

The candidate source manifest pins:

- repository: `musetrainer/library`
- commit: `9128876f6164d96997c877a2be843349a32bdabb`
- source format: compressed MusicXML (`.mxl`)
- 32 distinct source files / candidate family keys
- duplicate work variants intentionally excluded from the manifest
- raw external MXL files remain outside this repository

The pinned repository README identifies the collection as a public-domain MusicXML library. No standalone license file was observed at the pinned repository root during this intake review. Therefore this project records the corpus only as:

`RESEARCH_ONLY_FROM_REPOSITORY_PUBLIC_DOMAIN_CLAIM`

This is **not** commercial or production clearance and does not authorize redistribution of the raw MXL files from this training repository.

## Secure MXL boundary

`mxl_target_free.py` adds a separate compressed-MusicXML adapter instead of weakening the existing plain-MusicXML parser.

The adapter:

- caps the outer source size;
- bounds archive member count and total uncompressed bytes;
- rejects encrypted members;
- rejects symlink members;
- rejects absolute/traversal/non-normalized archive paths;
- rejects duplicate normalized member names;
- bounds per-member compression ratio;
- requires `META-INF/container.xml`;
- requires exactly one declared MusicXML rootfile;
- never extracts archive paths to disk;
- writes only the already-validated rootfile bytes to a fixed temporary filename when delegating to the existing target-free parser;
- preserves the exact outer MXL SHA-256 as source identity.

The existing target-free parser remains authoritative for MusicXML pitch/rhythm parsing. Technical string/fret values are not exposed to the E3-E target-free event representation.

## A1 structure audit

The audit harness deliberately stops before part/staff selection and before specialist reconstruction.

For each pinned source it records only:

- exact Git blob SHA-1 and byte size;
- exact outer MXL SHA-256;
- MXL rootfile path;
- MusicXML version and encoder software string;
- part IDs;
- observed staff IDs per part;
- pitched-note count per part;
- count of technical `string`/`fret` XML elements, without using their values as targets.

The resulting report is expected to expose whether a later target-blind part/staff policy is needed. That policy must be frozen before specialist disagreement inventory is produced.

## Development quarantine

The E3-E-A1 audit requires the already sealed external E3 curriculum package:

`ST_Guitar_Stage7G_E3_B_R1_Curriculum_Batch01_400.zip`

Expected SHA-256:

`e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`

The harness uses the existing frozen package reader to reconstruct the exact 40 development source SHA-256 values and family IDs from `internal_audit_e3_batch01_400.json`. It does **not** require or read the Teacher-GOLD answer file.

Any exact new-source SHA-256 overlap with those 40 development sources aborts A1.

## Stage 7E quarantine

The audit also consumes only the existing Stage 7E seal metadata and rejects:

- reuse of the Stage 7E repository; and
- exact Git-blob reuse of any of its 16 sealed source files.

However, the Stage 7E seal exposes numbered GP3 source paths rather than semantic composition/title identities. Therefore exact-source disjointness is not yet sufficient to claim the stronger E3-E family-disjoint gate.

A1 output intentionally remains:

`STRUCTURE_AUDIT_PASS_FAMILY_DISJOINTNESS_NOT_YET_SEALED`

with:

`PENDING_CONSERVATIVE_SEMANTIC_FAMILY_AUDIT`

until the pinned Stage 7E sources are reconstructed target-free enough to compare semantic family identity without using their evaluation targets.

## What A1 does not do

A1 does not:

- collect or inspect E3-E Teacher-GOLD responses;
- read the previous 400 Teacher-GOLD answer file;
- score `open_low` or `compact`;
- construct the E3-E disagreement inventory;
- select an E3-E quota;
- freeze a pass/fail metric;
- fit the E3-D gate model;
- select or revise a threshold;
- retain a checkpoint;
- authorize production or shadow integration;
- reuse Stage 7E for modeling.

## Next gate after this harness

After this PR is accepted, run the source structure audit with the sealed E3 development package present. Then, before any Teacher-GOLD annotation, resolve two target-blind questions from the audit evidence:

1. complete the conservative semantic family-overlap proof against both the 40 development families and Stage 7E;
2. freeze a deterministic part/staff selection policy if the new source structures require one.

Only after both pass may E3-E-A proceed to frozen specialist reconstruction, 40-feature extraction, and `open_low != compact` disagreement inventory.
