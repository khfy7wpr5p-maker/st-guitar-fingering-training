from __future__ import annotations

import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from st_guitar_fingering_training.common_tone_rollout import (
    _predict_style_candidate,
    rollout_common_tone_report,
)
from st_guitar_fingering_training.synthetic import family_to_musicxml, generate_synthetic_family
from st_guitar_fingering_training.synthetic_behavior import STYLES
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.transfer_validation import train_frozen_synthetic_specialists


class CommonToneRolloutTests(unittest.TestCase):
    def _parse_family(self, root: Path, family_index: int, *, family_id: str | None = None):
        family = generate_synthetic_family(family_index, events_per_family=6)
        path = root / f"{family.family_id}_{family_index}.xml"
        path.write_text(family_to_musicxml(family), encoding="utf-8")
        source = parse_guitar_musicxml(path, family_id=family_id or family.family_id)
        return family, source

    def _models(self, root: Path):
        groups = {}
        for family_index in (0, 12, 24, 36, 48):
            family, source = self._parse_family(root, family_index)
            groups[family.style] = (source,)
        self.assertEqual(set(groups), set(STYLES))
        return train_frozen_synthetic_specialists(groups)

    def test_rollout_prediction_seam_has_no_observed_target_parameter(self):
        parameters = inspect.signature(_predict_style_candidate).parameters
        self.assertNotIn("observed", parameters)
        self.assertNotIn("target", parameters)
        self.assertEqual(
            tuple(parameters),
            ("model", "style", "candidates", "previous_prediction"),
        )

    def test_common_tone_rollout_uses_system_context_and_retains_no_checkpoint(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            models = self._models(root)
            _, real_source = self._parse_family(root, 61, family_id="real_rollout_fixture")
            report = rollout_common_tone_report((real_source,), models)

        self.assertEqual(report["stage"], "7D-B")
        self.assertEqual(report["status"], "DIAGNOSTIC_PROTOCOL")
        self.assertEqual(report["rollout_previous_context"], "previous_system_prediction")
        self.assertFalse(report["observed_previous_voicing_in_rollout_features"])
        self.assertEqual(report["teacher_forced_context"], "diagnostic_comparator_only")
        self.assertEqual(report["real_training_rows"], 0)
        self.assertFalse(report["real_model_fit"])
        self.assertEqual(report["seed_events"], 1)
        self.assertGreater(report["evaluated_ambiguous_post_seed_events"], 0)
        self.assertGreaterEqual(report["context_divergence_rate"], 0.0)
        self.assertLessEqual(report["context_divergence_rate"], 1.0)
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])

    def test_rollout_requires_both_seed_and_common_tone_specialists(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, real_source = self._parse_family(root, 61, family_id="real_rollout_fixture")
            with self.assertRaisesRegex(ValueError, "open_low and common_tone"):
                rollout_common_tone_report((real_source,), {})


if __name__ == "__main__":
    unittest.main()
