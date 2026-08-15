# Architecture

```text
Guitar Pro / MusicXML source (quarantine)
        ↓
Safe XML intake
        ↓
Notation/TAB stream selection
        ↓
Tuning + transpose/pitch-semantics normalization
        ↓
Event/chord extraction
        ↓
Independent physical pitch ↔ string/fret validation
        ↓
Deterministic physically-valid candidate generator  ← authoritative boundary
        ↓
Frozen stateless voicing specialists
(open_low / compact / research-only alternatives)
        ↓
Blind Teacher-GOLD preference supervision
        ↓
Stage 7G-E1 Teacher-GOLD router
        ↓
Negative result + Stage 7G-E2 error diagnostic
        ↓
Stage 7G-E3 Guitar Ergonomics Curriculum
  ├─ E3-A frozen L1→L4 + 40-descriptor contract
  ├─ E3-B target-blind curriculum generator
  ├─ E3-B-R1 sealed 400-task development batch
  └─ E3-C 400/400 blind Teacher-GOLD responses
        ↓
Frozen explicit ergonomics representation
  ├─ chord/candidate-set context
  ├─ open/fretted-note geometry
  ├─ left-hand position/span proxies
  ├─ barre-like same-fret proxy
  ├─ string span / adjacency / internal gaps
  └─ compact-minus-open_low proposal deltas
        ↓
Stage 7G-E3-D conservative compact-gate protocol
  ├─ default = open_low
  ├─ StandardScaler + unbalanced LogisticRegression
  ├─ 5-fold outer / 4-fold inner family-isolated development CV
  ├─ threshold selected from inner OOF only
  └─ no qualifying threshold → NO_SWITCH → open_low
        ↓
Stage 7G-E3-D-R1 manual Colab execution (pending)
        ↓
Positive development signal?
  ├─ NO → retain negative evidence / redesign only under a new protocol
  └─ YES → design new E3-E family-disjoint Teacher-GOLD validation
        ↓
New untouched E3-E validation (future)
        ↓
Future preregistered checkpoint-retention gate
        ↓
Future GuitarTab Engine SHADOW integration
```

## Authority boundary

1. Deterministic guitar rules own physical validity. AI may never manufacture a valid-looking placement outside the deterministic candidate set.
2. Learned specialists, routers, curriculum models, and future ergonomics models may score/rank/route only candidates that already passed physical validation.
3. Source XML pitch is not trusted blindly. Sounding pitch is independently recomputed from tuning + string + fret whenever observed technical placement exists.
4. Standard-notation and TAB staves representing the same event are one lineage, not two labels.
5. Written-guitar octave conventions are recorded explicitly and are never silently mixed with sounding pitch.
6. Dataset families never cross a declared train/held-out split.
7. Observed source placement, rule-derived property supervision, blind pairwise Teacher-GOLD, and richer full-candidate Teacher-GOLD are distinct supervision types and must not be silently mixed.
8. `open_low` is the current strongest simple Teacher-GOLD baseline and the default E3-D decision. `compact` is a gated alternative, not a co-equal default.
9. Stage 7E is permanently consumed/evaluation-only and may not be reused for training, tuning, calibration, feature selection, or new validation.
10. The original 556 decisive E1/E2 pairwise labels are consumed development evidence. Findings from them may motivate hypotheses but those rows are excluded from the E3-D fit.
11. The new E3 Batch01 contains 400 blind Teacher-GOLD responses from the same 40-family development domain: 399 decisive and 1 equal/unsure. These rows support E3-D development but are not untouched validation.
12. E3-D threshold selection is inner-CV-only. Outer-fold labels cannot alter thresholds, features, class weights, or hyperparameters after results are seen.
13. A positive E3-D result can justify designing E3-E only; it cannot authorize checkpoint retention or production integration.
14. Production integration remains closed until a separately preregistered checkpoint gate passes on genuinely new untouched Teacher-GOLD evidence.

## Current learning state

The system has demonstrated that target-blind specialist routing can learn useful corpus-behavior signal, but Teacher-GOLD preference is more conservative. On the original 556 decisive pairwise labels, the E1 router reached 70.50% event-weighted agreement versus 77.88% for `always_open_low`. E2 showed why: the router recovered 66 genuine `compact` preferences but introduced 107 false compact switches.

E3 changes the representation and decision policy without changing the physical-validity boundary. The target-blind curriculum and 40-descriptor ergonomics contract are implemented; a new 400-task blind Teacher-GOLD development batch is sealed and complete; and the conservative E3-D training protocol is now frozen before fit.

The next executable architecture step is the pinned manual Colab E3-D-R1 run. No E3-D model has been trained, no result-derived threshold has been selected, no checkpoint is retained, and no production/shadow integration is authorized.
