# Stage 7G-E3-S1-H-A — Guitaristic Plausibility Analyzer + Conservative Pruning Contract

Status: **PREPARATION ONLY — BRANCH / DRAFT PR**  
Base `main`: `ac146e9a5c6519a03e3650fe00b236c13fe90a7b`  
Rule version: `S1-H-A.v1`

## Purpose

Insert a deterministic, explainable plausibility layer immediately after `valid_chord_voicings()` and before any future Teacher or AI ranker path.

The layer may analyze or prune existing physically-valid candidates. It must never create a new string/fret placement, repair an invalid candidate, legalize a candidate rejected by `valid_chord_voicings()`, or reinterpret musical preference as physical truth.

## Physical authority

`valid_chord_voicings()` remains the sole physical authority.

The analyzer validates every supplied candidate against the authoritative candidate set for the same pitch-set and tuning. Non-authoritative candidates and duplicate raw candidates fail closed.

Preferred full-set entry point:

`analyze_valid_chord_voicings(pitches, tuning)`

Lower-level entry point:

`analyze_guitaristic_plausibility(pitches, tuning, raw_candidates)`

## Deterministic facts

Existing Stage 7G-E3 geometry is reused through `stage7g_e3_proposal_geometry()`:

- open note count
- fretted note count
- minimum / mean / maximum positive fret information
- positive fret span
- unique positive frets
- same-fret multiplicity / barre proxy
- string span
- adjacent-string ratio
- internal string gaps

S1-H-A adds only deterministic structural facts:

- used/open/fretted string sets
- fretted-string topology (`O`, `F`, `-` by string)
- contiguous fretted runs
- isolated fretted-string count
- explicit internal gap positions
- effective fretted hand span (the existing positive-fret span, named explicitly for this layer)
- same-fret contiguous barre opportunities
- conservative minimum-finger proxy = number of distinct positive fret values

The minimum-finger proxy is a lower bound only. It is not a complete fingering solver.

## Classification contract

Classes are:

- `PLAUSIBLE`
- `BORDERLINE`
- `DOMINATED`
- `IMPRACTICAL`

Precedence is:

`IMPRACTICAL > DOMINATED > BORDERLINE > PLAUSIBLE`

### Hard prune

Only one hard-prune rule exists in v1:

`H001_MIN_FINGER_PROXY_GE_6`

A candidate with six distinct positive fret values has a conservative minimum-finger proxy of at least six. Under the ordinary single fretting-hand simultaneous-chord envelope, this exceeds the five available fretting-hand digits even before any additional reach or topology burden is considered.

Such a candidate is classified `IMPRACTICAL` and pruned.

This rule intentionally does not claim that every imaginable extended technique is impossible. Multi-hand tapping or other exceptional techniques are outside the S1-H-A ordinary chord-voicing scope.

### Borderline only

`B001_FIVE_DISTINCT_POSITIVE_FRETS`

Five distinct positive fret values are retained and classified `BORDERLINE`. No pruning occurs.

### Dominance is diagnostic-only in v1

`D001_MECHANICALLY_DOMINATED_SAME_TOPOLOGY`

Dominance is considered only when candidates have the same used/open/fretted string topology. The comparison uses only:

- conservative minimum-finger proxy
- effective fretted hand span

A candidate can be marked `DOMINATED` only when another same-topology candidate is no worse on both quantities and strictly better on at least one.

`DOMINATED` candidates are **retained** in v1. This prevents the deterministic layer from silently converting pitch-to-string timbre, resonance, voice-leading, or artistic preference into a pruning rule.

## Explicit non-rules

None of the following is a hard-prune rule by itself:

- `open_note_count`
- high fret / high position
- internal string gap
- multiple fretted runs
- isolated fretted strings
- open-string use
- lower position
- tone, beauty, resonance, color, stylistic preference, or preferred voicing

## Audit and determinism

Every assessment contains:

- stable content-derived `candidate_id`
- class
- `pruned` boolean
- fixed-order `reason_codes`
- optional `compared_candidate_id`
- complete deterministic facts
- top-level `rule_version`

Input candidate order does not change semantic output. Candidate and assessment ordering is canonicalized by stable candidate ID.

If every supplied physically-valid candidate is hard-pruned, the result is:

`NO_PLAUSIBLE_CANDIDATE`

The complete raw physically-valid candidate set remains present in the result for audit. The analyzer does not silently feed pruned candidates back to a downstream AI.

## Required invariants

1. retained candidate set is a subset of `valid_chord_voicings()` output;
2. no new voicing is created;
3. same input produces the same result and reason codes;
4. input candidate ordering does not alter semantic output;
5. raw physically-valid candidates are preserved for audit;
6. reason codes and compared IDs are stable and traceable;
7. all-pruned state is explicit as `NO_PLAUSIBLE_CANDIDATE`;
8. non-authoritative or duplicate raw inputs fail closed.

## Test strategy

The implementation includes unit/property-style deterministic tests for:

- authoritative membership and subset invariants across canonical pitch sets;
- no-new-voicing behavior;
- input-order invariance;
- 10/10 repeatability;
- raw-set preservation;
- stable dominance comparison IDs;
- the single hard-prune case;
- five-fret borderline retention;
- open strings, high fret, and internal gap as non-pruning single factors;
- the repository's existing observed open-C Guitar/MusicXML voicing regression.

## Scientific and training boundary

This stage does not reopen S1-E/S1-G human reliability collection and does not authorize component-model fitting.

- S1-E v2 pilot labels: `NEVER TRAINING`
- S1-E repeat labels: `NEVER TRAINING`
- S1-G v2 20-task first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY / NEVER TRAINING`
- S1-G repeat: not performed
- S1-F real model fit: remains hard-closed
- no checkpoint retention
- no shadow/production integration

The merged S1-G v1 preregistration remains immutable historical evidence. Open draft PR #70 is not used as the S1-H-A base and must not be treated as merged repository truth.

## Merge boundary

This document and implementation are preparation-only. Merge requires a separate explicit user approval.
