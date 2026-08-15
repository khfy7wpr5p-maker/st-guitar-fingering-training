# Stage 7G-E3-D-R1 — Pinned manual Colab execution package

## State

This package prepares the **execution harness only**. It does not execute E3-D training, inspect outer-CV results, retain a checkpoint, or integrate anything into production.

The workflow is deliberately two-part:

1. **R1A — execution harness:** merge the tested loader/preflight/nested-CV code and fail-closed notebook template.
2. **R1B — SHA pin:** after R1A merges, replace `__PIN_AFTER_R1A_MERGE__` in the notebook with the exact R1A merge SHA. The notebook cannot pass its first cell before this pin exists.

Only after R1B is on `main` may the user run the notebook in Colab.

## Frozen execution semantics

R1 implements the merged Stage 7G-E3-D protocol without adding a search dimension:

- model inputs: exactly the frozen 40 `STAGE7G_E3_FEATURE_NAMES` descriptors;
- positive class: `COMPACT`;
- model: `StandardScaler()` + `LogisticRegression(max_iter=2000, class_weight=None, C=1.0, solver="lbfgs", random_state=0)`;
- outer CV: `StratifiedGroupKFold(5, shuffle=True, random_state=731)`;
- inner CV: `StratifiedGroupKFold(4, shuffle=True, random_state=7310 + outer_fold_index)`;
- execution clarification frozen before any E3-D result: `outer_fold_index` is Python zero-based `0..4`, therefore inner seeds are exactly `7310..7314`;
- threshold candidates: `[0.50, 0.60, 0.70, 0.80, 0.90, 0.95]`;
- threshold eligibility and tie-breaks are exactly those in the merged E3-D protocol;
- no eligible threshold means `NO_SWITCH`, i.e. always `OPEN_LOW` for that outer fold;
- outer labels never influence threshold choice;
- no model object is returned for serialization and the notebook exports aggregate evidence JSON only.

## External input gate

The notebook accepts only the two sealed external artifacts already preregistered by E3-D:

- `ST_Guitar_Stage7G_E3_B_R1_Curriculum_Batch01_400.zip`
  - outer SHA-256 `e0ff5c2796ddc9950ddad5e27cc754629baf5cf5c582ad769f88a321ea8d87ef`
  - internal audit SHA-256 `e8fa34998a409a275d372ae089b9a3f3ed1ea5b53de5c15e58a61de0210a2915`
  - blind teacher manifest SHA-256 `433bd01d1d8abee7e92ace335733570fb624bf17d70904c42bf9669b45fe9af2`
- `ST_Guitar_E3_Batch01_choices_400of400.json`
  - SHA-256 `db0e752ec7b9e0e1b333a217d904175f4e57cd89a32b2511330ebab7b8c6c12e`

The ZIP is **not extracted to disk**. The harness reads bounded JSON members in memory, locates the internal audit and teacher manifest by their frozen schema IDs, then verifies their exact hashes.

The loader also verifies before fit:

- exact 400-task set across audit, teacher manifest, and response export;
- teacher option A/B placements exactly match the audit's blinded `open_low`/`compact` mapping;
- exact 40-feature contract and feature-list SHA;
- finite features only;
- L1=140, L2=120, L3=80, L4=60;
- decoded `OPEN_LOW=311`, `COMPACT=88`, `EQUAL_OR_UNSURE=1`;
- exactly 399 decisive rows and 40 families;
- family isolation in every outer and inner fold;
- both binary classes in every training partition.

Any mismatch aborts before model fit.

## Manual Colab sequence

The notebook cells are intentionally separated:

1. fail-closed exact Git SHA pin;
2. clone/checkout/install;
3. manual upload of the two sealed artifacts;
4. identity + hash + split preflight — **no fit**;
5. visible `STOP: PREFLIGHT PASS` message;
6. separate **MANUAL TRAIN CELL** that runs the frozen nested development CV;
7. aggregate result export.

The exported JSON must keep:

- `checkpoint_retained=false`;
- `production_integration=false`;
- `stage7e_used=false`.

## Scientific interpretation

This run is nested **development CV**, not untouched final validation. A positive result can authorize only the design of a new E3-E untouched Teacher-GOLD validation package. It cannot authorize checkpoint retention or production/shadow integration.

If the frozen continuation gate fails, the result is `NEGATIVE_DEVELOPMENT_CV_NO_PROMOTION` and no threshold/model rescue is allowed on the same run.
