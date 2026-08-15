# Stage 7G-E3-B — Target-Blind Curriculum Generator

## Status

**Generator implementation only. No real E3 curriculum batch has been generated and no E3 model training is authorized by this stage.**

Stage 7G-E3-B implements the generator boundary frozen in Stage 7G-E3-A. It converts already target-blind Stage 7G sampling envelopes into an easy→hard curriculum without reading teacher responses or observed source TAB placements.

## Inputs

The generator accepts only Stage 7G annotation sampling envelopes whose proposals were produced from:

- chord pitches;
- explicit six-string tuning;
- deterministic physical candidates;
- the four frozen stateless specialist outputs.

E3-B keeps only events where frozen `open_low` and `compact` disagree.

## Difficulty assignment

For every eligible event the generator calls the frozen E3-A 40-descriptor feature contract and deterministic L1→L4 difficulty assignment.

No Teacher-GOLD response, source TAB target, family performance statistic, E1 prediction, E2 error label, or Stage 7E information enters difficulty assignment.

## Selection policy

`select_stage7g_e3_curriculum_batch()` requires an explicit quota for **every** level (`L1`, `L2`, `L3`, `L4`). There are intentionally no data-dependent default quotas.

Inside each level:

1. families are placed in a deterministic SHA-256 order;
2. events inside each family are placed in deterministic event-id hash order;
3. selection proceeds round-robin across families until that level quota is filled or the level is exhausted.

This prevents a long source family from filling the beginning of one curriculum level.

## Teacher-facing channel

The teacher manifest exposes only:

- opaque task id;
- pitches;
- tuning;
- anonymous physical option `A`;
- anonymous physical option `B`;
- responses `A`, `B`, `EQUAL_OR_UNSURE`.

It explicitly withholds:

- source identity;
- family identity;
- `open_low` / `compact` identity;
- curriculum level;
- all 40 feature values;
- observed source voicing.

Blind A/B side assignment is deterministic from the task id using the E3-specific salt `stage7g-e3-pairwise-v1` and is fixed before annotation.

## Internal audit channel

A separate non-teacher-facing audit stores the information required to reproduce a sealed batch:

- family and source identity;
- curriculum level;
- deterministic candidate count;
- blind A/B specialist mapping;
- frozen `open_low` and `compact` proposals;
- exact 40-descriptor feature record.

The audit declares that teacher response, observed string/fret target, and target voicing were not used for generation.

## Rule-derived property records

For selected L1/L2 events, E3-B may derive six factual property targets frozen by E3-A:

- more open notes;
- fewer fretted notes;
- lower mean positive fret;
- narrower positive-fret span;
- smaller string span;
- fewer internal string gaps.

These records are marked `RULE_DERIVED_PROPERTY` and `teacher_gold=false`. They are descriptive geometry supervision only. They must never be called “best fingering”, “natural fingering”, Teacher-GOLD, or teacher preference.

L3/L4 receive no rule-derived preference label.

## Scientific boundary

E3-B does not:

- generate a real batch from the user's corpus in this PR;
- collect teacher labels;
- fit a model;
- tune a threshold or hyperparameter;
- reuse the consumed 556 Teacher-GOLD rows as fresh evidence;
- reuse Stage 7E;
- retain a checkpoint;
- authorize production integration.

A later batch-generation run must pin source hashes, source-family mapping, specialist reconstruction identity, level quotas, and generated artifact hashes before teacher annotation begins.

## Next stage

After E3-B is merged, a separate execution gate may generate the first sealed curriculum batch. The preferred sequence is:

1. inspect target-blind level counts without teacher labels;
2. freeze explicit L1/L2/L3/L4 quotas before seeing any new Teacher-GOLD responses;
3. generate and hash the teacher manifest + internal audit + L1/L2 property records;
4. only then begin Stage 7G-E3-C teacher annotation pilot.
