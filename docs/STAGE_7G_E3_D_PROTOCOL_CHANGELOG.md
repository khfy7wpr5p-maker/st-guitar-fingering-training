# Stage 7G-E3-D protocol change note

This stage intentionally changes the decision policy relative to Stage 7G-E1 without claiming new validation evidence.

Stage 7G-E1 used a balanced logistic model with a fixed 0.5 threshold and produced too many false `compact` switches. Stage 7G-E2 showed that false positives, not an inability to recognize `compact`, were the dominant failure mode. E3-D therefore freezes a different development hypothesis before any new fit:

- use the full frozen E3 ergonomics representation;
- keep `open_low` as the default;
- use an unbalanced logistic probability model (`class_weight=None`);
- select a conservative compact threshold only inside inner family-isolated CV;
- fall back to `NO_SWITCH` when no threshold meets precision and baseline-safety requirements.

This note does not add data, fit a model, select a threshold, or authorize checkpoint retention. It exists only to make the scientific change from E1 explicit rather than silent.
