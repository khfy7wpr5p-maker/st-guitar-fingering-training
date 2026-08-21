from __future__ import annotations

import json
from pathlib import Path

from st_guitar_fingering_training.guitarset_voicing_development import verify_sealed_json


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "evidence" / "stage7g_e3_guitarset_observed_voicing_cross_repo_shadow_compatibility_v1.json"
HISTORICAL_REVIEW = ROOT / "evidence" / "stage7g_e3_guitarset_observed_voicing_shadow_integration_review_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cross_repo_shadow_review_is_sealed_and_runtime_stays_closed() -> None:
    payload = _load(REVIEW)
    verify_sealed_json(payload, "evidence_sha256")

    assert payload["evidence_sha256"] == "7a8158b295912df0fe743f605df799362fcc164f01e3d5357a62e5e3835af789"
    assert payload["status"] == "CROSS_REPO_SHADOW_COMPATIBILITY_PASS_OFFLINE_ADAPTER_ELIGIBLE_RUNTIME_CLOSED"
    assert payload["retained_model_artifact_sha256"] == "5d109e3b46ef286439f00ad6fa5885fc7bdf13e070974c49040c27b007461869"
    assert payload["feature_schema_sha256"] == "05f8fda622f3901869a149db3e2cca2baf1310f4834d39e278e36428ae48cd38"
    assert payload["prereg_protocol_sha256"] == "1cbb3d219e8009c90c71075019a69a55c06a2893c12bd50264e66eda956dbc2d"

    runtime = payload["runtime_candidate_contract"]
    model = payload["model_domain"]
    assert runtime["document_type"] == "GuitarVoicingCandidateModel"
    assert runtime["contract_version"] == "1.0.0"
    assert runtime["policy"] == "STANDARD_SIX_STRING_DISTINCT_STRING_1.0"
    assert runtime["minimum_fret"] == model["minimum_fret"] == 0
    assert runtime["maximum_fret"] == 20
    assert model["maximum_fret"] == 19
    assert runtime["standard_tuning_midi_by_string"] == model["standard_tuning_midi_by_string"] == [64, 59, 55, 50, 45, 40]

    policy = payload["mandatory_offline_adapter_policy"]
    assert policy["no_candidate_generation"] is True
    assert policy["no_candidate_filtering"] is True
    assert policy["no_candidate_mutation"] is True
    assert policy["out_of_model_domain_policy"] == "IF_ANY_CANDIDATE_HAS_FRET_GT_19_THEN_NO_SCORE_NO_TRUNCATION"
    assert policy["optimizer_decision_effect"] is False
    assert policy["tab_output_effect"] is False
    assert policy["require_node_python_score_parity_before_execution_review"] is True

    assert payload["offline_node_adapter_implementation_authorized"] is True
    assert payload["shadow_execution_authorized"] is False
    assert payload["runtime_connection_authorized"] is False
    assert payload["authoritative_decision_effect_authorized"] is False
    assert payload["production_authorized"] is False
    assert payload["refit_authorized"] is False
    assert payload["tuning_authorized"] is False
    assert payload["next_gate"] == "OFFLINE_NODE_SHADOW_ADAPTER_IMPLEMENTATION_AND_CROSS_LANGUAGE_PARITY"


def test_historical_pr102_review_is_preserved_and_only_runtime_assumptions_are_superseded() -> None:
    historical = _load(HISTORICAL_REVIEW)
    verify_sealed_json(historical, "evidence_sha256")
    payload = _load(REVIEW)

    assert historical["evidence_sha256"] == payload["source_shadow_review_v1_evidence_sha256"]
    assert historical["engine_max_fret"] == 24
    assert historical["physical_candidate_authority"] == "valid_chord_voicings"

    supersession = payload["supersession"]
    assert supersession["historical_review_v1_rewritten"] is False
    assert supersession["historical_review_v1_training_repo_engine_max_fret"] == 24
    assert supersession["actual_runtime_engine_max_fret"] == 20
    assert supersession["historical_review_v1_candidate_authority"] == "valid_chord_voicings"
    assert supersession["actual_runtime_candidate_authority"] == "GuitarVoicingCandidateModel 1.0.0"
    assert supersession["scope"].startswith("SUPERSEDE_ONLY_CROSS_REPO_RUNTIME_TARGET_ASSUMPTIONS")
