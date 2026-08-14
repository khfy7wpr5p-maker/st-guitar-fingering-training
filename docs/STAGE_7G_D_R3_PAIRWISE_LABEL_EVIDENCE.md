# Stage 7G-D-R3 — Blind pairwise label evidence

## Scope

This stage records the completed blind pairwise teacher annotation result from the already-sealed Stage 7G-D-R2 batch. Raw teacher choice rows remain outside Git; the repository stores only validation/evidence summaries and hashes.

The first 38 blind full-candidate selections remain a separate richer preference evidence type and are **not** counted toward the pairwise training gate.

## Export validation

- choice schema: `st-guitar-stage7g-pairwise-choice-export-v1`
- teacher manifest SHA-256: `3d3fbf9d0107ef8a1a31e597820b687a072fa0f2cc5123b8e59adbbf07e4a167`
- raw teacher export SHA-256: `87aecd6f26f3aa450bb71524fd4205afefa77cb9aee8b8741577f8a0f169afde`
- reported tasks: 562
- validated rows: 562
- unknown task IDs: 0
- duplicate task IDs: 0
- invalid responses: 0
- missing tasks: 0
- annotation remained blind

## Responses

- A: 252
- B: 304
- `EQUAL_OR_UNSURE`: 6
- decisive A/B labels: **556 / 562 (98.93%)**

The A/B presentation itself was balanced independently of the teacher response: A mapped to `open_low` on 278 tasks and to `compact` on 284 tasks. The mapping was fixed by task-id hash before annotation.

After annotation, the internal blind-side mapping can be decoded for scientific analysis:

- teacher preferred `open_low`: **433 / 556 decisive labels (77.88%)**
- teacher preferred `compact`: **123 / 556 decisive labels (22.12%)**
- equal/unsure: 6
- family-majority preference: `open_low` 37 families, `compact` 2, tie 1

This is a result on a deliberately disagreement-enriched sample. It is **not** an estimate of all-guitar-chord prevalence, deployment accuracy, or production quality.

## Family coverage and preregistered gate

Stage 7G-C-R1 defines one preselected source as one Batch01 family. The 562 pairwise labels cover all 40 source/families, and every family has decisive A/B labels.

- decisive-label threshold: >= 400 → observed **556**
- independent-family threshold: >= 30 → observed **40**
- minimum decisive labels in any family: 10
- maximum decisive labels in any family: 15
- `EQUAL_OR_UNSURE` is preserved and is never coerced to A or B
- family-isolated validation remains mandatory

**Pairwise collection gate: PASS.**

## Scientific boundary

This evidence does not itself train or promote a model:

- model fit: not started
- Colab training: not started
- checkpoint retention: no
- production integration: no
- Stage 7E final corpus reuse: no
- raw teacher choice rows committed to Git: no

The next stage may define and run a Teacher-GOLD pairwise training experiment, but its split/training/evaluation protocol must preserve family isolation and must not reuse Stage 7E as training, tuning, calibration, feature-selection, or validation material.
