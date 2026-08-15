# Stage 7G-E3-E-A2 — Family-disjointness and part/staff policy seal

## Purpose

E3-E-A2 closes the two target-blind gates left open by E3-E-A1 before any E3-E specialist disagreement inventory or Teacher-GOLD annotation is created:

1. conservative semantic family separation from both the 40 E3 development families and the consumed Stage 7E corpus;
2. deterministic MusicXML part/staff selection for the new MuseTrainer sources.

This stage does **not** create Teacher-GOLD labels, score specialists or routers, fit a model, select a threshold, retain a checkpoint, or authorize production use.

## Inputs

The candidate corpus remains the 32-source MuseTrainer manifest pinned in `evidence/stage7g_e3_e_a1_source_manifest.json` at repository commit `9128876f6164d96997c877a2be843349a32bdabb`.

The development quarantine remains the exact 40-family AnimeTAB source set represented by `evidence/stage7g_c_r1_animetab_batch01_manifest.json` and its E3-B-R1 frozen source/family digests.

Stage 7E remains permanently consumed and quarantined. Its sealed corpus is the 16 numbered GP3 blobs in `robust-guitar-tabs/code` at `f50309ad06dc734ddae5e3a0eda756fca221e2e7`.

## Conservative semantic family audit

### Development families

The 32 frozen MuseTrainer family identities/source filenames were compared before specialist scoring with all 40 explicit AnimeTAB development filenames. No same-work semantic identity was found. Exact-source hash overlap had already been zero in E3-E-A1.

### Stage 7E

The 16 sealed GP3 files are numbered outputs and do not expose their work names in their filenames. A target-free metadata audit therefore read only the GP3 header identity fields after exact byte-size and Git-blob verification. All 16 title/artist/album-related header fields were empty. That result was **not** treated as evidence of no overlap.

The audit then used repository provenance without reading Stage 7E notes, beats, strings, frets, or evaluation targets. At the pinned commit:

- the repository README identifies `Guitar Pro Conversor` as the pre-GP5 conversion component and states that the repository includes 16 Guitar Pro examples;
- `GuitarProConversor/MasterExtraction.ipynb` walks `DummyTabs/`, accepts the effective `.gp/.gp2/.gp3/.gp4` input set, selects MIDI guitar tracks 24–31, and writes sequential `tabs/<counter>.gp3` outputs;
- the complete generator-eligible `DummyTabs/` tree at that commit contains nine source files representing eight distinct works.

The exact numbered output-to-input mapping was **not reconstructed**. Instead, the conservative comparison used the entire possible eight-work generator input set. None of those possible Stage 7E source works matches any of the 32 MuseTrainer candidate works. This supports the bounded gate:

`PASS_CONSERVATIVE_DEVELOPMENT_AND_STAGE7E_SEMANTIC_DISJOINTNESS`

This is a provenance-bounded semantic exclusion, not a claim that empty GP3 headers directly identified the 16 outputs.

## Frozen target-blind part/staff policy

`src/st_guitar_fingering_training/stage7g_e3_e_a2.py` freezes the following rule before any specialist output is computed:

1. Count non-grace pitched MusicXML notes per part.
2. Select the part with the greatest count; break ties lexically by `part_id`.
3. In that selected part, if counted notes carry explicit staff IDs, require all counted pitched notes to carry one and select the staff with the greatest count; break ties lexically by `staff_id`.
4. If no counted pitched note has an explicit staff ID, select `staff_id=None`.
5. Mixed explicit-staff and unstaffed pitched notes fail closed.

The pitch contract is also frozen to standard six-string tuning `(64, 59, 55, 50, 45, 40)` and `sounding_exact`.

The rule does not inspect physical candidate counts, specialist scores, router outputs, Teacher-GOLD responses, or validation metrics.

## Execution result and fail-closed quarantine

The structural selection rule completed on all 32 pinned MuseTrainer sources. A subsequent target-free parser preflight used the frozen selection for each source without specialist scoring.

Result:

- 31 sources parsed successfully;
- one source, `chopin_ballade1_op23`, failed with `ValueError: backup moved cursor before measure start`;
- the parser was **not relaxed or repaired after observing this untouched candidate source**;
- that source is quarantined before specialist scoring.

The resulting eligible E3-E source set contains 31 families:

- selected part counts: `P1=30`, `P2=1`;
- selected staff counts: `staff 1=18`, `staff 2=12`, `staff=None=1`.

The only `P2/None` selection is `schubert_standchen_d957_no4_liszt_arr`.

## Scientific boundary

At this seal:

- Teacher-GOLD generated: **false**;
- Teacher-GOLD answers read: **false**;
- specialist scoring: **false**;
- router scoring: **false**;
- model fit: **false**;
- threshold selection: **false**;
- checkpoint retained: **false**;
- production integration: **false**;
- Stage 7E musical content used for development: **false**.

MuseTrainer provenance remains research-only under the repository public-domain claim; this stage does not establish commercial or production clearance.

## Next gate

The 31-family set is eligible only for the next target-blind step:

`ELIGIBLE_FOR_FROZEN_SPECIALIST_RECONSTRUCTION_AND_OPEN_LOW_COMPACT_DISAGREEMENT_INVENTORY_NO_TEACHER_GOLD`

The next stage may reconstruct the already frozen `open_low` and `compact` specialists and produce a disagreement inventory. It must not create or read E3-E Teacher-GOLD responses until the task-selection quota and blind annotation package are separately frozen.
