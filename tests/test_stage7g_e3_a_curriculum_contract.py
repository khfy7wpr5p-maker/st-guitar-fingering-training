from __future__ import annotations

import unittest

from st_guitar_fingering_training.curriculum_contract import (
    STAGE7G_E3_FEATURE_NAMES,
    STAGE7G_E3_GEOMETRY_NAMES,
    STAGE7G_E3_RULE_PROPERTY_TARGETS,
    Stage7GE3Supervision,
    stage7g_e3_curriculum_level,
    stage7g_e3_proposal_geometry,
    stage7g_e3_rule_property_value,
    validate_stage7g_e3_supervision,
)


def _delta(**updates: float) -> dict[str, float]:
    values = {name: 0.0 for name in STAGE7G_E3_GEOMETRY_NAMES}
    values.update(updates)
    return values


def _geometry(**updates: float) -> dict[str, float]:
    values = {name: 0.0 for name in STAGE7G_E3_GEOMETRY_NAMES}
    values.update(updates)
    return values


class Stage7GE3ACurriculumContractTests(unittest.TestCase):
    def test_e3_feature_contract_is_fixed_and_target_blind(self):
        self.assertEqual(len(STAGE7G_E3_FEATURE_NAMES), 40)
        self.assertEqual(len(set(STAGE7G_E3_FEATURE_NAMES)), 40)
        forbidden = ("teacher", "family", "source", "observed", "stage7e", "target")
        for name in STAGE7G_E3_FEATURE_NAMES:
            self.assertFalse(any(token in name.lower() for token in forbidden))

    def test_e3_geometry_semantics_include_string_topology_and_barre_proxy(self):
        voicing = (
            (64, 1, 0),
            (60, 2, 1),
            (55, 4, 1),
        )
        values = dict(zip(STAGE7G_E3_GEOMETRY_NAMES, stage7g_e3_proposal_geometry(voicing)))
        self.assertEqual(values, {
            "open_note_count": 1.0,
            "fretted_note_count": 2.0,
            "min_positive_fret": 1.0,
            "mean_positive_fret": 1.0,
            "max_fret": 1.0,
            "positive_fret_span": 0.0,
            "unique_positive_frets": 1.0,
            "max_same_positive_fret_count": 2.0,
            "string_span": 3.0,
            "adjacent_string_ratio": 0.5,
            "internal_string_gaps": 1.0,
        })

    def test_e3_curriculum_levels_are_target_blind_and_deterministic(self):
        self.assertEqual(stage7g_e3_curriculum_level(
            chord_size=2,
            candidate_count=10,
            geometry_delta=_delta(open_note_count=1.0, mean_positive_fret=-3.0),
        ), "L1")
        self.assertEqual(stage7g_e3_curriculum_level(
            chord_size=3,
            candidate_count=18,
            geometry_delta=_delta(internal_string_gaps=1.0),
        ), "L2")
        self.assertEqual(stage7g_e3_curriculum_level(
            chord_size=4,
            candidate_count=30,
            geometry_delta=_delta(),
        ), "L3")
        self.assertEqual(stage7g_e3_curriculum_level(
            chord_size=5,
            candidate_count=12,
            geometry_delta=_delta(open_note_count=2.0, mean_positive_fret=-5.0),
        ), "L4")

    def test_e3_rule_derived_supervision_cannot_masquerade_as_teacher_gold(self):
        validate_stage7g_e3_supervision(Stage7GE3Supervision(
            curriculum_level="L1",
            provenance="RULE_DERIVED_PROPERTY",
            target_name="lower_mean_positive_fret",
            target_value="COMPACT",
            annotation_blinded=False,
        ))

        with self.assertRaisesRegex(ValueError, "unknown Stage 7G-E3 rule-derived property target"):
            validate_stage7g_e3_supervision(Stage7GE3Supervision(
                curriculum_level="L2",
                provenance="RULE_DERIVED_PROPERTY",
                target_name="pairwise_guitaristic_preference",
                target_value="COMPACT",
                annotation_blinded=False,
            ))

        with self.assertRaisesRegex(ValueError, "limited to L1/L2"):
            validate_stage7g_e3_supervision(Stage7GE3Supervision(
                curriculum_level="L3",
                provenance="RULE_DERIVED_PROPERTY",
                target_name="lower_mean_positive_fret",
                target_value="COMPACT",
                annotation_blinded=False,
            ))

        with self.assertRaisesRegex(ValueError, "Teacher-GOLD must be blinded"):
            validate_stage7g_e3_supervision(Stage7GE3Supervision(
                curriculum_level="L3",
                provenance="TEACHER_GOLD",
                target_name="pairwise_guitaristic_preference",
                target_value="COMPACT",
                annotation_blinded=False,
            ))

    def test_e3_teacher_gold_accepts_equal_or_unsure_without_coercion(self):
        validate_stage7g_e3_supervision(Stage7GE3Supervision(
            curriculum_level="L4",
            provenance="TEACHER_GOLD",
            target_name="pairwise_guitaristic_preference",
            target_value="EQUAL_OR_UNSURE",
            annotation_blinded=True,
        ))

    def test_e3_rule_property_targets_are_descriptive_not_preference_labels(self):
        open_geometry = _geometry(
            open_note_count=0.0,
            fretted_note_count=2.0,
            mean_positive_fret=7.0,
            positive_fret_span=4.0,
            string_span=4.0,
            internal_string_gaps=2.0,
        )
        compact_geometry = _geometry(
            open_note_count=1.0,
            fretted_note_count=1.0,
            mean_positive_fret=3.0,
            positive_fret_span=1.0,
            string_span=2.0,
            internal_string_gaps=0.0,
        )
        for property_name in STAGE7G_E3_RULE_PROPERTY_TARGETS:
            with self.subTest(property_name=property_name):
                self.assertEqual(stage7g_e3_rule_property_value(
                    property_name,
                    open_geometry,
                    compact_geometry,
                ), "COMPACT")

    def test_e3_contract_rejects_nonfinite_and_bad_dimensions(self):
        with self.assertRaisesRegex(ValueError, "geometry delta keys"):
            stage7g_e3_curriculum_level(
                chord_size=2,
                candidate_count=4,
                geometry_delta={"mean_positive_fret": 3.0},
            )
        with self.assertRaisesRegex(ValueError, "must be finite"):
            stage7g_e3_curriculum_level(
                chord_size=2,
                candidate_count=4,
                geometry_delta=_delta(mean_positive_fret=float("inf")),
            )


if __name__ == "__main__":
    unittest.main()
