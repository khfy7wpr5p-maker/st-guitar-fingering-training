# Roadmap

| Stage | Package | State / gate |
|---|---|---|
| 0 | Safety + architecture baseline | ✅ contracts + CI |
| 1 | Dataset Contract v1 | ✅ immutable schema + family split rules |
| 2 | Guitar Pro/MusicXML intake + normalizer | ✅ safe parse + stream/tuning/pitch mode |
| 3 | Physical validation + event extraction | ✅ independent pitch/string/fret veto |
| 4 | Dataset Builder v1 | ✅ family split + deterministic candidate generation |
| 5 | First bounded single-note training | ✅ executed; no retained production checkpoint |
| 6 | Chord voicing specialists + context experiments | ✅ research completed; failed rollout paths retained as negative evidence |
| 7D-A / 7E | Target-blind stateless specialist routing | ✅ relative research advantage survived Stage 7E; Stage 7E now permanently consumed |
| 7G-A → 7G-D | Teacher-GOLD corpus + blind pairwise annotation | ✅ 556 decisive labels / 40 families; 38 richer full-candidate labels remain separate |
| 7G-E1 | First real Teacher-GOLD pairwise router | ✅ negative: 70.50% vs 77.88% `always_open_low`; no promotion |
| 7G-E2 | Compact-preference error diagnostic | ✅ 107 compact false positives vs 66 recovered compact preferences |
| 7G-E3-A | Guitar ergonomics curriculum contract | ✅ merged: L1–L4 + frozen 40 target-blind descriptors |
| 7G-E3-B | Target-blind curriculum generator | ✅ merged |
| 7G-E3-B-R1 | First sealed curriculum batch | ✅ 400 tasks, all 40 development families, prior-task overlap 0 |
| 7G-E3-C | Teacher-GOLD Batch01 response seal | ✅ 400/400 validated; 399 decisive; open_low=311, compact=88, equal=1 |
| 7G-E3-D | Conservative compact-gate training protocol | ✅ merged/frozen before fit; `open_low` default; nested family-isolated CV + inner-only threshold selection |
| 7G-E3-D-R1A | Colab execution harness | ✅ merged at `dfe9c2b170eee1afce3a5b02ba8ec15c49c158e3` |
| 7G-E3-D-R1B | Exact execution SHA pin | ✅ notebook pinned to R1A merge SHA; one-line pin only |
| 7G-E3-D-R1 | Manual Colab development execution | ✅ **positive development signal**: 86.22% vs 77.94% baseline, +8.27 pp; macro-family +7.84 pp; no checkpoint |
| 7G-E3-E | New untouched Teacher-GOLD validation | 🟡 design opened; E3-E-A new-family intake audit is next |
| 8 | Context/transition ranking + GuitarTab Engine shadow integration | future; blocked until a valid untouched-validation checkpoint gate passes |

## Immediate next step

Proceed with **Stage 7G-E3-E-A — new-family intake audit**. This is target-blind validation-set construction, not training.

The required sequence is:

1. obtain new candidate MusicXML source material from families not present in the prior Teacher-GOLD development domain;
2. assign stable family IDs and record source/provenance/licensing status;
3. prove zero family overlap with the 40-family E1/E2/E3 development domain and with consumed Stage 7E material;
4. run only deterministic parsing, physical candidate generation, frozen `open_low`/`compact` specialist reconstruction, and frozen 40-feature extraction;
5. inventory `open_low != compact` events without Teacher-GOLD preference labels;
6. inspect family coverage and target-blind L1–L4 inventory;
7. freeze the E3-E validation quota, family allocation, blind manifest, internal audit, SHA-256 seals, and numeric pass/fail gate **before** Teacher-GOLD answers are collected;
8. only then begin blind E3-E Teacher-GOLD annotation.

No E3-E labels have been observed yet. If family disjointness or provenance cannot be demonstrated, do not create the validation batch.

## Stage 7G-E3-D-R1 evidence state

The frozen manual Colab run completed with:

- result status: `POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN`
- user-exported result SHA-256: `5626a1ea70a2bc285d3585ec2f155eb86040ece6507a03dd6a477dd073ec67d3`
- 399 decisive development events / 40 families
- event accuracy: 86.22%
- `always_open_low` event baseline: 77.94%
- event delta: +8.27 pp
- macro-family delta: +7.84 pp
- compact precision / recall: 77.97% / 52.27%
- compact TP / FP: 46 / 13
- family win / tie / loss: 22 / 13 / 5
- selected thresholds by outer fold: `[0.5, 0.5, 0.6, 0.5, 0.5]`
- checkpoint retained: no
- production integration: no
- Stage 7E used: no

This result authorizes E3-E design only. It is not untouched validation and is not a model-promotion decision.

## Scientific rules that remain fixed

- Deterministic guitar physics owns physical validity.
- `open_low` is the default decision; `compact` is a gated alternative.
- The E3-D fit used only the new E3 Batch01 399 decisive pairwise Teacher-GOLD rows.
- The earlier 556 decisive E1/E2 labels are consumed hypothesis-development evidence and remain excluded from the E3-D fit.
- The first 38 full-candidate Teacher-GOLD choices remain a separate semantic label type.
- Stage 7E is permanently forbidden for training, tuning, calibration, feature selection, or new validation.
- E3-D threshold selection occurred only on inner out-of-fold predictions; outer labels did not change thresholds.
- E3-D remains development CV and cannot authorize checkpoint retention or production.
- E3-E must use genuinely new family-disjoint blind Teacher-GOLD material.
- E3-E labels cannot be used to change features, model family, hyperparameters, thresholds, calibration, or pass/fail criteria.
- A positive E3-E result can at most open a separate checkpoint/promotion design gate; production/shadow integration remains separately gated.

## Development-control rule

Routine read-only analysis, branch creation, implementation inside an already approved bounded stage, tests, CI checks, and PR preparation do not require separate approval messages. One explicit approval remains at meaningful risk gates rather than at every mechanical step.

Code/model-behavior merges, checkpoint retention/promotion, production or shadow integration, destructive history operations, and other materially irreversible changes still require an explicit gate. Documentation-only maintenance explicitly requested by the user may be implemented and merged under that same bounded authorization after scope and CI are verified.
