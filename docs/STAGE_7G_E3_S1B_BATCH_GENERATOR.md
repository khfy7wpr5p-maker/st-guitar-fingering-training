# Stage 7G-E3-S1-B — Sealed Component Batch Generator

## Scope

S1-B implements the deterministic packaging machinery required by the frozen S1-A protocol. It does **not** train, tune, retain, or activate any model.

The generator accepts the exact original E3 Batch01 blind 400-task Teacher manifest and its validated 400-row Teacher-GOLD response file only to reconstruct which tasks have already been exposed in S0-C/S0-D-A/S0-D-B. Historical Teacher preference is not used to rank or select S1 tasks.

## Deterministic exclusions

Before S1 selection, S1-B reconstructs from the frozen historical algorithms:

- 60 S0-C repeat tasks;
- 20 S0-D-A pairwise-rubric tasks;
- 20 S0-D-B independent-scoring pilot tasks;
- the one original `EQUAL_OR_UNSURE` row.

The expected union is exactly 101 unique source tasks. The reconstruction uses the previously frozen salts and quotas, not old exported repeat/calibration answer files.

## First-pass seal

S1-B deterministically selects exactly 120 unexposed decisive tasks:

- L1=30
- L2=30
- L3=30
- L4=30
- maximum 4 tasks per family
- minimum 32 distinct families

Families are assigned to one of five frozen development folds by salted SHA-256 ordering. All tasks from one family remain in the same fold.

Each source task receives:

- an opaque S1 task ID;
- an independently reblinded A/B orientation;
- a sealed order;
- one of four 30-task sessions.

Teacher-facing manifests do not expose original task IDs, family IDs, curriculum levels, specialist identities, old answers, or historical Teacher preference.

## Blind repeat seal

Before any S1 first-pass answer exists, the generator selects exactly 48 tasks from the sealed 120-task first-pass corpus:

- L1=12
- L2=12
- L3=12
- L4=12
- maximum 2 repeat tasks per family

Repeat tasks receive new opaque IDs, independent A/B reblinding, and a new sealed order. The repeat manifest contains the frozen minimum-delay requirement of 24 hours but no first-pass score.

The hidden repeat audit links each repeat task to its first-pass task only for later reliability scoring. Repeat answers remain permanently reliability-only and may not become extra training rows.

## Teacher interface

`render_s1_component_annotator()` produces a self-contained mobile/iPhone-friendly HTML page.

For every task it enforces the S1-A order:

1. A alone → four 1–5 component scores;
2. B alone → four 1–5 component scores;
3. only then A and B together → overall A/B/equal-or-unsure preference.

The four fixed components are:

- `POSITION_COMFORT`
- `STRING_DISTRIBUTION`
- `FINGER_SPREAD`
- `OPEN_STRING_UTILITY`

The page autosaves locally and exports JSON only after all tasks are complete. First-pass and repeat exports use different schemas and filenames.

## Outputs

`build_s1_packages()` returns four separate objects:

1. teacher-facing 120-task first-pass manifest;
2. hidden first-pass audit;
3. teacher-facing 48-task repeat manifest;
4. hidden repeat audit.

The hidden audits must not be distributed with the Teacher-facing test before annotation is complete.

## Scientific boundary

S1-B authorizes none of the following:

- model training;
- component specialist training;
- Guitaristic Arbiter training;
- rubric-weight fitting;
- threshold/hyperparameter tuning;
- checkpoint retention/promotion;
- Stage 7E or E3-E reuse;
- GuitarTab Engine shadow/production integration.

After S1-B is merged and the real 120/48 package is generated, the exact manifests/audits and SHA-256 seals must be verified before the first Teacher response is collected.
