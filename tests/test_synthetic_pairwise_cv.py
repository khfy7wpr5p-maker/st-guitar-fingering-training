from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.synthetic import family_to_musicxml, generate_synthetic_family
from st_guitar_fingering_training.synthetic_pairwise import pairwise_behavior_cross_validation_report


class SyntheticPairwiseCvTests(unittest.TestCase):
    def test_pairwise_cv_is_family_isolated_and_does_not_retain_checkpoint(self):
        families = [generate_synthetic_family(index, events_per_family=4) for index in range(12, 17)]
        self.assertTrue(all(family.style == "compact" for family in families))

        sources = []
        with TemporaryDirectory() as td:
            root = Path(td)
            for family in families:
                path = root / f"{family.family_id}.xml"
                path.write_text(family_to_musicxml(family), encoding="utf-8")
                sources.append(parse_guitar_musicxml(path, family_id=family.family_id))

        report = pairwise_behavior_cross_validation_report(tuple(sources), "compact", folds=5)
        self.assertEqual(report["model_kind"], "pairwise_logistic_ranking_specialist")
        self.assertEqual(report["family_count"], 5)
        self.assertEqual(report["fold_count"], 5)
        self.assertTrue(report["family_isolated"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertEqual(report["previous_context"], "none")

        for fold in report["folds"]:
            train = set(fold["train_families"])
            validation = set(fold["validation_families"])
            self.assertFalse(train & validation)
            self.assertEqual(fold["train_family_count"], 4)
            self.assertEqual(fold["validation_family_count"], 1)
            self.assertGreater(fold["validation_events"], 0)


if __name__ == "__main__":
    unittest.main()
