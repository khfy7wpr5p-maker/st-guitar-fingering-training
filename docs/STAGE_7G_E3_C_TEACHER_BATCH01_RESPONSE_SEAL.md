# Stage 7G-E3-C — Teacher Batch01 response seal

## Status

**The first 400-task E3 curriculum annotation batch is complete and validation-clean. This stage records aggregate Teacher-GOLD evidence only; no model is fitted.**

The annotation remained blind to specialist identity, family identity, curriculum level, feature values, and observed source voicing during teacher choice collection. The response semantics are pairwise guitaristic preference between the two already-determined physically valid specialist options.

## External artifacts and integrity

The raw response export remains outside Git:

`ST_Guitar_E3_Batch01_choices_400of400.json`

SHA-256: `db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e`

It targets the sealed manifest SHA-256:

`433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2`

The externally validated artifact is:

`ST_Guitar_E3_Batch01_choices_400_VALIDATED.json`

Neither raw choices nor per-task validated rows are committed to Git in this stage.

## Validation result

Validation: **PASS**

- declared choices: 400
- actual choices: 400
- unique task IDs: 400
- exact manifest task-set match: yes
- duplicate task IDs: 0
- missing task IDs: 0
- invalid responses: 0
- annotation blinded: yes
- manifest SHA match: yes

## Aggregate Teacher-GOLD responses

Blind responses:

- A: **201**
- B: **198**
- equal / unsure: **1**

After internal blind mapping is decoded:

- `open_low`: **311**
- `compact`: **88**
- equal / unsure: **1**
- decisive: **399**

This batch is disagreement-enriched and must not be interpreted as population prevalence.

## Curriculum-level result

| Level | Tasks | open_low | compact | equal/unsure | compact rate among decisive |
|---|---:|---:|---:|---:|---:|
| L1 | 140 | 131 | 9 | 0 | 6.43% |
| L2 | 120 | 88 | 32 | 0 | 26.67% |
| L3 | 80 | 63 | 17 | 0 | 21.25% |
| L4 | 60 | 29 | 30 | 1 | 50.85% |

The target-blind curriculum ordering therefore shows a useful development signal: the easiest L1 contrasts strongly favor the `open_low` default, while L4 is nearly balanced. This is evidence that the curriculum difficulty representation aligns with preference ambiguity in this batch; it is **not** a production-routing rule and it is **not** a final validation result.

## Scientific boundary

- Teacher-GOLD semantics: pairwise guitaristic preference
- new pairwise Teacher-GOLD labels: 400
- source families: 40
- family overlap with prior development: **yes**
- untouched final validation: **no**
- Stage 7E reused: **no**
- first 38 historical full-candidate labels mixed into this pairwise batch: **no**
- model fit: **no**
- threshold tuning: **no**
- hyperparameter tuning: **no**
- checkpoint retained: **no**
- production integration: **no**

Because these labels come from the same 40 development families used earlier, E3-C may support subsequent E3 model development but cannot be used as a new untouched final validation corpus. Any model or threshold designed using these labels must later be evaluated on new family-disjoint Teacher-GOLD material.

## Next gate

Stage 7G-E3-D must freeze the training protocol before any Colab training run. The intended direction is an interpretable, precision-first conservative `compact` gate with `open_low` as the default, using the frozen ergonomics/string-topology representation and family-isolated validation. Checkpoint saving remains disabled by default.
