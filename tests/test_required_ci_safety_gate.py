from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
CONSTRAINTS = ROOT / "ci" / "constraints.txt"


def test_required_ci_uses_immutable_actions_and_exact_constraints():
    text = CI.read_text(encoding="utf-8")
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/checkout@v4" not in text
    assert "actions/setup-python@v5" not in text
    assert "PIP_CONSTRAINT: ci/constraints.txt" in text
    assert 'pip==24.3.1' in text
    assert "pip install --upgrade pip" not in text

    constraints = CONSTRAINTS.read_text(encoding="utf-8")
    for expected in (
        "setuptools==75.6.0",
        "wheel==0.45.1",
        "defusedxml==0.7.1",
        "numpy==1.26.4",
        "scipy==1.12.0",
        "scikit-learn==1.4.2",
        "joblib==1.4.2",
        "threadpoolctl==3.5.0",
    ):
        assert expected in constraints


def test_required_test_job_contains_real_hc_and_teacher_safety_gates():
    text = CI.read_text(encoding="utf-8")
    assert "- name: Required H-C capacity safety gate" in text
    assert "python scripts/run_s2a_hc_capacity_audit.py" in text
    assert "assert data['final_reservation']['hc_pass_source_count'] == 120" in text
    assert "assert data['scientific_boundary']['real_model_fit_executed'] is False" in text

    assert "- name: Required Teacher Correction safety gate" in text
    assert "python scripts/build_teacher_correction_v1_pilot.py" in text
    assert "assert m['task_count'] == 20" in text
    assert "assert a['untouched_final_sources_used'] == 0" in text
    assert "assert a['training_authorized'] is False" in text


def test_required_test_job_remains_branch_protection_compatible():
    text = CI.read_text(encoding="utf-8")
    assert "jobs:\n  test:" in text
    assert "push:\n    branches: [main]" in text
    assert "pull_request:" in text
