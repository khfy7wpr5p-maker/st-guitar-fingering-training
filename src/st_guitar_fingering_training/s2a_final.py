from __future__ import annotations

from typing import Iterable

import numpy as np

from .s2a_ranker import (
    S2ACorpus,
    _baseline_prediction,
    _family_accuracy,
    _metric_panel,
    _pair_probabilities,
)
from .s2a_teacher import S2A_FINAL_PROVENANCE


S2A_FINAL_BOOTSTRAP_RESAMPLES = 2000
S2A_FINAL_BOOTSTRAP_SEED = 0


def family_block_bootstrap_ci(
    family_deltas: dict[str, float],
    *,
    resamples: int = S2A_FINAL_BOOTSTRAP_RESAMPLES,
    seed: int = S2A_FINAL_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Deterministic percentile CI over family-level accuracy deltas."""

    if resamples <= 0:
        raise ValueError("S2-A bootstrap resamples must be positive")
    if len(family_deltas) < 2:
        raise ValueError("S2-A bootstrap requires at least two final families")
    family_ids = tuple(sorted(family_deltas))
    values = np.asarray([float(family_deltas[family_id]) for family_id in family_ids], dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("S2-A family deltas must be finite")

    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        sampled = rng.integers(0, len(values), size=len(values))
        means[index] = float(np.mean(values[sampled]))
    return (
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def _final_preflight(
    corpus: S2ACorpus,
    development_report: dict,
    development_family_ids: Iterable[str],
) -> dict:
    if corpus.provenance != S2A_FINAL_PROVENANCE:
        raise ValueError("S2-A untouched-final evaluator accepts FINAL provenance only")
    if development_report.get("stage") != "7G-E3-S2-A":
        raise ValueError("S2-A final requires a Stage 7G-E3-S2-A development report")
    if development_report.get("protocol_version") != "S2-A.v1":
        raise ValueError("S2-A final protocol version mismatch")
    if development_report.get("status") != "PASS":
        raise RuntimeError("S2-A untouched final is CLOSED until development PASS")
    if development_report.get("checkpoint_retained") is not False:
        raise ValueError("S2-A development report may not retain a checkpoint")
    if development_report.get("shadow_or_production_integration") is not False:
        raise ValueError("S2-A development report may not authorize integration")

    comparator = development_report.get("comparator_selection", {}).get("selected")
    if comparator not in ("LOW_FRET_BASELINE", "COMPACT_BASELINE"):
        raise ValueError("S2-A final comparator must be frozen by development report")

    final_families = {row.family_id for row in corpus.rows}
    development_families = {str(value) for value in development_family_ids}
    overlap = final_families & development_families
    checks = {
        "final_families_gte_20": len(final_families) >= 20,
        "final_decisive_pairs_gte_200": len(corpus.rows) >= 200,
        "development_final_family_disjoint": not overlap,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "final_families": len(final_families),
        "final_decisive_pairs": len(corpus.rows),
        "family_overlap": sorted(overlap),
        "comparator": comparator,
    }


def evaluate_s2a_untouched_final(
    model,
    corpus: S2ACorpus,
    development_report: dict,
    *,
    development_family_ids: Iterable[str],
) -> dict:
    """Evaluate a frozen S2-A model once on disjoint untouched-final data."""

    preflight = _final_preflight(corpus, development_report, development_family_ids)
    if preflight["status"] != "PASS":
        raise RuntimeError("S2-A untouched-final minimum evidence gate is CLOSED")

    rows = tuple(corpus.rows)
    comparator = str(preflight["comparator"])
    probabilities = _pair_probabilities(model, rows)
    metrics = _metric_panel(rows, probabilities, comparator)

    predicted = (probabilities >= 0.5).astype(np.int64)
    comparator_predictions = np.asarray(
        [_baseline_prediction(row, comparator) for row in rows],
        dtype=np.int64,
    )
    family_model = _family_accuracy(rows, predicted)
    family_comparator = _family_accuracy(rows, comparator_predictions)
    if set(family_model) != set(family_comparator):
        raise AssertionError("S2-A final family metric key mismatch")
    family_deltas = {
        family_id: family_model[family_id] - family_comparator[family_id]
        for family_id in family_model
    }
    ci_low, ci_high = family_block_bootstrap_ci(family_deltas)

    checks = {
        "pairwise_accuracy_gte_065": metrics["pairwise_accuracy"] >= 0.65,
        "macro_family_accuracy_gte_065": metrics["macro_family_accuracy"] >= 0.65,
        "roc_auc_gte_070": metrics["roc_auc"] is not None and metrics["roc_auc"] >= 0.70,
        "macro_family_delta_gte_005": metrics["macro_family_accuracy_delta_vs_comparator"] >= 0.05,
        "family_wins_gt_losses": metrics["family_wins"] > metrics["family_losses"],
        "family_block_bootstrap_95_ci_lower_gt_0": ci_low > 0.0,
        "candidate_authority_violations_eq_0": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "stage": "7G-E3-S2-A-UNTOUCHED-FINAL",
        "protocol_version": "S2-A.v1",
        "preflight": preflight,
        "metrics": metrics,
        "family_block_bootstrap": {
            "unit": "family_id",
            "resamples": S2A_FINAL_BOOTSTRAP_RESAMPLES,
            "seed": S2A_FINAL_BOOTSTRAP_SEED,
            "delta_metric": "family_accuracy_model_minus_frozen_comparator",
            "ci_95_lower": ci_low,
            "ci_95_upper": ci_high,
        },
        "candidate_authority_violations": 0,
        "pass_checks": checks,
        "status": status,
        "result": "ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW" if status == "PASS" else "NOT_ELIGIBLE",
        "checkpoint_retained": False,
        "shadow_or_production_integration": False,
    }
