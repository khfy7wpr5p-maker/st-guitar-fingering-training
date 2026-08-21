from __future__ import annotations

import copy
import json
import unittest

from st_guitar_fingering_training.guitarset_split import parse_comp_member_identity
from st_guitar_fingering_training.guitarset_teacher_voicing import (
    DECISION_EQUAL_OR_UNSURE,
    DECISION_MANUAL_VOICING,
    DECISION_SELECT_OPTION,
    TEACHER_VOICING_EXPORT_SCHEMA,
    TEACHER_VOICING_PILOT_VERSION,
    build_teacher_voicing_manifest,
    build_teacher_voicing_task,
    candidate_id,
    development_members_from_archive_metadata,
    parse_manual_voicing,
    render_teacher_voicing_html,
    validate_teacher_voicing_export,
)
from st_guitar_fingering_training.guitarset_voicing_prereg import GUITARSET_SOURCE_ARCHIVE_SHA256


E_MINOR_PITCHES = (40, 47, 52, 55)
E_MINOR_OBSERVED = ((40, 6, 0), (47, 5, 2), (52, 4, 2), (55, 3, 0))


def _task(event_id: str = "event-1"):
    return build_teacher_voicing_task(
        event_id=event_id,
        pitches_midi=E_MINOR_PITCHES,
        observed_placements=E_MINOR_OBSERVED,
        option_cap=6,
    )


def _manifest():
    task, _ = _task()
    return build_teacher_voicing_manifest(
        batch_id="TVPV1_TEST",
        session_id="TVPV1_TEST",
        tasks=[task],
    )


