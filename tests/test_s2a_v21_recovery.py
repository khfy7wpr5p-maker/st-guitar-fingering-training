from __future__ import annotations

import unittest

from st_guitar_fingering_training.s2a_v21_recovery import (
    V21_EXPANDED_DIM,
    quadratic_feature_vector,
    unstable_repeat_semantics,
)
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
)


E_MINOR = (
    (40, 6, 0),
    (47, 5, 2),
    (52, 4, 2),
    (55, 3, 0),
)


class S2AV21RecoveryTests(unittest.TestCase):
    def test_quadratic_feature_map_is_frozen_495d(self):
        assignment = assignments_for_fixed_voicing(E_MINOR)[0]
        first = quadratic_feature_vector(assignment)
        second = quadratic_feature_vector(assignment)
        self.assertEqual(len(first), V21_EXPANDED_DIM)
        self.assertEqual(first, second)

    def test_repeat_disagreement_is_excluded_by_semantic_identity(self):
        original = build_fixed_voicing_task(
            event_id="v21-regression",
            fixed_voicing=E_MINOR,
            export_bucket=BUCKET_DEVELOPMENT,
            presentation_nonce="ORIGINAL",
        )
        repeats = [
            build_fixed_voicing_task(
                event_id="v21-regression",
                fixed_voicing=E_MINOR,
                export_bucket=BUCKET_DEVELOPMENT,
                presentation_nonce=f"REPEAT-{index}",
            )
            for index in range(30)
        ]
        final = build_fixed_voicing_task(
            event_id="v21-final",
            fixed_voicing=E_MINOR,
            export_bucket=BUCKET_FINAL,
            presentation_nonce="FINAL",
        )
        manifest = build_single_session_manifest(
            batch_id="b",
            session_id="s",
            tasks=(original, *repeats, final),
        )
        options = [row["assignment_id"] for row in original["options"]]
        self.assertGreaterEqual(len(options), 2)
        decisions = [{
            "task_id": original["task_id"],
            "semantic_fingerprint": original["semantic_fingerprint"],
            "decision": DECISION_SELECT,
            "selected_assignment_id": options[0],
        }]
        for index, repeat in enumerate(repeats):
            decisions.append({
                "task_id": repeat["task_id"],
                "semantic_fingerprint": repeat["semantic_fingerprint"],
                "decision": DECISION_SELECT,
                "selected_assignment_id": options[1] if index == 0 else options[0],
            })
        export = {
            "schema": S2A_V2_EXPORT_SCHEMA,
            "protocol_version": S2A_V2_PROTOCOL_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": manifest["annotator_id"],
            "export_bucket": BUCKET_DEVELOPMENT,
            "decisions": decisions,
        }
        audit = {
            "schema": S2A_V2_AUDIT_SCHEMA,
            "rows": [],
            "repeat_pairs": [
                {
                    "original_task_id": original["task_id"],
                    "repeat_task_id": repeat["task_id"],
                }
                for repeat in repeats
            ],
        }
        unstable = unstable_repeat_semantics(manifest, audit, export)
        self.assertEqual(unstable, (original["semantic_fingerprint"],))


if __name__ == "__main__":
    unittest.main()
