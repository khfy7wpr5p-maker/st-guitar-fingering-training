# Dataset Contract v1

Each normalized source event contains:

- `family_id`: source-family identity used to prevent leakage;
- `source_sha256`: exact source-byte digest;
- `musicxml_version` and producer software when available;
- `tuning`: technical string 1..N mapped to sounding open-string MIDI;
- `pitch_mode`: `sounding_exact` or `written_octave_plus_12`;
- measure, onset, duration, voice;
- one or more sounding MIDI pitches;
- observed `string` and `fret` per pitch when the source supplies technical placement;
- physical-validation result.

Observed-placement training eligibility additionally requires:

- one selected guitar/TAB stream;
- complete string/fret placement for the event;
- every placement physically matches the normalized sounding pitch;
- frets in the supported physical range;
- no unresolved pitch-mode disagreement.

## Teacher-GOLD supervision types

Teacher-GOLD data is not the same label source as observed corpus placement. The following supervision types are explicit and must remain semantically separate:

1. **full-candidate preference** — a blind Teacher choice from the complete displayed deterministic candidate set;
2. **pairwise preference** — a blind `A` / `B` / `EQUAL_OR_UNSURE` comparison between two frozen physically-valid proposals;
3. **independent component score** — a 1–5 score assigned to candidate A or candidate B independently, before the final pairwise preference is shown;
4. **repeat-reliability label** — a later blinded re-rating of a previously seen task, used only to measure label stability.

Pairwise labels may not be silently promoted into full-candidate Teacher-GOLD records. Independent component scores may not be silently collapsed into a single overall preference target. `EQUAL_OR_UNSURE` is preserved and is never coerced into a binary target.

Repeat-reliability labels are a distinct evidence type and are not additional training rows unless a future protocol explicitly changes that rule. The current S0-C and S1 repeat labels are permanently reliability-only.

Raw Teacher response rows remain outside Git; repository evidence may store pinned hashes, manifests, seals, and derived aggregate results.

## Stage 7G-E3 ergonomics curriculum — implemented development framework

The Guitar Ergonomics Curriculum adds a **difficulty/teaching tier**, not a new source of physical truth:

- `L1`: easy 2-note contrasts with clearly separated ergonomic geometry;
- `L2`: basic open-string / position / fret-span / string-topology contrasts;
- `L3`: medium 3–4 note chords with several plausible physical candidates;
- `L4`: hard frozen `open_low` ↔ `compact` specialist disagreements.

Curriculum examples may be generated or selected target-blind from pitches, tuning, deterministic candidates, and fixed geometry descriptors. A deterministic rule may be used to create synthetic/pretraining targets only if the target is explicitly marked as **rule-derived**; such a target must never be described as Teacher-GOLD.

Teacher preference supervision still requires an actual blind Teacher response.

The frozen E3 representation contains 40 target-blind descriptors covering chord/candidate context, open/fretted-note geometry, position/span proxies, same-fret/barre-like proxies, string span/adjacency/internal gaps, and proposal-difference descriptors. These descriptors may describe ergonomics but do not grant physical validity.

## Current S1 independent-component contract

The S1 component rubric scores each candidate independently on:

- `POSITION_COMFORT`;
- `STRING_DISTRIBUTION`;
- `FINGER_SPREAD`;
- `OPEN_STRING_UTILITY`.

The final `A` / `B` / `EQUAL_OR_UNSURE` overall preference is collected only after both candidates' component ratings are locked.

S1 data identities are frozen before reliability evaluation:

- first pass: 120 tasks, L1/L2/L3/L4 = 30/30/30/30;
- first-pass family coverage: 38 distinct families, maximum 4 tasks per family;
- blind repeat: 48 tasks, 12 per level;
- repeat family coverage: 31 families, maximum 2 repeat tasks per family;
- repeat subset selected and sealed before first-pass answers were opened;
- first-pass answers are hidden during repeat annotation;
- A/B sides are independently reblinded for the repeat.

The S1 first-pass component labels remain quarantined until the preregistered S1-D primary reliability gate passes **and** a separate component-model training protocol is merged. A reliability PASS alone does not authorize training.

S1 repeat labels are permanently reliability-only and may never be added as extra training rows.

## Split and evaluation contract

- family identity is the primary leakage boundary;
- train/validation/test families remain disjoint unless a separately preregistered nested-development design explicitly defines inner folds;
- the original 556 decisive Stage 7G E1/E2 pairwise labels are consumed development evidence, not fresh validation;
- E3 Batch01 contains 400 Teacher-GOLD responses from the 40-family development domain: 399 decisive and 1 equal/unsure;
- Stage 7E is permanently evaluation-only and cannot be reused for training, tuning, calibration, feature selection, or new validation;
- E3-E Teacher-GOLD is permanently consumed untouched evaluation evidence and cannot be reused for training, tuning, calibration, threshold/model/feature selection, or another fresh validation claim;
- S0-C repeat labels are reliability-only and forbidden from training/tuning/model selection;
- S0-D-A/B pilot labels are architecture-design/calibration evidence and are not automatically admitted to specialist training;
- S1 first-pass component labels are quarantined until the frozen reliability gate passes and a separate training protocol is merged;
- S1 repeat labels are permanently reliability-only;
- any future DCR-inspired hard-error mining must use preregistered family-isolated development predictions and may not mine Stage 7E, E3-E, S0-C repeat labels, or S1 repeat labels;
- any future checkpoint-retention claim requires new, separately controlled evidence with the gate fixed before scoring.

## Authority boundary

Dataset labels, descriptors, Teacher preferences, component scores, and learned predictions never override deterministic physical validity. Every candidate admitted to any learned ranking or refinement stage must already pass the deterministic physical engine.
