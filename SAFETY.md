# Safety

- Parse untrusted XML with `defusedxml`.
- No network DTD/schema fetching.
- Reject unsupported string numbers, fret ranges, missing tuning, malformed durations, and impossible physical mappings.
- Permit a source XML pitch differing by exactly +12 semitones only when the complete selected stream consistently demonstrates written-guitar octave notation; store this mode explicitly.
- Never infer left-hand finger numbers from string/fret alone.
- Deterministic guitar rules remain authoritative for physical validity; learned models may only score/rank/route already-valid candidates.
- No user upload, teacher correction, annotation, or repeat answer is automatic training consent.
- Copyrighted/rights-unclear source files remain outside Git.
- Training/evaluation split is by source family, never by individual event.
- Observed corpus placement, rule-derived synthetic targets, blind pairwise Teacher-GOLD, blind full-candidate Teacher-GOLD, repeat-reliability labels, and independent 1–5 component labels are distinct supervision types and must never be silently mixed.
- `EQUAL_OR_UNSURE` teacher responses are preserved and are never coerced into A/B.

## Consumed evidence boundaries

- Stage 7E is permanently consumed/evaluation-only. It is forbidden for training, tuning, calibration, feature selection, or new validation.
- The original 556 decisive Stage 7G E1/E2 pairwise labels are consumed development evidence. E2 patterns may generate hypotheses, but those labels cannot be retuned and presented as fresh validation.
- The E3 curriculum Batch01 contains 400 additional blind pairwise Teacher-GOLD responses from the same 40-family development domain: 399 decisive and 1 equal/unsure. It is valid E3 development data but not untouched validation.
- E3-E Teacher-GOLD is permanently consumed untouched evaluation evidence. It may not be used for training, threshold selection, feature/model selection, calibration, post-hoc retuning, or another fresh validation claim.
- S0-C repeat labels are reliability evidence only. They may not be used for training, threshold tuning, or model selection.
- S0-D-A and S0-D-B pilot labels are architecture-design/calibration evidence. They do not automatically become a specialist-training corpus; any future training use requires an explicit preregistered data/training protocol.

## Model / architecture safety

- The frozen 40-descriptor target-blind ergonomics representation may describe valid candidate geometry, but it never grants physical validity.
- `open_low` remains the conservative fallback/default proposal until a later promotion gate explicitly changes that policy.
- A `compact` proposal is a secondary alternative, not an independently authoritative answer.
- E3-D and E3-E produced positive research signals, but neither result authorized checkpoint retention or production/shadow integration.
- R2/S0/S0-B are diagnostic evidence. No epoch, architecture, threshold, or specialist may be promoted post hoc from those diagnostics.
- The S0-C reliability failure means a single global pairwise “naturalness” label must not be treated as proven stable specialist supervision.
- S0-D-A showed that repeated A/B subquestions can remain collinear and must not be mislabeled as independent component supervision.
- S0-D-B showed component separation under independent 1–5 per-option scoring, but the 20-task pilot is too small to authorize specialist training or fitted component weights.
- `POSITION_COMFORT`, `STRING_DISTRIBUTION`, and `FINGER_SPREAD` remained strongly coupled in the S0-D-B pilot. Do not assume they require three independent learned models without larger evidence.
- `OPEN_STRING_UTILITY` was more distinct in the S0-D-B pilot, but that observation is an architecture-design signal, not a promoted rule or model.
- No simple unweighted sum or fitted weighting of S0-D-B component scores is authorized from the pilot.
- A future component-supervision stage must freeze data selection, family isolation, repeat-reliability criteria, and any model-training gate before labels/results are observed.
- A validation result is not a production-quality claim.
- Checkpoint-retention criteria must be fixed before the untouched evaluation used to decide retention.
- A true sealed benchmark requires fresh, separately controlled material not inspected during development.
- GuitarTab Engine production/shadow integration remains closed until an explicit later gate authorizes it.

## Manual training control

- Agreed model training/evaluation execution is manual in Colab unless a later protocol explicitly changes that rule.
- The merged preregistered protocol is the design gate; the user's manual execution of a clearly separated TRAIN cell is the execution gate.
- Training does not imply checkpoint retention, model promotion, or production authorization.
- Do not select an epoch/checkpoint/threshold after seeing the same validation result unless the protocol explicitly preregistered that selection rule.

## Development control and approval gates

The project uses fewer approval interruptions while preserving the high-risk gates.

No separate approval is required for routine read-only analysis, fresh reads, branch creation, work inside an already approved bounded stage, tests, CI inspection, draft/ready PR preparation, or evidence/documentation maintenance that does not change runtime/model behavior.

An explicit approval remains required for materially consequential gates:

1. merging a code or model-behavior PR into `main`;
2. retaining/promoting a model checkpoint;
3. production or GuitarTab Engine shadow integration;
4. destructive history operations such as force-push/reset/rewrite;
5. materially expanding a previously approved stage beyond its stated scope.

For a documentation/evidence-only maintenance task that the user explicitly requests, that same bounded request may authorize the maintenance PR through merge once the diff is verified and CI is green; a second mechanical confirmation is not required.
