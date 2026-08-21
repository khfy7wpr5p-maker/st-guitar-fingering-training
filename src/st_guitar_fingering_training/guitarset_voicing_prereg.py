from __future__ import annotations

from hashlib import sha256
import json

GUITARSET_OBSERVED_VOICING_MODEL_VERSION = "GUITARSET-OBSERVED-VOICING-MODEL.v1"
GUITARSET_VOICING_FEATURE_VERSION = "GUITARSET-VOICING-FEATURES.v1"
GUITARSET_SOURCE_ARCHIVE_SHA256 = "06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe"
GUITARSET_SPLIT_VERSION = "GUITARSET-SPLIT.v1"
GUITARSET_VOICING_MAX_FRET = 19
GUITARSET_NEGATIVE_SAMPLE_CAP = 32

FEATURE_SPECS = (
    ("open_ratio", "open_note_count/note_count"),
    ("mean_fret", "mean(fret)/19"),
    ("max_fret", "max(fret)/19"),
    ("min_positive_fret", "min(fret>0)/19 else 0"),
    ("max_positive_fret", "max(fret>0)/19 else 0"),
    ("positive_fret_span", "(max(fret>0)-min(fret>0))/19 else 0"),
    ("string_span", "(max(string)-min(string))/5"),
    ("adjacent_string_ratio", "adjacent_occupied_pairs/max(1,note_count-1)"),
    ("internal_string_gap_ratio", "missing_strings_between_minmax/5"),
    ("mean_string", "mean(string-1)/5"),
    ("string_1_occupied", "1 if string 1 occupied else 0"),
    ("string_2_occupied", "1 if string 2 occupied else 0"),
    ("string_3_occupied", "1 if string 3 occupied else 0"),
    ("string_4_occupied", "1 if string 4 occupied else 0"),
    ("string_5_occupied", "1 if string 5 occupied else 0"),
    ("string_6_occupied", "1 if string 6 occupied else 0"),
    ("string_1_fret", "fret/19 if string 1 occupied else 0"),
    ("string_2_fret", "fret/19 if string 2 occupied else 0"),
    ("string_3_fret", "fret/19 if string 3 occupied else 0"),
    ("string_4_fret", "fret/19 if string 4 occupied else 0"),
    ("string_5_fret", "fret/19 if string 5 occupied else 0"),
    ("string_6_fret", "fret/19 if string 6 occupied else 0"),
    ("string_1_pitch", "midi/127 if string 1 occupied else 0"),
    ("string_2_pitch", "midi/127 if string 2 occupied else 0"),
    ("string_3_pitch", "midi/127 if string 3 occupied else 0"),
    ("string_4_pitch", "midi/127 if string 4 occupied else 0"),
    ("string_5_pitch", "midi/127 if string 5 occupied else 0"),
    ("string_6_pitch", "midi/127 if string 6 occupied else 0"),
)

EXPECTED_FEATURE_SCHEMA_SHA256 = "05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38"
EXPECTED_PROTOCOL_SHA256 = "1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def feature_schema_payload() -> dict:
    return {
        "version": GUITARSET_VOICING_FEATURE_VERSION,
        "max_fret": GUITARSET_VOICING_MAX_FRET,
        "features": [
            {"name": name, "definition": definition}
            for name, definition in FEATURE_SPECS
        ],
    }


def feature_schema_sha256() -> str:
    return _canonical_sha256(feature_schema_payload())


