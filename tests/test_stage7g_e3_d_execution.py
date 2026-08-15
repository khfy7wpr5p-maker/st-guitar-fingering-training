import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

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


def test_feature_list_hash_is_frozen():
    assert len(STAGE7G_E3_FEATURE_NAMES) == 40
    assert feature_list_sha256() == STAGE7G_E3_D_EXPECTED_FEATURE_LIST_SHA256


def test_threshold_selection_uses_frozen_tie_break_and_no_switch():
    y = np.asarray([0] * 20 + [1] * 20, dtype=np.int64)
    probabilities = np.asarray([0.1] * 20 + [0.9] * 20, dtype=np.float64)
    threshold, candidates = select_stage7g_e3_d_threshold(y, probabilities)
    assert threshold == 0.9
    assert [row["threshold"] for row in candidates] == [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

    threshold, candidates = select_stage7g_e3_d_threshold(
        y, np.asarray([0.1] * 40, dtype=np.float64)
    )
    assert threshold is None
    assert not any(row["eligible"] for row in candidates)


def test_nested_split_preflight_is_family_isolated_and_deterministic():
    rows = _synthetic_rows()
    report = stage7g_e3_d_split_preflight(rows)
    assert report["status"] == "PREFLIGHT_PASS_STOP_BEFORE_TRAIN"
    assert report["family_isolated"] is True
    assert report["outer_splits"] == 5
    assert report["inner_splits"] == 4
    assert report["outer_random_state"] == 731
    assert report["inner_random_states"] == [7310, 7311, 7312, 7313, 7314]
    assert sum(fold["test_rows"] for fold in report["outer_folds"]) == len(rows)
    assert all(len(fold["inner_folds"]) == 4 for fold in report["outer_folds"])
    assert report == stage7g_e3_d_split_preflight(rows)


def test_nested_cv_is_frozen_positive_synthetic_signal_and_never_promotes_checkpoint():
    report = stage7g_e3_d_nested_cv_report(_synthetic_rows())
    assert report["status"] == "POSITIVE_DEVELOPMENT_SIGNAL_ELIGIBLE_FOR_E3E_DESIGN"
    assert report["scientific_scope"] == "nested_development_cv_not_untouched_validation"
    assert report["model"]["class_weight"] is None
    assert report["model"]["feature_count"] == 40
    assert report["validation"]["outer_splits"] == 5
    assert report["validation"]["inner_splits"] == 4
    assert report["aggregate"]["accuracy_delta_vs_always_open_low"] > 0
    assert report["aggregate"]["compact_true_positive"] > report["aggregate"]["compact_false_positive"]
    assert report["checkpoint_retained"] is False
    assert report["production_integration"] is False
    assert report["stage7e_used"] is False


def test_non_finite_feature_fails_closed():
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
    with pytest.raises(ValueError, match="feature matrix"):
        stage7g_e3_d_split_preflight(rows)


def test_unsealed_zip_is_rejected_before_member_use(tmp_path):
    path = tmp_path / "unsealed.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("audit.json", json.dumps({"schema": "anything"}))
    with pytest.raises(ValueError, match="outer package SHA-256 mismatch"):
        read_stage7g_e3_package_json(path)


def test_colab_template_is_fail_closed_and_separates_train_cell():
    notebook = json.loads(
        Path("notebooks/ST_Guitar_Stage7G_E3_D_R1_Colab.ipynb").read_text(encoding="utf-8")
    )
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
    all_source = "\n".join(sources)
    assert "__PIN_AFTER_R1A_MERGE__" in all_source
    assert "PREFLIGHT_PASS_STOP_BEFORE_TRAIN" in all_source
    train_cells = [source for source in sources if "MANUAL TRAIN CELL" in source]
    assert len(train_cells) == 1
    assert "stage7g_e3_d_nested_cv_report(rows)" in train_cells[0]
    assert "joblib.dump" not in all_source
    assert "pickle.dump" not in all_source
    assert "checkpoint_retained" in all_source
