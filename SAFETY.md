# Safety

## Physical-authority invariants

- Parse untrusted XML with safe parsers; do not fetch network DTD/schema resources.
- Reject unsupported string/fret mappings, missing tuning, malformed durations, and impossible physical placements.
- `valid_chord_voicings()` remains the authoritative physical candidate generator.
- Deterministic downstream layers may only remove candidates or expand metadata/assignments for candidates from that set; they may never manufacture or legalize a new physical placement.
- Learned systems may rank only candidates supplied by their approved deterministic authority boundary.

## S1-H-A plausibility safety

- complete authoritative candidate set required;
- non-authoritative candidates, duplicates, and incomplete subsets fail closed;
- raw physical set preserved for audit;
- v1 hard prune limited to `H001_MIN_FINGER_PROXY_GE_6`;
- five distinct positive frets retained as `BORDERLINE` at H-A;
- dominance remains diagnostic-only at H-A;
- tone/style/resonance/preference are not physical hard-prune rules.

## S1-H-B fretting-resource safety

S1-H-B is an ordinary four-fretting-finger resource model, not full biomechanics.

- it recomputes the complete H-A state;
- it may only further prune H-A-retained candidates;
- open strings consume no fretting finger;
- same-fret notes may share one continuous barre only under the frozen crossing rules;
- required open strings and lower positive frets block a higher-fret barre crossing;
- unused strings and higher-fret overrides are passable;
- v1 hard prune is limited to `H101_MIN_STANDARD_FINGERS_GE_5`;
- H-A-pruned candidates remain audited and may never be reintroduced;
- zero surviving candidates is explicit as `NO_STANDARD_FINGERING_CANDIDATE`.

H-B must not be described as proving comfort, reach, naturalness, wrist safety, or impossibility under extended techniques such as thumb-over or two-hand tapping.

## S1-H-C assignment-generation safety

Authoritative S1-H-C.v1 enumerates standard assignments but does not choose a preferred one.

- only H-B-retained voicings receive assignments;
- open strings use finger `0`;
- fretted groups use distinct fingers `1..4` under the frozen v1 hand model;
- notes in one H-B group share a finger;
- strictly increasing frets require strictly increasing finger numbers;
- exact pitch/string/fret placement is preserved;
- barre metadata must match the upstream group span;
- assignment identities are stable and deterministic;
- a retained voicing with zero assignments is a fail-closed invariant error;
- upstream-pruned voicings receive zero assignments.

A learned S2-A ranker must not output an assignment ID that was not supplied by authoritative S1-H-C for that event.

### Provisional S1-H-C.v2 boundary

PR #90 remains open and non-authoritative. It explores a correction to the v1 same-fret grouping assumption by allowing separate-finger partitions in addition to valid barre assignments.

PR #90 must not become authoritative until downstream H-C capacity and S2-A evidence are explicitly re-audited. Existing frozen S2-A evidence must not be silently reclassified, regenerated, or claimed under v2 semantics.

## Training and label boundaries

No user upload, Teacher correction, annotation, pilot answer, repeat answer, or external dataset is automatic training consent or automatic model-development authorization.

Protected historical rules include:

- S1-E v2 pilot labels: `NEVER_TRAINING`;
- S1-E repeat labels: `NEVER_TRAINING`;
- S1-G v2 first-pass: `DESIGN_FAIL_DIAGNOSTIC_ONLY_NEVER_TRAINING`;
- S1-G repeat: `DO_NOT_RUN`;
- historical repeat/reliability labels: not extra training rows;
- S2-A Batch01: `DIAGNOSTIC_ONLY_NEVER_TRAINING`, effective fit rows = 0;
- Stage 7E and E3-E consumed final evidence: evaluation-only, never recycled;
- S1-F historical project-label fit: separate hard-closed historical path unless superseded by an explicit newer protocol.

`EQUAL_OR_UNSURE` remains ambiguity evidence and must never be silently coerced into A/B.

## S2-A learned-ranker safety

S2-A v1 may rank only exact authoritative S1-H-C assignment IDs.

Its executable fit harness remains fail-closed on provenance, corpus minimums, repeat reliability, family isolation, and deterministic evaluation. The existence of `fit_s2a_ranker()` is not permission to fit arbitrary data.

Current S2-A state:

- implementation through untouched-final evaluation: complete;
- Batch01: diagnostic-only;
- fit-eligible fresh Teacher corpus: unavailable;
- real S2-A fit: not executed;
- checkpoint/shadow/production: closed.

## GuitarSet archive/data safety

PR #91 introduced a separate real-guitar observed string/fret evidence path.

The approved GuitarSet archive is fail-closed against:

- oversized archive/member payloads;
- excessive member counts;
- duplicate member names;
- path traversal;
- symlink members;
- excessive compression ratios;
- excessive total uncompressed comp payload;
- unsupported members outside the approved `annotation/*_comp.jams` surface.

