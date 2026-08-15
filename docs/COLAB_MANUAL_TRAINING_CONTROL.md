# Manual Colab Training Control

## Decision

For ST Guitar Fingering Training, the preferred execution model is **GitHub-controlled protocol + manually operated Google Colab training**.

Neither environment is the sole authority:

- **GitHub** owns versioned code, protocol, tests, evidence contracts, and merge history.
- **Colab** is a disposable execution environment where the user can manually inspect and run the approved training steps.

This hybrid model gives stronger traceability than an unpinned ad-hoc Colab notebook and more human execution control than an unattended training job.

## Why not train from an editable notebook alone?

A free-form notebook can silently drift:

- cells may be edited after earlier cells were run;
- execution order may differ from notebook order;
- package versions may change;
- uploaded data may be a different file with the same display name;
- thresholds or model settings can be changed after results are seen.

Therefore a notebook result is trusted only when it proves its execution identity.

## Required pre-run identity block

Before any model fit, the Colab run must print and save:

1. repository full name;
2. exact approved Git commit SHA;
3. `git rev-parse HEAD` output matching that SHA;
4. input data file names, byte sizes, and SHA-256 hashes;
5. Python version;
6. NumPy and scikit-learn versions;
7. frozen random seeds/model configuration;
8. protocol/stage identifier;
9. statement that Stage 7E is not mounted or used;
10. statement identifying whether the data are rule-derived, development-consumed, new Teacher-GOLD development, or untouched validation.

If any identity check fails, the notebook must stop before training.

## Recommended manual run sequence

### Gate 1 — Code pin

Clone the repository and checkout the exact approved commit SHA. Do not train from a moving branch name such as `main` without subsequently pinning and printing its resolved SHA.

### Gate 2 — Environment

Install the repository from the checked-out commit. Print dependency versions. Run the relevant unit tests or a frozen preflight script before any fit.

### Gate 3 — Data upload and hash verification

Upload the sealed input artifacts manually. Compute SHA-256 inside Colab and compare them with the preregistered expected hashes.

A matching file name is not sufficient.

### Gate 4 — Pre-fit report

Before fitting, display:

- number of events;
- number of independent families;
- curriculum level counts where applicable;
- label provenance counts;
- excluded/tied/invalid row counts;
- train/development/validation family disjointness checks.

The user should be able to stop here if the input does not look correct.

### Gate 5 — Explicit manual training cell

Keep model fitting in a separate clearly labelled cell. The preceding cells should perform only loading, validation, feature construction, and reporting.

Do not combine data inspection, parameter editing, and fit in one opaque cell.

### Gate 6 — Frozen evaluation

Run only the metrics preregistered for that stage. Do not change thresholds, features, class weights, folds, or hyperparameters after viewing the result unless a new experiment is preregistered.

### Gate 7 — Evidence export

Export a small machine-readable run result containing:

- exact code SHA;
- exact input hashes;
- environment versions;
- frozen configuration;
- aggregate metrics;
- scientific-boundary flags;
- whether a checkpoint was retained.

Raw copyrighted source files and raw teacher-label rows should remain outside Git unless separately allowed by the data contract.

## Checkpoint rule

A successful Colab run does **not** automatically authorize checkpoint retention.

The notebook should default to:

- `checkpoint_retained = false`
- `production_integration = false`

A model file may be retained only if the relevant stage had a preregistered checkpoint gate before the untouched validation result was inspected.

## Reliability comparison

### GitHub CI is stronger for

- reproducible code identity;
- automated regression tests;
- immutable review history;
- proving exactly which commit passed tests;
- preventing accidental undocumented code drift.

### Manually operated Colab is stronger for

- user-visible control of expensive training;
- inspecting uploaded data before fit;
- stopping before a suspicious run;
- GPU/CPU execution without adding training secrets or large datasets to GitHub;
- keeping private/large training files outside the repository.

### Recommended project rule

**Do not choose one instead of the other.**

Use GitHub to approve and freeze the experiment, then use a generated/pinned Colab notebook to execute it manually. Return only the hashed aggregate evidence to a new GitHub PR. GitHub CI then validates the evidence schema and project boundaries.

## Assistant boundary

The assistant can prepare and review the pinned Colab notebook, run local deterministic reproductions when possible, and inspect user-provided Colab outputs/screenshots. The assistant cannot independently launch or control the user's remote Colab runtime, so a run must not be described as “executed in Colab” unless the user actually runs it there and supplies the resulting evidence.