class GuitarSetTeacherVoicingTests(unittest.TestCase):
    def test_task_is_deterministic_blinded_and_contains_observed_as_unlabeled_option(self):
        task1, audit1 = _task()
        task2, audit2 = _task()
        self.assertEqual(task1, task2)
        self.assertEqual(audit1, audit2)
        self.assertTrue(task1["observed_answer_withheld"])
        self.assertTrue(task1["source_identity_withheld"])
        self.assertTrue(task1["model_scores_withheld"])
        self.assertNotIn("observed_candidate_id", task1)
        self.assertNotIn("observed_placements", task1)
        shown = {row["candidate_id"] for row in task1["options"]}
        self.assertIn(audit1["observed_candidate_id"], shown)
        self.assertEqual(audit1["observed_candidate_id"], candidate_id(E_MINOR_OBSERVED))

    def test_manifest_is_diagnostic_only_and_closes_all_consequential_gates(self):
        manifest = _manifest()
        self.assertTrue(manifest["annotation_blinded"])
        self.assertTrue(manifest["diagnostic_only_never_training"])
        self.assertFalse(manifest["training_authorized"])
        self.assertFalse(manifest["validation_access_authorized"])
        self.assertFalse(manifest["final_access_authorized"])
        self.assertFalse(manifest["checkpoint_authorized"])
        self.assertFalse(manifest["runtime_connection_authorized"])
        self.assertEqual(manifest["observed_guitarist_answer"], "withheld")
        self.assertEqual(manifest["model_output"], "withheld")
        self.assertEqual(manifest["baseline_output"], "withheld")

    def test_manual_voicing_accepts_exact_geometry_and_rejects_wrong_pitch_multiset(self):
        parsed = parse_manual_voicing(
            "6:0,5:2,4:2,3:0",
            pitches_midi=E_MINOR_PITCHES,
        )
        self.assertEqual(parsed, E_MINOR_OBSERVED)
        with self.assertRaisesRegex(ValueError, "pitch multiset"):
            parse_manual_voicing(
                "6:0,5:3,4:2,3:0",
                pitches_midi=E_MINOR_PITCHES,
            )
        with self.assertRaisesRegex(ValueError, "reuses a string"):
            parse_manual_voicing(
                "6:0,6:7,4:2,3:0",
                pitches_midi=E_MINOR_PITCHES,
            )

    def test_export_accepts_shown_choice_manual_and_equal_but_rejects_unknown_candidate(self):
        manifest = _manifest()
        task = manifest["tasks"][0]
        base = {
            "schema": TEACHER_VOICING_EXPORT_SCHEMA,
            "protocol_version": TEACHER_VOICING_PILOT_VERSION,
            "manifest_sha256": manifest["manifest_sha256"],
            "annotator_id": manifest["annotator_id"],
        }

        selected = dict(base)
        selected["decisions"] = [{
            "task_id": task["task_id"],
            "semantic_fingerprint": task["semantic_fingerprint"],
            "decision": DECISION_SELECT_OPTION,
            "selected_candidate_id": task["options"][0]["candidate_id"],
            "manual_voicing": None,
        }]
        summary = validate_teacher_voicing_export(selected, manifest)
        self.assertEqual(summary["decision_counts"][DECISION_SELECT_OPTION], 1)
        self.assertFalse(summary["training_authorized"])

        manual = dict(base)
        manual["decisions"] = [{
            "task_id": task["task_id"],
            "semantic_fingerprint": task["semantic_fingerprint"],
            "decision": DECISION_MANUAL_VOICING,
            "selected_candidate_id": None,
            "manual_voicing": "6:0,5:2,4:2,3:0",
        }]
        manual_summary = validate_teacher_voicing_export(manual, manifest)
        self.assertEqual(len(manual_summary["manual_candidates"]), 1)

        equal = dict(base)
        equal["decisions"] = [{
            "task_id": task["task_id"],
            "semantic_fingerprint": task["semantic_fingerprint"],
            "decision": DECISION_EQUAL_OR_UNSURE,
            "selected_candidate_id": None,
            "manual_voicing": None,
        }]
        self.assertEqual(
            validate_teacher_voicing_export(equal, manifest)["decision_counts"][DECISION_EQUAL_OR_UNSURE],
            1,
        )

        bad = copy.deepcopy(selected)
        bad["decisions"][0]["selected_candidate_id"] = "tvpv1-candidate-sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "shown candidate"):
            validate_teacher_voicing_export(bad, manifest)

    def test_manifest_rejects_duplicate_semantic_task_even_if_event_id_differs(self):
        task1, _ = _task("event-1")
        task2, _ = _task("event-2")
        self.assertNotEqual(task1["task_id"], task2["task_id"])
        self.assertEqual(task1["semantic_fingerprint"], task2["semantic_fingerprint"])
        with self.assertRaisesRegex(ValueError, "duplicate semantic"):
            build_teacher_voicing_manifest(
                batch_id="TVPV1_TEST",
                session_id="TVPV1_TEST",
                tasks=[task1, task2],
            )

    def test_html_has_resume_copy_and_download_paths_without_internal_answer_leakage(self):
        manifest = _manifest()
        page = render_teacher_voicing_html(manifest)
        self.assertIn("localStorage", page)
        self.assertIn("JSON'u kopyala", page)
        self.assertIn("JSON dosyası indir", page)
        self.assertIn("manualInput", page)
        self.assertNotIn("observed_candidate_id", page)
        self.assertNotIn("observed_placements", page)
        self.assertNotIn("source_member", page)

    def test_development_member_selection_is_exact_and_does_not_open_validation_or_final(self):
        tracks = [f"Style{style:02d}-{variant + 100}-C" for style in range(15) for variant in range(2)]
        members = [
            f"annotation/{performer}_{track}_comp.jams"
            for performer in ("00", "01", "02", "03", "04", "05")
            for track in tracks
        ]
        selected = development_members_from_archive_metadata(
            members,
            source_archive_sha256=GUITARSET_SOURCE_ARCHIVE_SHA256,
        )
        self.assertEqual(len(selected), 120)
        performers = {parse_comp_member_identity(member)[0] for member in selected}
        self.assertEqual(performers, {"00", "01", "04", "05"})
        self.assertNotIn("02", performers)
        self.assertNotIn("03", performers)

        with self.assertRaisesRegex(ValueError, "archive SHA mismatch"):
            development_members_from_archive_metadata(
                members,
                source_archive_sha256="0" * 64,
            )

    def test_teacher_manifest_json_contains_no_internal_audit_keys(self):
        manifest = _manifest()
        serialized = json.dumps(manifest, sort_keys=True)
        for forbidden in (
            "observed_candidate_id",
            "observed_placements",
            "source_member",
            "recording_id",
            "performer",
            "track_key",
            "style_key",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
