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
    "929264a1778b061ff21464da41ecacbcd952a3cd",
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
)

STALE_LIVE_CLAIMS = (
    "Current `main` baseline after merged PR #93",
    "Current live baseline after merged PR #93",
    "Current main baseline after merged PR #93",
    "Architecture synchronization base (PR #93 merge)",
    "PR #90 remains open",
    "PR #90 OPEN",
    "GuitarSet real model fit: ⛔ not executed",
    "OBSERVED_VOICING_MODEL_DEVELOPMENT_IMPLEMENTATION_AND_FIT",
    "development implementation + fit                     ⏳ NEXT GATE",
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_all_live_documents_share_the_v2_identity_and_closed_authority_boundary():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        for marker in COMMON_REQUIRED:
            assert marker in text, f"{relative_path} missing {marker}"


def test_stale_v1_era_live_claims_cannot_return():
    for relative_path in LIVE_DOCS:
        text = read(relative_path)
        for stale_claim in STALE_LIVE_CLAIMS:
            assert stale_claim not in text, f"{relative_path} contains stale claim: {stale_claim}"


def test_live_status_distinguishes_untrained_s2a_from_trained_guitarset_v2():
    status = read("STATUS.md")
    assert "S2-A Teacher naturalness" in status and "no real fit" in status
    assert "Development, validation, final, retention, and integration review complete" in status
    assert "PR #90" in status and "Closed without merge" in status


def test_live_documents_do_not_overclaim_numerical_convergence():
    for relative_path in ("README.md", "ARCHITECTURE.md", "STATUS.md", "SAFETY.md"):
        text = read(relative_path)
        assert "gradient" in text.lower() or "numerical-convergence" in text.lower()
        assert "n_iter=37" in text
