from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

import numpy as np

from .dataset import Voicing, valid_chord_voicings
from .intake import ParsedSource
from .synthetic_behavior import _feature_vector


ROLLOUT_SEED_POLICY = "single_candidate_else_open_low_prediction"
ROLLOUT_PREVIOUS_CONTEXT = "previous_system_prediction"


def _observed_voicing(event) -> Voicing:
    return tuple(sorted(
        (placement.sounding_midi, placement.string, placement.fret)
        for placement in event.placements
    ))


def _predict_style_candidate(
    model: object,
    style: str,
    candidates: tuple[Voicing, ...],
    previous_prediction: Voicing | None,
) -> Voicing:
    """Choose one candidate without access to the observed target voicing."""
    if not candidates:
        raise ValueError("cannot rank an empty candidate set")
    if len(candidates) == 1:
        return candidates[0]
    if style == "common_tone" and previous_prediction is None:
        raise ValueError("common_tone rollout requires a previous system prediction")
    if style != "common_tone" and previous_prediction is not None:
        raise ValueError("stateless specialist prediction cannot receive previous context")

    X = np.asarray(
        [_feature_vector(style, candidate, previous_prediction) for candidate in candidates],
        dtype=np.float64,
    )
    scores = np.asarray(model.decision_function(X), dtype=np.float64)
    if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
        raise ValueError("invalid specialist score vector")
    winner = max(range(len(candidates)), key=lambda index: (scores[index], -index))
    return candidates[winner]


def rollout_common_tone_report(
    real_sources: Iterable[ParsedSource],
    specialist_models: Mapping[str, object],
) -> dict:
    """Evaluate common-tone continuity with system-predicted previous context.

    The rollout path never feeds an observed previous real voicing into the
    common-tone specialist. The first chord of each source is seeded by the
    deterministic sole candidate when unambiguous, otherwise by the frozen
    open-low specialist. Later single-candidate events update context
    deterministically; later ambiguous events are predicted by common-tone.

    Teacher-forced common-tone and always-open-low are reported only as
    diagnostics on the same evaluated ambiguous events.
    """
    if "open_low" not in specialist_models or "common_tone" not in specialist_models:
        raise ValueError("Stage 7D-B requires open_low and common_tone specialists")
    sources = tuple(real_sources)
    if not sources:
        raise ValueError("no real sources for common-tone rollout")

    per_family: dict[str, dict[str, int]] = defaultdict(lambda: {
        "events": 0,
        "rollout_correct": 0,
        "teacher_forced_correct": 0,
        "open_low_correct": 0,
        "context_diverged": 0,
    })
    chord_events = 0
    seed_events = 0
    deterministic_context_updates = 0
    evaluated_events = 0

    for source in sources:
        previous_prediction: Voicing | None = None
        previous_observed: Voicing | None = None

        for event in source.events:
            if not event.is_chord:
                continue
            chord_events += 1
            observed = _observed_voicing(event)
            pitches = tuple(sorted(placement.sounding_midi for placement in event.placements))
            candidates = valid_chord_voicings(pitches, event.tuning)
            if not candidates:
                raise ValueError("rollout chord has no physically valid candidates")
            if observed not in candidates:
                raise ValueError("observed real voicing missing from deterministic candidate set")

            if previous_prediction is None:
                if len(candidates) == 1:
                    previous_prediction = candidates[0]
                else:
                    previous_prediction = _predict_style_candidate(
                        specialist_models["open_low"], "open_low", candidates, None
                    )
                previous_observed = observed
                seed_events += 1
                continue

            if len(candidates) == 1:
                previous_prediction = candidates[0]
                previous_observed = observed
                deterministic_context_updates += 1
                continue

            if previous_observed is None:
                raise AssertionError("teacher-forced diagnostic context missing")

            context_diverged = previous_prediction != previous_observed
            rollout_choice = _predict_style_candidate(
                specialist_models["common_tone"],
                "common_tone",
                candidates,
                previous_prediction,
            )
            teacher_forced_choice = _predict_style_candidate(
                specialist_models["common_tone"],
                "common_tone",
                candidates,
                previous_observed,
            )
            open_low_choice = _predict_style_candidate(
                specialist_models["open_low"], "open_low", candidates, None
            )

            family = per_family[source.family_id]
            family["events"] += 1
            family["rollout_correct"] += int(rollout_choice == observed)
            family["teacher_forced_correct"] += int(teacher_forced_choice == observed)
            family["open_low_correct"] += int(open_low_choice == observed)
            family["context_diverged"] += int(context_diverged)
            evaluated_events += 1

            previous_prediction = rollout_choice
            previous_observed = observed

    if evaluated_events == 0:
        raise ValueError("no ambiguous post-seed events for common-tone rollout")

    family_reports = {}
    for family_id, counts in sorted(per_family.items()):
        events = counts["events"]
        if events == 0:
            continue
        family_reports[family_id] = {
            "events": events,
            "rollout_top1": counts["rollout_correct"] / events,
            "teacher_forced_top1": counts["teacher_forced_correct"] / events,
            "always_open_low_top1": counts["open_low_correct"] / events,
            "context_divergence_rate": counts["context_diverged"] / events,
        }
    if not family_reports:
        raise ValueError("no families with common-tone rollout events")

    rollout_correct = sum(item["rollout_correct"] for item in per_family.values())
    teacher_forced_correct = sum(item["teacher_forced_correct"] for item in per_family.values())
    open_low_correct = sum(item["open_low_correct"] for item in per_family.values())
    context_diverged = sum(item["context_diverged"] for item in per_family.values())

    rollout_top1 = rollout_correct / evaluated_events
    teacher_forced_top1 = teacher_forced_correct / evaluated_events
    open_low_top1 = open_low_correct / evaluated_events

    return {
        "stage": "7D-B",
        "status": "DIAGNOSTIC_PROTOCOL",
        "rollout_kind": "common_tone_self_rollout_with_target_blind_seed",
        "seed_policy": ROLLOUT_SEED_POLICY,
        "rollout_previous_context": ROLLOUT_PREVIOUS_CONTEXT,
        "observed_previous_voicing_in_rollout_features": False,
        "teacher_forced_context": "diagnostic_comparator_only",
        "real_training_rows": 0,
        "real_model_fit": False,
        "chord_events": chord_events,
        "seed_events": seed_events,
        "deterministic_single_candidate_context_updates": deterministic_context_updates,
        "evaluated_ambiguous_post_seed_events": evaluated_events,
        "event_weighted_rollout_top1": rollout_top1,
        "event_weighted_teacher_forced_top1": teacher_forced_top1,
        "event_weighted_always_open_low_top1": open_low_top1,
        "rollout_delta_vs_open_low": rollout_top1 - open_low_top1,
        "rollout_gap_vs_teacher_forced": rollout_top1 - teacher_forced_top1,
        "context_divergence_rate": context_diverged / evaluated_events,
        "macro_family_rollout_top1": float(np.mean([item["rollout_top1"] for item in family_reports.values()])),
        "macro_family_teacher_forced_top1": float(np.mean([item["teacher_forced_top1"] for item in family_reports.values()])),
        "macro_family_always_open_low_top1": float(np.mean([item["always_open_low_top1"] for item in family_reports.values()])),
        "evaluated_families": len(family_reports),
        "families": family_reports,
        "checkpoint_retained": False,
        "production_integration": False,
    }
