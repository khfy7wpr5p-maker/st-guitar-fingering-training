from __future__ import annotations

import unittest

from st_guitar_fingering_training.teacher_pairwise_router import (
    TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES,
    TeacherPairwiseRouterRow,
    teacher_pairwise_router_cross_validation_report,
    teacher_pairwise_router_feature_vector,
    train_teacher_pairwise_router,
)


TUNING = (64, 59, 55, 50, 45, 40)
OPEN = ((55, 3, 0), (60, 2, 1))
COMPACT = ((55, 4, 5), (60, 3, 5))


class TeacherPairwiseRouterTests(unittest.TestCase):
    def test_feature_vector_is_fixed_target_blind_and_physical(self) -> None:
        features = teacher_pairwise_router_feature_vector(
            (55, 60),
            TUNING,
            OPEN,
            COMPACT,
        )
        self.assertEqual(len(features), len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES))
        self.assertEqual(len(features), 15)
        self.assertTrue(all(isinstance(value, float) for value in features))

        with self.assertRaisesRegex(ValueError, "disagreement"):
            teacher_pairwise_router_feature_vector((55, 60), TUNING, OPEN, OPEN)

    def test_training_rejects_non_decisive_targets(self) -> None:
        features = (0.0,) * len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES)
        rows = (
            TeacherPairwiseRouterRow("f1", "e1", 0, features),
            TeacherPairwiseRouterRow("f1", "e2", 2, features),
        )
        with self.assertRaisesRegex(ValueError, "binary and decisive"):
            train_teacher_pairwise_router(rows)

    def test_family_isolated_cv_is_exhaustive_and_keeps_boundaries_closed(self) -> None:
        rows = []
        feature_count = len(TEACHER_PAIRWISE_ROUTER_FEATURE_NAMES)
        for family_index in range(10):
            family_id = f"family-{family_index:02d}"
            for event_index, target in enumerate((0, 1, 0, 1)):
                values = [0.0] * feature_count
                values[0] = float(target)
                values[1] = family_index / 10.0
                rows.append(TeacherPairwiseRouterRow(
                    family_id=family_id,
                    event_id=f"{family_id}-event-{event_index}",
                    teacher_prefers_compact=target,
                    features=tuple(values),
                ))

        report = teacher_pairwise_router_cross_validation_report(tuple(rows), folds=5)
        self.assertEqual(report["stage"], "7G-E1")
        self.assertEqual(report["family_count"], 10)
        self.assertEqual(report["event_count"], 40)
        self.assertTrue(report["family_isolated"])
        self.assertFalse(report["target_in_features"])
        self.assertFalse(report["hyperparameter_search"])
        self.assertFalse(report["checkpoint_retained"])
        self.assertFalse(report["production_integration"])

        seen_validation = set()
        for fold in report["folds"]:
            train = set(fold["train_families"])
            validation = set(fold["validation_families"])
            self.assertFalse(train & validation)
            self.assertEqual(fold["train_family_count"], 8)
            self.assertEqual(fold["validation_family_count"], 2)
            seen_validation |= validation
        self.assertEqual(seen_validation, {f"family-{index:02d}" for index in range(10)})


if __name__ == "__main__":
    unittest.main()
