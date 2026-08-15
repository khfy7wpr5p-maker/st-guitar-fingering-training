# Safety

- Parse untrusted XML with `defusedxml`.
- No network DTD/schema fetching.
- Reject unsupported string numbers, fret ranges, missing tuning, malformed durations, and impossible physical mappings.
- Permit a source XML pitch differing by exactly +12 semitones only when the complete selected stream consistently demonstrates written-guitar octave notation; store this mode explicitly.
- Never infer left-hand finger numbers from string/fret alone.
- Deterministic guitar rules remain authoritative for physical validity; learned models may only score/rank/route already-valid candidates.
- No user upload or teacher correction is automatic training consent.
- Copyrighted/rights-unclear source files remain outside Git.
- Training/evaluation split is by source family, never by individual event.
- Observed corpus placement, rule-derived synthetic targets, blind pairwise Teacher-GOLD, and blind full-candidate Teacher-GOLD are distinct label types and must never be silently mixed.
- `EQUAL_OR_UNSURE` teacher responses are preserved and are never coerced into A/B.
- Stage 7E is permanently consumed/evaluation-only. It is forbidden for training, tuning, calibration, feature selection, or new validation.
- The original 556 decisive Stage 7G pairwise labels are consumed E1/E2 development evidence. E2 patterns may generate hypotheses, but those same labels cannot be retuned and presented as fresh validation.
- The E3 curriculum Batch01 contains 400 additional blind pairwise Teacher-GOLD responses from the same 40-family development domain: 399 decisive and 1 equal/unsure. It is valid E3 development data but **not** untouched validation.
- Stage 7G-E3-D may fit only the new E3 Batch01 399 decisive rows under the frozen protocol. The earlier 556 decisive rows and the first 38 full-candidate choices are excluded from that fit.
- The E3-D model input is the frozen 40-descriptor target-blind ergonomics representation. Family identity is split metadata only; curriculum level is reporting metadata only.
- `open_low` remains the default E3-D decision. A `compact` switch is allowed only under the frozen inner-CV threshold gate; if no threshold qualifies, the required fallback is `NO_SWITCH → OPEN_LOW`.
- Outer-fold labels may not select or alter E3-D thresholds.
- A simpler curriculum may accelerate learning, but rule-derived curriculum examples are not Teacher-GOLD and cannot substitute for independent teacher validation.
- A validation result is not a production-quality claim.
- Checkpoint-retention criteria must be fixed before the untouched evaluation used to decide retention.
- A true sealed benchmark requires fresh, separately controlled material not inspected during development.
- GuitarTab Engine production/shadow integration remains closed until an explicit later gate authorizes it.

## Development control and approval gates

The project uses fewer approval interruptions while preserving the high-risk gates.

No separate approval is required for routine read-only analysis, fresh reads, branch creation, work inside an already approved bounded stage, tests, CI inspection, draft/ready PR preparation, or evidence/documentation maintenance that does not change runtime/model behavior.

An explicit approval remains required for materially consequential gates:

1. merging a code or model-behavior PR into `main`;
2. retaining/promoting a model checkpoint;
3. production or GuitarTab Engine shadow integration;
4. destructive history operations such as force-push/reset/rewrite;
5. materially expanding a previously approved stage beyond its stated scope.

For a documentation-only maintenance task that the user explicitly requests and approves, that same bounded request may authorize the documentation PR through merge once the diff is verified and CI is green; a second mechanical confirmation is not required.

For Colab training, the merged preregistered protocol is the design gate and the user's manual execution of the clearly separated TRAIN cell is the execution gate. Training still does not imply checkpoint retention or production authorization.
