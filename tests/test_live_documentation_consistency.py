from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_DOCS = (
    "README.md",
    "ARCHITECTURE.md",
    "STATUS.md",
    "ROADMAP.md",
    "SAFETY.md",
    "DATASET_CONTRACT.md",
)

COMMON_REQUIRED = (
    "LIVE_DOCUMENTATION_GUITARSET_V2_SYNC_COMPLETE",
    "LIVE_DOCUMENTATION_COMPATIBILITY_GOVERNANCE_HARDENED",
    "Scientific synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115)",
    "Compatibility/governance hardening baseline: `5b18e0c6ac44ab3fba575658dd6ac8814cc1f0f8` (PR #121)",
    "GUITARSET-OBSERVED-VOICING-MODEL.v2",
    "candidate domain: 0..20",
    "observed positive-gold domain: 0..19",
    "fret20QualityAuthority=false",
    "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314",
    "617981e90cce46c941596d1bd50ffffff64e6816c59d8f0dbed1acd6d8938285",
    "db67d88c4889a2b8c63411cd1e9bbd7481248dfbdd76da67f5df60b3871b4c02",
    "f42809c1ca9d5f6ff1c62dd072c91a9195bb46e1714e88bd84e8a5a57eef9140",
    "GUITARSET_V2_CONTROLLED_OFFLINE_SHADOW_EVIDENCE_COMPLETE",
    "ENGINE_RUNTIME_SHADOW_CONNECTION_REVIEW",
    "new_training_or_refit_authorized=false",
    "runtime_connection_authorized=false",
    "production_authorized=false",
    "NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED",
    "evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json",
    "30f31a2322d0bdb45422c9715eb4a720d8b14c87b2fb1015fb457cb199392670",
    "0321a793bce30a9857720e9ec61c289e40ab2eef02f05c9fbe80e782152c491e",
)

STALE_LIVE_CLAIMS = (
    "Current `main` baseline after merged PR #93",
    "Current live baseline after merged PR #93",
    "Current main baseline after merged PR #93",
    "Architecture synchronization base (PR #93 merge)",
    "Synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).",
    "Documentation synchronization source: `929264a1778b061ff21464da41ecacbcd952a3cd` (PR #115).",
    "PR #90 remains open",
    "PR #90 OPEN",
    "PR #67 S1-D legacy draft | Open draft",
    "PR #67 (`Stage 7G-E3-S1-D`) remains a draft",
    "GuitarSet real model fit: ⛔ not executed",
    "OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT",
    "development implementation + fit                     ⏳ NEXT GATE",
    "A separate numerical-convergence hardening record may be produced",
    "Numerical optimizer-convergence hardening is a separate evidence task",
    "Residual evidence limitation",
    "does not include a gradient norm",
    "Any numerical-convergence hardening requires",
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_all_live_documents_share_the_v2_identity_and_closed_authority_boundary():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        for marker in COMMON_REQUIRED:
            assert marker in text, f"{relative_path} missing {marker}"


def test_stale_live_claims_cannot_return():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        for stale_claim in STALE_LIVE_CLAIMS:
            assert stale_claim not in text, f"{relative_path} contains stale claim: {stale_claim}"


def test_live_status_distinguishes_untrained_s2a_from_trained_guitarset_v2():
    status = read("STATUS.md")
    assert "S2-A Teacher naturalness" in status and "no real fit" in status
    assert "Development, validation, final, retention, and integration review complete" in status
    assert "PR #90" in status and "Closed without merge" in status
    assert "PR #67 S1-D legacy draft" in status and "Closed without merge" in status


def test_live_documents_bind_completed_numerical_hardening_without_runtime_authority():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        assert "NUMERICAL_HARDENING_PASS_MODEL_UNCHANGED_RUNTIME_CLOSED" in text
        assert "evidence/stage7g_e4_guitarset_observed_voicing_numerical_hardening_v2.json" in text
        assert "n_iter=37" in text
        assert "runtime_connection_authorized=false" in text
        assert "production_authorized=false" in text


def test_provenance_anchors_are_not_presented_as_current_blob_identity():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        assert "provenance anchors" in text
        assert "not a claim that" in text
