import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from st_guitar_fingering_training.guitarset_voicing_numerical_hardening_v2 import (
    EXPECTED_BASE_MAIN_SHA,
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_MODEL_ARTIFACT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    EXPECTED_SOURCE_ARCHIVE_SHA256,
    _canonical_sha256,
    load_authorized_request,
    logistic_objective_gradient,
    reconstruct_lbfgs,
)


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "evidence" / "stage7g_e4_guitarset_observed_voicing_numerical_hardening_request_v2.json"


def symmetric_surface():
    positive = np.asarray(
        [
            [2.0, 0.5, -0.5],
            [1.0, 1.5, 0.25],
            [0.5, -1.0, 2.0],
            [1.5, 0.25, 1.0],
        ],
        dtype=np.float64,
    )
    X = np.vstack([positive, -positive])
    y = np.asarray([1] * len(positive) + [0] * len(positive), dtype=np.int8)
    return X, y


class GuitarSetV2NumericalHardeningTests(unittest.TestCase):
    def test_objective_gradient_matches_independent_central_difference(self):
        X, y = symmetric_surface()
        X_scaled = StandardScaler().fit_transform(X)
        coefficients = np.asarray([0.2, -0.3, 0.4], dtype=np.float64)
        _, gradient = logistic_objective_gradient(X_scaled, y, coefficients)
        epsilon = 1e-6
        finite_difference = []
        for index in range(len(coefficients)):
            plus = coefficients.copy()
            minus = coefficients.copy()
            plus[index] += epsilon
            minus[index] -= epsilon
            plus_objective = logistic_objective_gradient(X_scaled, y, plus)[0]
            minus_objective = logistic_objective_gradient(X_scaled, y, minus)[0]
            finite_difference.append((plus_objective - minus_objective) / (2 * epsilon))
        np.testing.assert_allclose(gradient, finite_difference, rtol=1e-7, atol=1e-9)

    def test_reconstruction_matches_the_frozen_sklearn_pipeline_contract(self):
        X, y = symmetric_surface()
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                fit_intercept=False,
                class_weight=None,
                solver="lbfgs",
                max_iter=2000,
                random_state=0,
            ),
        ).fit(X, y)
        X_scaled = model.named_steps["standardscaler"].transform(X)
        sealed = model.named_steps["logisticregression"].coef_[0]
        evidence = reconstruct_lbfgs(X_scaled, y, sealed)
        self.assertTrue(evidence["optimizer_success"])
        self.assertEqual(evidence["optimizer_status"], 0)
        self.assertTrue(evidence["accepted_objective_trace_non_increasing"])
        self.assertTrue(evidence["coefficient_delta_within_limit"])
        self.assertTrue(evidence["training_score_delta_within_limit"])
        self.assertLess(evidence["final_objective"], evidence["initial_objective"])

    def test_fail_closed_input_validation_rejects_bad_surfaces(self):
        X, y = symmetric_surface()
        with self.assertRaises(ValueError):
            logistic_objective_gradient(X, np.zeros(len(y)), np.zeros(X.shape[1]))
        contaminated = X.copy()
        contaminated[0, 0] = np.nan
        with self.assertRaises(ValueError):
            logistic_objective_gradient(contaminated, y, np.zeros(X.shape[1]))
        with self.assertRaises(ValueError):
            logistic_objective_gradient(X[:, :2], y, np.zeros(3))

    def test_request_authorizes_only_development_diagnostics(self):
        request = load_authorized_request(REQUEST)
        self.assertEqual(request["base_training_main_sha"], EXPECTED_BASE_MAIN_SHA)
        self.assertEqual(request["retained_model_artifact_sha256"], EXPECTED_MODEL_ARTIFACT_SHA256)
        self.assertEqual(request["feature_schema_sha256"], EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(request["protocol_sha256"], EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(request["source_archive_sha256"], EXPECTED_SOURCE_ARCHIVE_SHA256)
        self.assertEqual(request["allowed_data_role"], "DEVELOPMENT_ONLY")
        self.assertTrue(request["diagnostic_reconstruction_authorized"])
        for field in (
            "checkpoint_replacement_authorized",
            "model_mutation_authorized",
            "validation_access_authorized",
            "final_access_authorized",
            "runtime_connection_authorized",
            "production_authorized",
        ):
            self.assertFalse(request[field], field)


if __name__ == "__main__":
    unittest.main()