Rows with malformed/non-finite values, invalid time, MIDI-range violations, negative fret, or fret above the frozen maximum are quarantined instead of repaired.

Same-string ambiguity inside the conservative 50 ms local clustering window excludes the whole window from derived voicing gold. Direct note observations and derived voicing clusters remain distinct evidence types.

GuitarSet supplies observed string/fret placements only. It does not authorize claims about left-hand finger number, barre identity, comfort, biomechanics, or Teacher preference.

## GuitarSet split/leakage safety

`GUITARSET-SPLIT.v1` is frozen before fit.

- DEVELOPMENT performers: `00,01,04,05`;
- VALIDATION performer: `03`;
- UNTOUCHED_FINAL performer: `02`;
- performer overlap across roles must be zero;
- recording overlap across roles must be zero;
- note-id overlap across roles must be zero;
- voicing-id overlap across roles must be zero;
- validation may not enter fit;
- final may not enter fit, CV, model selection, or validation.

Because repertoire/style identities are shared across performer roles, this split supports only the claim `UNSEEN_PERFORMER_SEEN_REPERTOIRE`. Unseen-repertoire and unseen-style claims are forbidden.

## GuitarSet candidate-authority safety

The observed-voicing model target is:

`OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET`

For each event, candidate construction must:

- preserve the exact simultaneous MIDI pitch multiset;
- use frozen standard tuning;
- use at most one note per string;
- keep frets in `0..19`;
- include the observed GuitarSet realization;
- exclude single-candidate events from ranking fit/metrics;
- remain independent of H-C finger assignments, Teacher labels, S2-A preferences, historical labels, and model scores.

The learned model may only rank this exact physical candidate set. It has no authority to create or repair placements.

## GuitarSet frozen model-development contract

PR #93 froze the observed-voicing scientific contract before any fit:

- 28D static pitch/string/fret feature schema;
- feature SHA `05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38`;
- pairwise observed-vs-alternative objective;
- deterministic SHA-selected cap of 32 alternatives/event for fit;
- full candidate set retained for evaluation;
- `StandardScaler()`;
- no-intercept `LogisticRegression(C=1.0, class_weight=None, solver="lbfgs", max_iter=2000, random_state=0)`;
- no hyperparameter tuning;
- fixed comparator `LOW_TOTAL_FRET.v1`;
- frozen development, validation, final, bootstrap, and determinism gates;
- protocol SHA `1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d`.

Changing the target, split, features, candidate rules, comparator, model family, alternative-selection rule, or acceptance thresholds after observing outcomes requires a new explicit protocol version rather than an in-place rewrite.

## Current real-training gate

PR #93 is preregistration evidence only. Its explicit authorization remains:

- `training_authorized = false`;
- `checkpoint_authorized = false`;
- `runtime_connection_authorized = false`;
- `final_access_authorized = false`.

Therefore the current safe autonomous engineering boundary is:

- model-development implementation: allowed;
- deterministic candidate/feature generation: allowed;
- negative tests, leakage tests, regression tests, determinism tests: allowed;
- test-only/synthetic fitting needed to verify implementation behavior: allowed when it cannot consume protected project evidence or promote artifacts;
- real project `.fit()` on GuitarSet DEVELOPMENT evidence: closed until explicit training authorization;
- validation performer `03`: closed until development PASS;
- untouched-final performer `02`: closed until development + validation PASS and sealed development model;
- checkpoint retention: separate closed gate;
- GuitarTab Engine shadow/production: separate closed gates.

## Promotion gates

No model-development result automatically authorizes:

- retaining/promoting a checkpoint;
- replacing S1-H-C.v1 authority with provisional v2;
- activating a learned arbiter/refiner beyond its approved experiment;
- opening protected final evidence early;
- GuitarTab Engine shadow integration;
- production integration.

## Verification baseline

PR #93 merge-state verification recorded successful CI run #274 with unit tests and compile validation passing. The S2-A Batch01 regression workflow run #61 also passed. The Stage 7B-C2 comparison step was skipped by branch condition and is not counted as PASS evidence.

External Codex review was unavailable for recent PRs because review-usage limits were exhausted; no external-review PASS is claimed where it did not occur.

## Historical evidence files

Frozen preregistration/evidence JSON files are immutable historical snapshots. Do not rewrite them solely to match a later merge. Live status belongs in the top-level documentation.

## Development-control rule

Small, isolated engineering changes must begin from fresh repository truth and preserve all current authority/leakage boundaries. Any change that would alter the frozen scientific contract, consume protected labels, authorize real training, open validation/final evidence, retain a checkpoint, replace authoritative H-C, or connect shadow/production is a consequential gate and must not be inferred from routine implementation work.
