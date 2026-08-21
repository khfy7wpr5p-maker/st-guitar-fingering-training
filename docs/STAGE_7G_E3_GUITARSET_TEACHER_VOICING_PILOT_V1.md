# Stage 7G-E3 — GuitarSet Teacher Voicing Pilot v1

## Purpose

Collect an independent Teacher preference over **string/fret voicing geometry** without exposing the GuitarSet observed answer, learned-model score, deterministic baseline score, performer identity, recording identity, or validation/final data.

This is a **diagnostic usability/calibration pilot only**. It is not training data and is not a preregistered model validation gate.

## Question shown to the Teacher

For one fixed simultaneous MIDI pitch multiset, the UI asks:

> Bu sesleri gitarda sen hangi tel-perde düzeniyle çalardın?

The pilot accepts only events with **2..6 exact physical candidates** and displays the **complete candidate set**. The GuitarSet observed placement is therefore naturally present, but it is never identified and no candidate is specially inserted because it is the observed answer. Display order is deterministic and blinded.

Allowed responses:

- choose one displayed candidate;
- `EQUAL_OR_UNSURE`;
- `MANUAL_VOICING` using `string:fret` pairs such as `6:0,5:2,4:2,3:0`;
- reject a malformed/unusable task.

Manual input must preserve the exact pitch multiset, use distinct strings, stay within frets `0..19`, and match the deterministic physical candidate authority.

## Source isolation

Pilot construction accepts only the exact sealed GuitarSet archive SHA-256:

`06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe`

The builder validates archive metadata for the complete corpus, then reads JAMS bytes only for frozen `DEVELOPMENT` performers:

- `00`
- `01`
- `04`
- `05`

It must not read performer `03` validation JAMS bytes or performer `02` untouched-final JAMS bytes.

## Task selection

Default pilot size: **24 tasks**.

Selection is deterministic and label-blind:

1. derive conservative GuitarSet voicing events from DEVELOPMENT only;
2. require **2..6** exact physical candidates;
3. show **all** exact physical candidates for each selected task;
4. deduplicate equivalent semantic pitch/candidate sets;
5. balance across the four DEVELOPMENT performers;
6. prefer lower full-candidate-count tasks for pilot usability, then deterministic hash order;
7. blind the complete candidate-set display order;
8. never use learned-model scores, baseline scores, historical Teacher labels, validation labels, or final labels for task selection.

Showing the complete candidate set prevents the hidden observed answer from being inferable through a special “observed + sampled alternatives” inclusion rule.

Because this pilot is drawn from DEVELOPMENT data, any agreement statistics are **diagnostic only** and must not be reported as independent model validation.

## Teacher/internal separation

Teacher package contains:

- blinded HTML;
- blinded manifest JSON.

Internal audit contains:

- performer/recording/source identity;
- exact observed GuitarSet candidate ID;
- exact observed placement;
- task-selection provenance.

Internal audit fields are forbidden from the Teacher manifest and HTML.

## Response safety

The HTML:

- stores responses automatically in browser `localStorage`;
- restores answers after refresh/reopen;
- exposes a copyable JSON text area after all tasks are answered;
- provides both **JSON'u kopyala** and **JSON dosyası indir** paths.

This is intentionally more robust than relying on only one browser download button.

## Authorization boundary

The pilot freezes:

- `diagnostic_only_never_training = true`
- `training_authorized = false`
- `validation_access_authorized = false`
- `final_access_authorized = false`
- `checkpoint_authorized = false`
- `runtime_connection_authorized = false`

Teacher answers from this pilot may later be compared descriptively with GuitarSet observed choices, the baseline, and a sealed development model, but they may not retroactively tune the preregistered GuitarSet model or alter frozen validation/final gates.

## Build command

```bash
python scripts/build_guitarset_teacher_voicing_pilot_v1.py /path/to/GuitarSet.zip \
  --output-dir /tmp/guitarset_teacher_voicing_pilot
```

Expected Teacher output:

- `teacher/ST_Guitar_GuitarSet_TeacherVoicing_Pilot01.html`
- `teacher/ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_manifest.json`

Expected internal output:

- `internal/ST_Guitar_GuitarSet_TeacherVoicing_Pilot01_audit.json`

## Relationship to open PR #95

This pilot is architecturally independent of the open GuitarSet DEVELOPMENT-fit PR. It does not merge, validate, promote, or consume the model artifact from PR #95. It can be reviewed as a separate diagnostic data-collection layer.