def protocol_payload() -> dict:
    return {
        "schema": "st-guitar-guitarset-observed-voicing-model-prereg-v1",
        "version": GUITARSET_OBSERVED_VOICING_MODEL_VERSION,
        "source_archive_sha256": GUITARSET_SOURCE_ARCHIVE_SHA256,
        "split_version": GUITARSET_SPLIT_VERSION,
        "benchmark_target": "UNSEEN_PERFORMER_SEEN_REPERTOIRE",
        "prediction_target": "OBSERVED_STRING_FRET_VOICING_FOR_FIXED_PITCH_MULTISET",
        "event_source": "DERIVED_DISTINCT_STRING_ONSET_CLUSTER_FROM_ACCEPTED_NOTE_GOLD",
        "candidate_set": {
            "tuning_midi_by_string": {"1": 64, "2": 59, "3": 55, "4": 50, "5": 45, "6": 40},
            "min_fret": 0,
            "max_fret": GUITARSET_VOICING_MAX_FRET,
            "same_pitch_multiset_required": True,
            "distinct_strings_required": True,
            "candidate_enumeration": "ALL_EXACT_PHYSICAL_ASSIGNMENTS_WITHIN_0_19",
            "single_candidate_events": "EXCLUDE_FROM_FIT_AND_RANKING_METRICS_REPORT_SEPARATELY",
        },
        "features": {
            "version": GUITARSET_VOICING_FEATURE_VERSION,
            "count": len(FEATURE_SPECS),
            "sha256": feature_schema_sha256(),
            "specs": feature_schema_payload()["features"],
        },
        "training": {
            "objective": "PAIRWISE_OBSERVED_VS_ALTERNATIVE",
            "negative_sampling": "UP_TO_32_ALTERNATIVES_BY_ASCENDING_SHA256(GUITARSET-NEGSEL.v1|voicing_id|canonical_candidate)",
            "symmetric_pairs": True,
            "model_pipeline": {
                "scaler": "StandardScaler()",
                "estimator": "LogisticRegression",
                "params": {
                    "C": 1.0,
                    "fit_intercept": False,
                    "class_weight": None,
                    "solver": "lbfgs",
                    "max_iter": 2000,
                    "random_state": 0,
                },
                "hyperparameter_tuning": False,
            },
        },
        "baseline": {
            "name": "LOW_TOTAL_FRET.v1",
            "rank_key": "(sum_fret,max_fret,positive_fret_span,-open_count,string_span,canonical_candidate)",
            "ascending": True,
        },
        "development": {
            "roles": ["DEVELOPMENT"],
            "cv": "LEAVE_ONE_DEVELOPMENT_PERFORMER_OUT_4_FOLDS",
            "metrics": [
                "event_top1",
                "event_mrr",
                "event_recall_at_3",
                "recording_macro_top1",
                "recording_macro_mrr",
            ],
            "pass": {
                "minimum_ambiguous_events": 1000,
                "macro_event_top1_delta_vs_baseline_gte": 0.03,
                "macro_event_mrr_delta_vs_baseline_gte": 0.05,
                "top1_fold_wins_gte": 3,
                "mrr_fold_wins_gte": 3,
                "deterministic_reproduction_runs": 10,
            },
        },
        "validation": {
            "performer": "03",
            "use": "ONE_SHOT_GATE_NO_TUNING",
            "minimum_ambiguous_events": 500,
            "pass": {
                "event_top1_delta_vs_baseline_gte": 0.02,
                "event_mrr_delta_vs_baseline_gte": 0.05,
                "recording_macro_top1_delta_gt": 0.0,
                "recording_macro_mrr_delta_gt": 0.0,
                "recording_block_bootstrap": {
                    "repetitions": 2000,
                    "seed": 0,
                    "confidence": 0.95,
                    "metric": "event_mrr_delta_vs_baseline",
                    "lower_bound_gt": 0.0,
                },
            },
        },
        "final": {
            "performer": "02",
            "open_only_if": "DEVELOPMENT_PASS_AND_VALIDATION_PASS_AND_MODEL_ARTIFACT_SEALED",
            "no_refit_after_validation": True,
            "no_tuning_after_open": True,
            "pass": {
                "event_top1_delta_vs_baseline_gt": 0.0,
                "event_mrr_delta_vs_baseline_gt": 0.0,
                "recording_macro_top1_delta_gt": 0.0,
                "recording_macro_mrr_delta_gt": 0.0,
                "recording_block_bootstrap": {
                    "repetitions": 2000,
                    "seed": 0,
                    "confidence": 0.95,
                    "metric": "event_mrr_delta_vs_baseline",
                    "lower_bound_gt": 0.0,
                },
            },
            "pass_semantics": "ELIGIBLE_FOR_CHECKPOINT_RETENTION_REVIEW_ONLY",
        },
        "forbidden_inputs": [
            "Teacher Correction labels",
            "S2-A preference labels",
            "historical Teacher labels",
            "model scores during split/candidate selection",
            "left-hand finger numbers",
            "barre labels",
        ],
        "training_authorized": False,
        "checkpoint_authorized": False,
        "runtime_connection_authorized": False,
        "final_access_authorized": False,
        "next_gate": "OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT",
    }


def protocol_sha256() -> str:
    return _canonical_sha256(protocol_payload())


def assert_frozen_protocol() -> None:
    if feature_schema_sha256() != EXPECTED_FEATURE_SCHEMA_SHA256:
        raise AssertionError("GuitarSet observed-voicing feature schema drift")
    if protocol_sha256() != EXPECTED_PROTOCOL_SHA256:
        raise AssertionError("GuitarSet observed-voicing preregistration drift")
    protocol = protocol_payload()
    if protocol["training_authorized"]:
        raise AssertionError("preregistration must not authorize training")
    if protocol["final_access_authorized"]:
        raise AssertionError("preregistration must not open untouched final")
