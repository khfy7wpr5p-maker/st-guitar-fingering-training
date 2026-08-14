from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement, parse_guitar_musicxml
from st_guitar_fingering_training.synthetic import STANDARD_TUNING, family_to_musicxml, generate_synthetic_family
from st_guitar_fingering_training.synthetic_behavior import STYLES
from st_guitar_fingering_training.transfer_validation import (
    build_real_transfer_rows,
    real_transfer_report,
    train_frozen_synthetic_specialists,
)


class TransferValidationTests(unittest.TestCase):
    def _parse_family(self, root: Path, family_index: int, *, family_id: str | None = None):
        family = generate_synthetic_family(family_index, events_per_family=4)
        path = root / f"{family.family_id}.xml"
        path.write_text(family_to_musicxml(family), encoding="utf-8")
        return family, parse_guitar_musicxml(path, family_id=family_id or family.family_id)

    def _synthetic_training_groups(self, root: Path):
        groups = {}
        for family_index in (0, 12, 24, 36, 48):
            family, source = self._parse_family(root, family_index)
            groups[family.style] = (source,)
        self.assertEqual(set(groups), set(STYLES))
        return groups

    def test_transfer_report_never_fits_real_data_and_keeps_domains_disjoint(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            synthetic_groups = self._synthetic_training_groups(root)
            _, real_a = self._parse_family(root, 60, family_id="real_fixture_a")
            _, real_b = self._parse_family(root, 61, family_id="real_fixture_b")

            models = train_frozen_synthetic_specialists(synthetic_groups)
            report = real_transfer_report(models, synthetic_groups, (real_a, real_b))

        self.assertEqual(report["status"], "DIAGNOSTIC")
        self.assertTrue(report["domain_disjoint"])
        self.assertEqual(report["real_training_rows"], 0)
        self.assertFalse(report["real_model_fit"])
        self.assertEqual(report["real_label_semantics"], "observed_behavior_not_teacher_gold")
        self.assertEqual(report["real_evaluation_families"], 2)
        self.assertEqual(set(report["specialists"]), set(STYLES))
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])
        self.assertEqual(
            report["specialists"]["common_tone"]["previous_context"],
            "observed_previous_real_voicing_diagnostic",
        )
        coverage = report["specialist_coverage"]["top1_coverage"]
        self.assertGreaterEqual(coverage, 0.0)
        self.assertLessEqual(coverage, 1.0)
        self.assertEqual(
            report["specialist_coverage"]["meaning"],
            "oracle_like_diagnostic_not_deployment_policy",
        )

    def test_transfer_rejects_synthetic_real_source_overlap(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            synthetic_groups = self._synthetic_training_groups(root)
            models = train_frozen_synthetic_specialists(synthetic_groups)
            overlapping_source = synthetic_groups["open_low"][0]
            with self.assertRaisesRegex(ValueError, "overlap"):
                real_transfer_report(models, synthetic_groups, (overlapping_source,))

    def test_real_candidate_set_is_not_truncated_at_synthetic_fret_12(self):
        placements = (
            Placement(sounding_midi=64, xml_midi=64, string=2, fret=5),
            Placement(sounding_midi=77, xml_midi=77, string=1, fret=13),
        )
        event = GuitarEvent(
            family_id="real_high_fret",
            source_sha256="a" * 64,
            musicxml_version="3.1",
            software="fixture",
            pitch_mode="sounding_exact",
            tuning=STANDARD_TUNING,
            measure="1",
            onset=0,
            duration=1,
            voice="1",
            placements=placements,
        )
        source = ParsedSource(
            family_id="real_high_fret",
            source_sha256="a" * 64,
            musicxml_version="3.1",
            software="fixture",
            pitch_mode="sounding_exact",
            tuning=STANDARD_TUNING,
            selected_staff="1",
            events=(event,),
        )

        rows, audit = build_real_transfer_rows((source,), "compact")
        expected_candidates = valid_chord_voicings((64, 77), STANDARD_TUNING)

        self.assertEqual(len(rows), len(expected_candidates))
        self.assertGreater(len(rows), 1)
        self.assertEqual(audit["observed_above_synthetic_training_fret_events"], 1)
        self.assertEqual(audit["candidate_set_above_synthetic_training_fret_events"], 1)
        self.assertTrue(audit["real_candidate_fret_range_retained"])
        self.assertEqual(sum(row.observed for row in rows), 1)


if __name__ == "__main__":
    unittest.main()
