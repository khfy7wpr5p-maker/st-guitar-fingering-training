# Stage 7G-E3-E-A3 — Frozen open_low / compact disagreement inventory

## Purpose

E3-E-A3 executes the target-blind step allowed by the merged E3-E-A2 seal:

1. reconstruct the already-approved Stage 7B `open_low` and `compact` pairwise specialists from the fixed balanced 100-family synthetic corpus;
2. parse only the 31 E3-E families admitted by A2 with the already-frozen part/staff selections;
3. enumerate deterministic physical chord candidates;
4. count `open_low != compact` disagreements without creating Teacher-GOLD tasks or reading human labels.

This stage does not train or tune on E3-E data. The only fitted estimators are in-memory reconstructions of the frozen Stage 7B synthetic specialists. No checkpoint is serialized.

## Reconstruction guard

The live evidence run reproduced the historical Stage 7B-C2 guard exactly:

- balanced synthetic corpus: 100 families total;
- `open_low`: 20 synthetic families, 480 training events, pairwise matrix shape `6900 x 4`, family-isolated CV macro Top-1 `1.0`;
- `compact`: 20 synthetic families, 480 training events, pairwise matrix shape `7708 x 4`, family-isolated CV macro Top-1 `1.0`.

Guard status:

`PASS_STAGE7B_C2_OPEN_LOW_COMPACT_RECONSTRUCTION`

The reconstructed models remain in memory only.

## E3-E input boundary

A3 accepts exactly the 31 families in `evidence/stage7g_e3_e_a2_family_selection_seal.json`.

`chopin_ballade1_op23` remains quarantined because the frozen target-free parser rejected it before specialist scoring. A3 did not repair or relax the parser after observing that source.

For every admitted family, A3 uses the A2-frozen:

- `part_id`;
- `staff_id`;
- standard six-string tuning `(64, 59, 55, 50, 45, 40)`;
- `sounding_exact` pitch mode.

## Inventory semantics

For every target-free chord event:

- `valid_chord_voicings()` is the sole physical-validity authority;
- zero-candidate and single-candidate chord events are counted but are not disagreement candidates;
- events with at least two deterministic candidates are scored independently by the frozen `open_low` and `compact` specialists;
- disagreement means their deterministic Top-1 voicings differ.

The persistent evidence is aggregate-only. It contains per-family counts and a SHA-256 digest of the exact disagreement event-ID set, but no raw disagreement event-ID list, Teacher-GOLD response, or teacher-facing task list.

## Pinned execution result

Draft execution PR #52 ran the pinned 31-family set at head `7c7ed8528e40943ce0b80ac4ecc00d011ce82501` in CI #123 (`run_id=31883699570`, `job_id=95009720181`). The live execution test passed, the full unit suite passed, and compile validation passed. The separate Stage7B-C2 workflow step was `SKIPPED` and is not counted as a pass; the reconstruction guard above was executed by the A3 tests themselves.

Aggregate result:

- eligible families: **31**;
- families with at least one `open_low != compact` disagreement: **24**;
- pitched events: **18,664**;
- chord events: **4,159**;
- zero-candidate chord events: **647**;
- single-candidate chord events: **74**;
- deterministic ambiguous chord events: **3,438**;
- `open_low != compact` disagreements: **1,937**;
- disagreement rate among ambiguous events: **56.34089586969168%**;
- ambiguous candidate-count range: **2..165**;
- ambiguous candidate-count mean: **21.562536358347877**;
- exact disagreement event-ID set digest SHA-256: `2d2d712b5c95b19f249aa950947062d78ab7f774a9b027b9b2386ef29d833ee1`.

The digest is computed as SHA-256 over the newline-joined lexicographically sorted exact event IDs with no trailing newline.

## Family-coverage interpretation

The frozen E3-E design requires A-phase inventory to contain only events where `open_low != compact`, but it intentionally did **not** preregister a numeric validation event quota or a numeric E3-E family floor. Therefore A3 does not post-hoc declare 24 disagreement-bearing families either sufficient or insufficient for untouched validation.

The current pool can provide at most **24 distinct families** to a disagreement-only validation batch. That limitation is now known before any E3-E Teacher-GOLD response exists and must be handled in the next preregistration gate.

E3-E-B must decide, before annotation, whether to:

- freeze a validation quota/allocation using the current disagreement-only pool; or
- require additional genuinely new, family-disjoint source material before sealing the batch.

No choice may be justified from Teacher-GOLD outcomes because none exist yet.

## Scientific boundary

At A3:

- E3-E Teacher-GOLD generated: **false**;
- E3-E Teacher-GOLD answers read: **false**;
- teacher-facing validation manifest created: **false**;
- router scoring: **false**;
- E3-E model fit/tuning: **false**;
- threshold selection: **false**;
- checkpoint retained: **false**;
- production integration: **false**;
- Stage7E musical content reused: **false**.

The next allowed gate is **E3-E-B preregistration of the validation quota, family allocation, blind A/B package, and pass/fail criteria before Teacher-GOLD answers are collected**.
