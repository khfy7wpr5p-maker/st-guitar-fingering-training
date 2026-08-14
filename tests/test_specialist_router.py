from __future__ import annotations

import unittest

import numpy as np

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement
from st_guitar_fingering_training.specialist_router import (
    ROUTER_FEATURE_NAMES,
    STATELESS_ROUTER_STYLES,
    RouterRow,
    build_stateless_router_rows,
    stateless_router_cross_validation_report,
)


STANDARD_TUNING = (64, 59, 55, 50, 45, 40)


class _IndexScoreModel:
    def decision_function(self, X):
        return np.arange(len(X), dtype=np.float64)


def _source_with_observed(voicing, family_id="real_family") -> ParsedSource:
    placements = tuple(
        Placement(sounding_midi=pitch, xml_midi=pitch, string=string, fret=fret)
        for pitch, string, fret in voicing
    )
    event = GuitarEvent(
        family_id=family_id,
        source_sha256="a" * 64,
        musicxml_version="4.0",
        software="fixture",
        pitch_mode="sounding_exact",
        tuning=STANDARD_TUNING,
        measure="1",
        onset=0,
        duration=1,
        voice="1",
        placements=placements,
    )
    return ParsedSource(
        family_id=family_id,
        source_sha256="a" * 64,
        musicxml_version="4.0",
        software="fixture",
        pitch_mode="sounding_exact",
        tuning=STANDARD_TUNING,
        selected_staff="2",
        events=(event,),
    )


class SpecialistRouterTests(unittest.TestCase):
    def test_router_features_are_target_blind_and_common_tone_is_excluded(self) -> None:
        pitches = (60, 64, 67)
        candidates = valid_chord_voicings(pitches, STANDARD_TUNING)
        self.assertGreaterEqual(len(candidates), 2)
        models = {style: _IndexScoreModel() for style in STATELESS_ROUTER_STYLES}

        first_rows, first_audit = build_stateless_router_rows(
            (_source_with_observed(candidates[0]),),
            models,
        )
        last_rows, last_audit = build_stateless_router_rows(
            (_source_with_observed(candidates[-1]),),
            models,
        )

        first_by_style = {row.style: row for row in first_rows}
        last_by_style = {row.style: row for row in last_rows}
        self.assertEqual(set(first_by_style), set(STATELESS_ROUTER_STYLES))
        self.assertEqual(set(last_by_style), set(STATELESS_ROUTER_STYLES))
        for style in STATELESS_ROUTER_STYLES:
            self.assertEqual(first_by_style[style].features, last_by_style[style].features)
        self.assertNotEqual(
            [first_by_style[style].success for style in STATELESS_ROUTER_STYLES],
            [last_by_style[style].success for style in STATELESS_ROUTER_STYLES],
        )
        self.assertFalse(first_audit["observed_target_in_features"])
        self.assertFalse(last_audit["common_tone_included"])
        self.assertNotIn("common_tone", STATELESS_ROUTER_STYLES)

    def test_router_cv_is_family_isolated_and_retains_no_checkpoint(self) -> None:
        rows = []
        feature_count = len(ROUTER_FEATURE_NAMES)
        for family_index in range(5):
            family_id = f"family_{family_index}"
            for event_index in range(3):
                event_id = f"{family_id}:event_{event_index}"
                for style_index, style in enumerate(STATELESS_ROUTER_STYLES):
                    success = int(
                        (style == "open_low" and event_index % 2 == 0)
                        or (style == "compact" and event_index % 2 == 1)
                        or (style == "mid_position" and family_index % 2 == 0 and event_index == 2)
                    )
                    features = [0.0] * feature_count
                    features[0] = (event_index + 1) / 3.0
                    features[1] = family_index / 5.0
                    features[11] = style_index / 4.0
                    features[13 + style_index] = 1.0
                    rows.append(RouterRow(
                        family_id=family_id,
                        event_id=event_id,
                        style=style,
                        success=success,
                        features=tuple(features),
                    ))

        report = stateless_router_cross_validation_report(tuple(rows), folds=5)
        self.assertTrue(report["family_isolated"])
        self.assertFalse(report["observed_target_in_features"])
        self.assertFalse(report["common_tone_included"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])
        self.assertEqual(report["fold_count"], 5)
        for fold in report["folds"]:
            self.assertFalse(set(fold["train_families"]) & set(fold["validation_families"]))


if __name__ == "__main__":
    unittest.main()
