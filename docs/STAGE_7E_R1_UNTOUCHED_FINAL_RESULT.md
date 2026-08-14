# Stage 7E-R1 — Untouched Final Test Result

Status: **PASS PROMOTION GATE — NO CHECKPOINT / NO PRODUCTION INTEGRATION**

## Sealed evaluation

The final corpus and decision rule were committed to `main` before any router accuracy was computed.

- seal `main` commit: `6aae2b694e23a8997d440ffa0ecc01c4d26608c2`
- sealed artifact ID: `9222264940`
- artifact ZIP SHA-256: `74ceaf2ea3c8425a6f4031a5dbf26807e7e997c5b9747c79327ffc85387c8781`
- external source: `robust-guitar-tabs/code` at `f50309ad06dc734ddae5e3a0eda756fca221e2e7`
- 16 pinned GP3 source files
- source-hash overlap with development corpus: **0**

The target-free extraction contained 4550 structurally eligible chord events. Deterministic physical candidate validation found:

- 0 events with no physical candidates;
- 0 observed GP3 voicings missing from the physical candidate set;
- 591 single-candidate events excluded from ranking;
- **3959 ambiguous final-test events**;
- **13 final families with ambiguous events**.

The preregistered corpus sufficiency gate (at least 100 ambiguous events and 8 families) passed.

## Reproduction guard

Before accepting the final score, the prior development state reproduced:

- 33 unique admitted development XML;
- 25 development families;
- 1879 development chord events;
- frozen `open_low` development Top-1: `0.7915754923413567`;
- Stage 7D-A family-isolated CV macro router Top-1: `0.8386507946895563`;
- Stage 7D-A CV macro `open_low`: `0.7967706271049415`.

No final label entered specialist or router fitting. The evaluation router was fitted in memory on the previously accepted development families only.

## Untouched final result

| Metric | Router | always-open_low | Delta |
|---|---:|---:|---:|
| Event-weighted Top-1 | **0.456681** | 0.431169 | **+0.025511** |
| Macro-family Top-1 | **0.434132** | 0.395052 | **+0.039080** |

Additional diagnostics:

- stateless-oracle coverage: `0.9105834807`
- family outcomes versus `open_low`: **2 wins / 11 ties / 0 losses**
- router selections: `open_low` 3845, `compact` 114, `mid_position` 0, `high_position` 0

## Preregistered gate

The seal required both:

1. event-weighted router Top-1 > event-weighted `open_low`; and
2. macro-family router Top-1 >= macro-family `open_low`.

**Both gates passed.**

## Interpretation

The absolute final-test accuracy is materially lower than on the development corpus, so there is real domain shift and the Stage 7D-A development score must not be presented as general production accuracy.

However, the router's advantage over the simple `always-open_low` policy survived the untouched corpus:

- +2.55 percentage points event-weighted;
- +3.91 percentage points macro-family;
- no final family was worse than the baseline under the preregistered family comparison.

This is positive external evidence for the stateless routing idea. It supports a **promotion review**, not automatic deployment.

## Safety state

- final training rows: **0**
- final targets used for fit/tuning/calibration: **false**
- post-result tuning: **false**
- `common_tone` included: **false**
- checkpoint retained: **false**
- production integration: **false**
