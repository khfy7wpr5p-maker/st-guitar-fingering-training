import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_licensing_package_is_complete_and_declared():
    required = (
        "LICENSE", "COMMERCIAL-LICENSE.md", "LICENSE-SCOPE.md",
        "MODEL-LICENSE.md", "DATASET-LICENSES.md", "NOTICE",
        "TRADEMARKS.md", "CONTRIBUTOR-LICENSE-AGREEMENT.md",
        "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md",
        "third_party/dependency-licenses.json",
    )
    assert all((ROOT / path).is_file() for path in required)
    assert "PolyForm Noncommercial License 1.0.0" in read("LICENSE")
    project = tomllib.loads(read("pyproject.toml"))["project"]
    assert project["license"]["file"] == "LICENSE"
    assert "Commercial use requires a separate signed agreement" in read("README.md")


def test_direct_dependencies_have_machine_readable_records():
    project = tomllib.loads(read("pyproject.toml"))["project"]
    inventory = json.loads(read("third_party/dependency-licenses.json"))
    names = {item["name"].lower() for item in inventory["components"]}
    for dependency in project["dependencies"]:
        name = dependency.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0].strip().lower()
        assert name in names
    assert inventory["exactTransitiveLockPresent"] is False


def test_model_and_dataset_authority_is_fail_closed():
    model = read("MODEL-LICENSE.md")
    assert "7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314" in model
    assert "fret20QualityAuthority=false" in model
    assert "automatic learning during active use are not authorized" in model
    datasets = read("DATASET-LICENSES.md")
    assert "10.5281/zenodo.3371780" in datasets
    assert "Excluded from commercial training and production" in datasets
    assert "Excluded pending written rights clearance" in datasets

