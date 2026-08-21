# Stage 7G-E3 — GuitarSet Observed Voicing Model v1 DEVELOPMENT

## Scope

This stage implements and executes the already-merged `GUITARSET-OBSERVED-VOICING-MODEL.v1` preregistration using **DEVELOPMENT only**.

Allowed performers: `00, 01, 04, 05`.

Not opened in this stage:

- VALIDATION performer `03`;
- UNTOUCHED_FINAL performer `02`;
- Teacher Correction / S2-A labels;
- checkpoint retention;
- runtime or production integration.

The archive is bound to SHA-256 `06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe` before any JAMS content is read. The loader validates ZIP metadata for the full archive but deliberately reads JAMS bytes only for the 120 DEVELOPMENT recordings.

## DEVELOPMENT capacity

- recordings: 120
- accepted string-specific notes: 31,699
- quarantined notes: 35
- derived voicings: 8,330
- ambiguous voicings used for ranking: 7,919
- single-candidate voicings excluded from ranking metrics: 411
- exact physical candidates across all 8,330 voicings: 227,989

The preregistered minimum of 1,000 ambiguous events is therefore satisfied before model judgment.

## Frozen implementation

The implementation uses the preregistered:

- exact pitch-multiset-preserving 0..19 fret candidate set;
- 28D static feature schema;
- SHA-selected maximum 32 alternatives per ambiguous training event;
- symmetric observed-vs-alternative pairwise rows;
- `StandardScaler()` + fixed `LogisticRegression` configuration;
- `LOW_TOTAL_FRET.v1` comparator.

`MAX_ENUMERATED_CANDIDATES_PER_EVENT=10000` is a **fail-closed resource safety ceiling only**. It does not truncate candidates; exceeding it aborts the run.

## 4-fold unseen-performer DEVELOPMENT result

| Held-out performer | Ambiguous events | Learned Top-1 | Baseline Top-1 | Delta | Learned MRR | Baseline MRR | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00 | 2,290 | 0.669869 | 0.606114 | +0.063755 | 0.814880 | 0.682930 | +0.131950 |
| 01 | 2,191 | 0.772250 | 0.424920 | +0.347330 | 0.881751 | 0.564223 | +0.317528 |
| 04 | 1,865 | 0.738874 | 0.461662 | +0.277212 | 0.861177 | 0.574988 | +0.286189 |
| 05 | 1,573 | 0.752066 | 0.500954 | +0.251113 | 0.873914 | 0.577879 | +0.296035 |

Macro DEVELOPMENT:

- learned Top-1: `0.7332648050`
- baseline Top-1: `0.4984123638`
- Top-1 delta: `+0.2348524412`
- learned MRR: `0.8579304901`
- baseline MRR: `0.6000050472`
- MRR delta: `+0.2579254429`
- Recall@3: `0.9888483669`
- Top-1 fold wins: `4/4`
- MRR fold wins: `4/4`

All preregistered DEVELOPMENT gates PASS.

## Determinism and seal

The complete 4-fold DEVELOPMENT execution reproduced identically `10/10` times in the recorded execution environment.

- DEVELOPMENT event identity SHA-256: `3335a150d538258ce0e31c42e3b902f446bb0e2bbbcaa93cf0ae134c049c6e81`
- deterministic CV signature SHA-256: `ff8a0b588f2ab88925e4cb698b6268b494330e736c651c7d25c7aa165cacd19c`
- full DEVELOPMENT pair identity SHA-256: `728ace31810106c9d4ccae7cf5a15cfdf1402b59a5631fe61bbd5c8aad96acb4`
- sealed validation-only model artifact SHA-256: `5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869`

The model artifact stores exact float parameters as hexadecimal strings. It is a sealed DEVELOPMENT artifact for the later one-shot validation gate, **not** an authorized production checkpoint.

## State

`DEVELOPMENT_PASS_MODEL_SEALED_VALIDATION_CLOSED`

Next gate: `OBSERVED_VOICING_MODEL_VALIDATION_ONE_SHOT`.

Validation remains closed in this stage; there is no tuning or refit based on performer `03`, and untouched-final performer `02` remains closed.
