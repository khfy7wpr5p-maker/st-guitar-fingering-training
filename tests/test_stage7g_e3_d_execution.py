import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np

from st_guitar_fingering_training.curriculum_contract import STAGE7G_E3_FEATURE_NAMES
from st_guitar_fingering_training.stage7g_e3_d_execution import (
    STAGE7G_E3_D_EXPECTED_FEATURE_LIST_SHA256,
    Stage7GE3DRow,
    feature_list_sha256,
    read_stage7g_e3_package_json,
    select_stage7g_e3_d_threshold,
    stage7g_e3_d_nested_cv_report,
    stage7g_e3_d_split_preflight,
)


def _synthetic_rows():
    rows = []
    levels = ("L1", "L2", "L3", "L4")
    for family_index in range(40):
        for local_index, target in enumerate((0, 0, 1, 1)):
            features = [0.0] * len(STAGE7G_E3_FEATURE_NAMES)
            features[0] = float(target * 10)
            features[1] = float(family_index) / 100.0
            rows.append(Stage7GE3DRow(
                family_id=f"family_{family_index:02d}",
                event_id=f"family_{family_index:02d}:event_{local_index}",
                curriculum_level=levels[local_index],
                teacher_prefers_compact=target,
                features=tuple(features),
            ))
    return tuple(rows)


class Stage7GE3DExecutionTests(unittest.TestCase):
    def test_feature_list_hash_is_frozen(self):
        self.assertEqual(len(STAGE7G_E3_FEATURE_NAMES), 40)
        self.assertEqual(
            feature_list_sha256(),
            STAGE7G_E3_D_EXPECTED_FEATURE_LIST_SHA256,
        )

    def test_threshold_selection_uses_frozen_tie_break_and_no_switch(self):
        y = np.asarray([0] * 20 + [1] * 20, dtype=np.int64)
        probabilities = np.asarray([0.1] * 20 + [0.9] * 20, dtype=np.float64)
        threshold, candidates = select_stage7g_e3_d_threshold(y, probabilities)
        self.assertEqual(threshold, 0.9)
        self.assertEqual(
            [row["threshold"] for row in candidates],
            [0.5, 0.6, 0.7, 0.8, 0.9, 0.95],
        )

        threshold, candidates = select_stage7g_e3_d_threshold(
            y,
            np.asarray([0.1] * 40, dtype=np.float64),
        )
        self.assertIsNone(threshold)
        self.assertFalse(any(row["eligible"] for row in candidates))

    def test_nested_split_preflight_is_family_isolated_and_deterministic(self):
        rows = _synthetic_rows()
        report = stage7g_e3_d_split_preflight(rows)
        self.assertEqual(report["status"], "PREFLIGHT_PASS_STOP_BEFORE_TRAIN")
        self.assertIs(report["family_isolated"], True)
        self.assertEqual(report["outer_splits"], 5)
        self.assertEqual(report["inner_splits"], 4)
        self.assertEqual(report["outer_random_state"], 731)
        self.assertEqual(report["inner_random_states"], [7310, 7311, 7312, 7313, 7314])
        self.assertEqual(
            sum(fold["test_rows"] for fold in report["outer_folds"]),
            len(rows),
        )
        self.assertTrue(all(len(fold["inner_folds"]) == 4 for fold in report["outer_folds"]))
        self.assertEqual(report, stage7g_e3_d_split_preflight(rows))

    def test_nested_cv_is_frozen_positive_synthetic_signal_and_never_promotes_checkpoint(self):
        report = stage7g_e3_d_nested_cv_report(_synthetic_rows())
        self.assertEqual(
            report["status"],
            "POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN",
        )
        self.assertEqual(
            report["scientific_scope"],
            "nested_development_cv_not_untouched_validation",
        )
        self.assertIsNone(report["model"]["class_weight"])
        self.assertEqual(report["model"]["feature_count"], 40)
        self.assertEqual(report["validation"]["outer_splits"], 5)
        self.assertEqual(report["validation"]["inner_splits"], 4)
        self.assertGreater(report["aggregate"]["accuracy_delta_vs_always_open_low"], 0)
        self.assertGreater(
            report["aggregate"]["compact_true_positive"],
            report["aggregate"]["compact_false_positive"],
        )
        self.assertIs(report["checkpoint_retained"], False)
        self.assertIs(report["production_integration"], False)
        self.assertIs(report["stage7e_used"], False)

    def test_non_finite_feature_fails_closed(self):
        rows = list(_synthetic_rows())
        broken = list(rows[0].features)
        broken[3] = float("inf")
        rows[0] = Stage7GE3DRow(
            rows[0].family_id,
            rows[0].event_id,
            rows[0].curriculum_level,
            rows[0].teacher_prefers_compact,
            tuple(broken),
        )
        with self.assertRaisesRegex(ValueError, "feature matrix"):
            stage7g_e3_d_split_preflight(rows)

    def test_unsealed_zip_is_rejected_before_member_use(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "unsealed.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("audit.json", json.dumps({"schema": "anything"}))
            with self.assertRaisesRegex(ValueError, "outer package SHA-256 mismatch"):
                read_stage7g_e3_package_json(path)

    def test_colab_template_is_fail_closed_and_separates_train_cell(self):
        notebook = json.loads(
            Path("notebooks/ST_Guitar_Stage7G_E3_D_R1_Colab.ipynb").read_text(
                encoding="utf-8"
            )
        )
        sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
        all_source = "\n".join(sources)
        self.assertIn("__PIN_AFTER_R1A_MERGE__", all_source)
        self.assertIn("PREFLIGHT_PASS_STOP_BEFORE_TRAIN", all_source)
        train_cells = [
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
            and "MANUAL TRAIN CELL" in "".join(cell.get("source", []))
        ]
        self.assertEqual(len(train_cells), 1)
        self.assertIn("stage7g_e3_d_nested_cv_report(rows)", train_cells[0])
        self.assertNotIn("joblib.dump", all_source)
        self.assertNotIn("pickle.dump", all_source)
        self.assertIn("checkpoint_retained", all_source)


if __name__ == "__main__":
    unittest.main()
