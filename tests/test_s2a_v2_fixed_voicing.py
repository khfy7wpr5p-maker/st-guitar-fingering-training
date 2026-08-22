from __future__ import annotations

import unittest

import numpy as np

from st_guitar_fingering_training.s2a_v2_fixed_voicing import (
    BUCKET_DEVELOPMENT,
    BUCKET_FINAL,
    DECISION_SELECT,
    S2A_V2_AUDIT_SCHEMA,
    S2A_V2_EXPORT_SCHEMA,
    S2A_V2_PROTOCOL_VERSION,
    assignments_for_fixed_voicing,
    build_fixed_voicing_task,
    build_single_session_manifest,
    reliability_report,
    validate_choice_export,
)
from st_guitar_fingering_training.s2a_v2_ranker import (
    PreferenceConstraint,
    build_training_matrix,
    mechanical_complexity_key,
)
from st_guitar_fingering_training.s2a_features import assignment_feature_vector


E_MINOR = (
    (40, 6, 0),
    (47, 5, 2),
    (52, 4, 2),
    (55, 3, 0),
)


class S2AV2FixedVoicingTests(unittest.TestCase):
    def _task(self, nonce: str, bucket: str = BUCKET_DEVELOPMENT):
        return build_fixed_voicing_task(
            event_id="e-minor-regression",
            fixed_voicing=E_MINOR,
            export_bucket=bucket,
            presentation_nonce=nonce,
        )

    def test_hc_v2_keeps_separate_finger_e_minor(self):
        assignments = assignments_for_fixed_voicing(E_MINOR)
        expected = {
            (6, 0, 0),
            (5, 2, 2),
            (4, 2, 3),
            (3, 0, 0),
        }
        found = False
        for assignment in assignments:
            triplets = {(string, fret, finger) for _, string, fret, finger in assignment.placements}
            if triplets == expected:
                self.assertEqual(assignment.barres, ())
                found = True
                break
        self.assertTrue(found, "ordinary separate-finger E-minor assignment missing from H-C.v2")

    def test_task_is_fixed_voicing_multiway_without_manual_fields(self):
        task = self._task("ORIGINAL")
        self.assertGreaterEqual(task["assignment_count"], 2)
        self.assertEqual(task["assignment_count"], len(task["options"]))
        fixed = {(row["pitch_midi"], row["string"], row["fret"]) for row in task["fixed_voicing"]}
        self.assertEqual(fixed, set(E_MINOR))
        for option in task["options"]:
            restored = {(row["pitch_midi"], row["string"], row["fret"]) for row in option["placements"]}
            self.assertEqual(restored, set(E_MINOR))
        self.assertNotIn("manual_entry_format", task)

    def test_development_and_final_exports_are_strictly_separate(self):
        dev = self._task("DEV")
        final = self._task("FINAL", BUCKET_FINAL)
        manifest = build_single_session_manifest(batch_id="b", session_id="s", tasks=(dev, final))
        selected = dev["options"][0]["assignment_id"]
        dev_export = {
            "schema": S2A_V2_EXPORT_SCHEMA,
            "protocol_version": S2A_V2_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": manifest["annotator_id"],
            "export_bucket": BUCKET_DEVELOPMENT,
            "decisions": [{
                "task_id": dev["task_id"],
                "semantic_fingerprint": dev["semantic_fingerprint"],
                "decision": DECISION_SELECT,
                "selected_assignment_id": selected,
            }],
        }
        decoded = validate_choice_export(dev_export, manifest, expected_bucket=BUCKET_DEVELOPMENT)
        self.assertEqual(set(decoded), {dev["task_id"]})
        with self.assertRaises(ValueError):
            validate_choice_export(dev_export, manifest, expected_bucket=BUCKET_FINAL)

    def test_out_of_set_assignment_fails_closed(self):
        task = self._task("DEV")
        final = self._task("FINAL", BUCKET_FINAL)
        manifest = build_single_session_manifest(batch_id="b", session_id="s", tasks=(task, final))
        payload = {
            "schema": S2A_V2_EXPORT_SCHEMA,
            "protocol_version": S2A_V2_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": manifest["annotator_id"],
            "export_bucket": BUCKET_DEVELOPMENT,
            "decisions": [{
                "task_id": task["task_id"],
                "semantic_fingerprint": task["semantic_fingerprint"],
                "decision": DECISION_SELECT,
                "selected_assignment_id": "fingering-sha256:not-real",
            }],
        }
        with self.assertRaises(ValueError):
            validate_choice_export(payload, manifest, expected_bucket=BUCKET_DEVELOPMENT)

    def test_hidden_repeat_reliability_compares_exact_assignment(self):
        original = self._task("ORIGINAL")
        repeat = self._task("HIDDEN_REPEAT")
        final = self._task("FINAL", BUCKET_FINAL)
        manifest = build_single_session_manifest(batch_id="b", session_id="s", tasks=(original, repeat, final))
        selected = original["options"][0]["assignment_id"]
        export = {
            "schema": S2A_V2_EXPORT_SCHEMA,
            "protocol_version": S2A_V2_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": manifest["annotator_id"],
            "export_bucket": BUCKET_DEVELOPMENT,
            "decisions": [
                {
                    "task_id": task["task_id"],
                    "semantic_fingerprint": task["semantic_fingerprint"],
                    "decision": DECISION_SELECT,
                    "selected_assignment_id": selected,
                }
                for task in (original, repeat)
            ],
        }
        audit = {
            "schema": S2A_V2_AUDIT_SCHEMA,
            "rows": [
                {"task_id": original["task_id"], "role": "DEVELOPMENT_ORIGINAL", "family_id": "f1"},
                {"task_id": repeat["task_id"], "role": "RELIABILITY_REPEAT", "family_id": "f1"},
                {"task_id": final["task_id"], "role": "UNTOUCHED_FINAL", "family_id": "f2"},
            ],
            "repeat_pairs": [{
                "original_task_id": original["task_id"],
                "repeat_task_id": repeat["task_id"],
            }],
        }
        report = reliability_report(export, manifest, audit, minimum_repeat_pairs=1)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["exact_assignment_or_class_agreement"], 1.0)
        self.assertFalse(report["repeat_rows_trainable"])

    def test_multiway_selection_creates_mirrored_pair_constraints(self):
        assignments = assignments_for_fixed_voicing(E_MINOR)
        preferred, other = assignments[:2]
        constraint = PreferenceConstraint(
            family_id="f1",
            task_id="t1",
            preferred_assignment_id=preferred.assignment_id,
            other_assignment_id=other.assignment_id,
            preferred_features=assignment_feature_vector(preferred),
            other_features=assignment_feature_vector(other),
        )
        X, y = build_training_matrix((constraint,))
        self.assertEqual(X.shape, (2, 30))
        self.assertTrue(np.array_equal(X[0], -X[1]))
        self.assertEqual(y.tolist(), [1, 0])
        self.assertIsInstance(mechanical_complexity_key(preferred), tuple)


if __name__ == "__main__":
    unittest.main()
