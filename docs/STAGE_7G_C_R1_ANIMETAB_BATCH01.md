# Stage 7G-C-R1 — AnimeTAB Batch01 clean source pool

## Goal

Establish a new, pinned, target-free MusicXML source pool that is large enough for blind Teacher-GOLD annotation before any human preference label or Teacher-GOLD model fit exists.

Raw AnimeTAB MusicXML remains outside Git. The repository records only source identity metadata, derived intake/disagreement evidence, and regression checks.

## Batch identity

- User-supplied AnimeTAB archive SHA-256: `23b634ad619dac7452af1546caef6699863e49ca5b3b4257f18e29eb91463656`.
- Clean Batch01 ZIP SHA-256: `2105c0ca1f11c80fbf2a096014cee77c905e94bdc13898820ad5d6fea4298710`.
- 40 full-track MusicXML files from `AnimeTAB/Entire songs`.
- `Clips` and `Clips/Originals` are excluded so derived excerpts/copies cannot inflate family diversity.
- One preselected full track is one Batch01 family.
- 40/40 source SHA-256 values are unique.
- Exact historical Stage 7C/7D source-hash overlap is zero.
- Conservative normalized historical family-key overlap is zero.
- Stage 7E final source is not reused.

The supplied AnimeTAB README claims `CC BY-NC`, but this evidence does not establish underlying arrangement rights or commercial/production clearance. Batch01 remains a research source pool only.

## Why staff 2 is the official intake staff

Every Batch01 file is a single-part Guitar Pro export with notation staff 1 and guitar TAB staff 2. The source-encoding audit found all 40 staff-2 tunings to be standard six-string guitar `(64, 59, 55, 50, 45, 40)` and all 40 files to have an exact XML-pitch minus physical string/fret relation of zero.

Technical string/fret metadata is used only for this source-encoding audit. The Stage 7G-C target-free parser then reads pitch/rhythm from staff 2 and does not expose or use the observed source string/fret placement for annotation sampling.

A preliminary local count used staff 1 and reported 12,660 ambiguous events. That was not sealed evidence. The official Stage 7G-C-R1 corpus uses staff 2 because it is the validated guitar/TAB staff; its final target-free count is **12,714 ambiguous events**.

Grace notes remain outside the Stage 7G-C v1 event vocabulary under the PR #27 contract. Two zero-candidate and 826 single-candidate staff-2 chord events are excluded from ambiguous annotation tasks.

## Frozen specialist guard

The synthetic pairwise specialists are reconstructed in memory from the fixed balanced 100-family synthetic corpus. The reconstruction exactly reproduces Stage 7B-C2 macro Top-1:

- `open_low`: 1.000000
- `compact`: 1.000000
- `mid_position`: 0.9458333333333332
- `high_position`: 0.9541666666666668
- `common_tone`: 0.9217391304347828

Only the four stateless specialists participate in Stage 7G annotation sampling. `common_tone` remains excluded.

## Batch01 disagreement result

From 12,714 deterministic ambiguous chord events:

- open_low vs compact disagreement: **5,626** events (44.25%).
- any disagreement among the four stateless specialists: **12,358** events (97.20%).
- four-specialist consensus: 356 events.
- all 40 families contain open_low-vs-compact disagreement.
- the smallest family still contains 57 open_low-vs-compact disagreement events.

Therefore a deterministic 600-task annotation preview can take 15 highest-priority open_low-vs-compact disagreement tasks from each of 40 families. It does not need tier-1 or consensus events.

## Gate interpretation

Stage 7G source-pool requirements are now available before labeling:

- required independent families: 30; available: 40.
- required Teacher-GOLD ambiguous events: 600; available unlabeled tasks: 12,714.
- required specialist-disagreement events: 100; available unlabeled disagreement tasks: 12,358.

This does **not** mean the Teacher-GOLD corpus gate has passed. Human Teacher-GOLD labels are still exactly **0**. No Teacher-GOLD model has been fitted, no checkpoint is retained, and production integration remains unauthorized.

Next scientific step after this evidence is accepted: generate the 600-task blind, family-balanced Teacher-GOLD annotation batch and collect human preference choices without exposing source voicing or specialist predictions.
