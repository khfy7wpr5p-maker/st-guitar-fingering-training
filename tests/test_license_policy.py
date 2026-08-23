import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def normalized(path: str) -> str:
    return " ".join(read(path).split())


class LicensePolicyTests(unittest.TestCase):
    def test_licensing_package_is_complete_and_declared(self):
        required = (
            "LICENSE", "COMMERCIAL-LICENSE.md", "LICENSE-SCOPE.md",
            "MODEL-LICENSE.md", "DATASET-LICENSES.md", "NOTICE",
            "TRADEMARKS.md", "CONTRIBUTOR-LICENSE-AGREEMENT.md",
            "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md",
            "third_party/dependency-licenses.json",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn("PolyForm Noncommercial License 1.0.0", read("LICENSE"))
        project = tomllib.loads(read("pyproject.toml"))["project"]
        self.assertEqual(project["license"]["file"], "LICENSE")
        self.assertIn(
            "Commercial use requires a separate signed agreement",
            normalized("README.md"),
        )

    def test_direct_dependencies_have_machine_readable_records(self):
        project = tomllib.loads(read("pyproject.toml"))["project"]
        inventory = json.loads(read("third_party/dependency-licenses.json"))
        names = {item["name"].lower() for item in inventory["components"]}
        for dependency in project["dependencies"]:
            name = dependency.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0].strip().lower()
            self.assertIn(name, names)
        self.assertIs(inventory["exactTransitiveLockPresent"], False)

    def test_model_and_dataset_authority_is_fail_closed(self):
        model = normalized("MODEL-LICENSE.md")
        self.assertIn("7a56436c27ee6d996a49e7f989d37d7ffff187232277095b176c3c395c432314", model)
        self.assertIn("fret20QualityAuthority=false", model)
        self.assertIn("automatic learning during active use are not authorized", model)
        datasets = normalized("DATASET-LICENSES.md")
        self.assertIn("10.5281/zenodo.3371780", datasets)
        self.assertIn("Excluded from commercial training and production", datasets)
        self.assertIn("Excluded pending written rights clearance", datasets)


if __name__ == "__main__":
    unittest.main()
