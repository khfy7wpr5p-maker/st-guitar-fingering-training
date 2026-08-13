# Stage 6F — Sequence Path Optimizer v1

Stage 6F keeps Stage 6E's learned local ranking model but changes validation decoding from greedy event-by-event selection to bounded Viterbi-style dynamic programming over the entire chord sequence.

Safety boundaries:

- candidate states come only from deterministic physical guitar voicing enumeration;
- the learned model cannot create or approve physically impossible string/fret states;
- validation decoding receives no observed previous or future string/fret labels;
- future information remains Stage 6E pitch-only lookahead;
- per-event state count and per-source transition count are bounded and fail closed;
- no checkpoint is retained;
- this remains Guitar Pro behavior-cloning diagnostics, not teacher-GOLD or production authority.

Primary evaluation: same model, same 5 family-isolated folds, Stage 6F path decoder versus Stage 6E greedy rollout. Promotion requires fold-majority improvement without violating the safety boundaries above.
