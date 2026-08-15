# Stage 7G-E3-E-A3 — Frozen open_low / compact disagreement inventory

## Purpose

E3-E-A3 executes the next target-blind step allowed by the merged E3-E-A2 seal:

1. reconstruct the already-approved Stage 7B `open_low` and `compact` pairwise specialists from the fixed balanced 100-family synthetic corpus;
2. parse only the 31 E3-E families admitted by A2 with the already-frozen part/staff selections;
3. enumerate deterministic physical chord candidates;
4. count `open_low != compact` disagreements without creating Teacher-GOLD tasks or reading human labels.

This stage does not train or tune on E3-E data. The only fitted estimators are in-memory reconstructions of the frozen Stage 7B synthetic specialists. No checkpoint is serialized.

## Reconstruction guard

The reconstruction must fail closed unless both specialists reproduce the historical Stage 7B-C2 identity values already sealed in repository evidence:

- balanced synthetic corpus: 100 families total;
- `open_low`: 20 synthetic families, 480 training events, pairwise matrix shape `6900 x 4`, family-isolated CV macro Top-1 `1.0`;
- `compact`: 20 synthetic families, 480 training events, pairwise matrix shape `7708 x 4`, family-isolated CV macro Top-1 `1.0`.

The reconstructed models remain in memory only.

## E3-E input boundary

A3 accepts exactly the 31 families in `evidence/stage7g_e3_e_a2_family_selection_seal.json`.

`chopin_ballade1_op23` remains quarantined because the frozen target-free parser rejected it before specialist scoring. A3 does not repair or relax the parser after observing that source.

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

The persistent evidence is aggregate-only. It may contain per-family counts and a SHA-256 digest of the exact disagreement event-ID set, but it must not contain Teacher-GOLD responses or a teacher-facing task list.

## Scientific boundary

At A3:

- E3-E Teacher-GOLD generated: false;
- E3-E Teacher-GOLD answers read: false;
- router scoring: false;
- E3-E model fit/tuning: false;
- threshold selection: false;
- checkpoint retained: false;
- production integration: false;
- Stage7E musical content reused: false.

A target-blind disagreement inventory can be used only to design and freeze a later blind annotation quota/package before human responses exist.
