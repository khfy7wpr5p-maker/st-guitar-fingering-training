# Safety

- Parse untrusted XML with `defusedxml`.
- No network DTD/schema fetching.
- Reject unsupported string numbers, fret ranges, missing tuning, malformed durations, and impossible physical mappings.
- Permit a source XML pitch differing by exactly +12 semitones only when the complete selected stream consistently demonstrates written-guitar octave notation; store this mode explicitly.
- Never infer left-hand finger numbers from string/fret alone.
- Deterministic guitar rules remain authoritative for physical validity; learned models may only score/rank/route/refine already-valid candidates.
- No user upload, teacher correction, annotation, or repeat answer is automatic training consent.
- Copyrighted/rights-unclear source files remain outside Git.
- Training/evaluation split is by source family, never by individual event.
- Observed corpus placement, rule-derived synthetic targets, blind pairwise Teacher-GOLD, blind full-candidate Teacher-GOLD, independent 1–5 component labels, and repeat-reliability labels are distinct supervision types and must never be silently mixed.
- `EQUAL_OR_UNSURE` teacher responses are preserved and are never coerced into A/B.

## Consumed evidence boundaries

- Stage 7E is permanently consumed/evaluation-only. It is forbidden for training, tuning, calibration, feature selection, or new validation.
- The original 556 decisive Stage 7G E1/E2 pairwise labels are consumed development evidence. E2 patterns may generate hypotheses, but those labels cannot be retuned and presented as fresh validation.
- The E3 curriculum Batch01 contains 400 additional blind pairwise Teacher-GOLD responses from the same 40-family development domain: 399 decisive and 1 equal/unsure. It is valid E3 development data but not untouched validation.
- E3-E Teacher-GOLD is permanently consumed untouched evaluation evidence. It may not be used for training, threshold selection, feature/model selection, calibration, post-hoc retuning, hard-error mining, or another fresh validation claim.
- S0-C repeat labels are reliability evidence only. They may not be used for training, threshold tuning, model selection, or hard-error mining.
- S0-D-A and S0-D-B pilot labels are architecture-design/calibration evidence. They do not automatically become a specialist-training corpus; any future training use requires an explicit preregistered data/training protocol.
- S1 first-pass component labels are quarantined until the frozen S1-D primary reliability gate passes and a separate component-model training protocol is merged.
- S1 repeat labels are permanently reliability-only. They may not be added as additional training rows, used for model selection, or mined as hard-error examples.

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
- No simple unweighted sum or fitted weighting of component scores is authorized by S0-D-B or S1-D.
- S1-A/B/C established the preregistered reliability contract, sealed exact first-pass/repeat identities, and completed 120/120 first-pass responses. S1-D is a reliability test only.
- No component specialist may be trained or activated during S1-D.
- A S1-D component-reliability PASS opens only a separate preregistered component-model training protocol design. It does not itself authorize fitting, checkpoint retention, or integration.
- If the secondary overall-preference repeat gate fails while the primary component gate passes, component-model design may proceed, but direct overall-preference / Base Guitaristic Arbiter target training remains closed.
- A validation result is not a production-quality claim.
- Checkpoint-retention criteria must be fixed before the untouched evaluation used to decide retention.
- A true sealed benchmark requires fresh, separately controlled material not inspected during development.
- GuitarTab Engine production/shadow integration remains closed until an explicit later gate authorizes it.

## DCR-inspired refinement safety

The future **Hard Guitaristic Error Refinement** layer is a research design candidate only. It is not active during S1.

A refiner may be studied only after all of the following exist:

1. S1 component reliability passes;
2. a separate component-model training protocol is preregistered and merged;
3. valid component/base-arbiter models exist under family-isolated development evaluation;
4. high-confidence wrong decisions are defined from family-isolated development predictions, preferably out-of-fold;
5. the hard-error definition, confidence rule, hard/ordinary sample mixture, refiner model class, and base-vs-refined comparison gate are frozen before the experiment.

Additional invariants:

- the refiner may only rerank candidates already accepted by the deterministic physical engine;
- the refiner may never manufacture or legalize a new physical placement;
- Stage 7E, E3-E, S0-C repeat labels, and S1 repeat labels are forbidden for refiner training/tuning/hard-error mining;
- no hard-error threshold or sample mixture may be selected by inspecting an untouched promotion corpus;
- the Base Guitaristic Arbiter remains the conservative bypass/fallback if a future refiner is not justified or fails its gate.

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
