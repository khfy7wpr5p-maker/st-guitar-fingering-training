from __future__ import annotations

import json
from pathlib import Path
import unittest

from st_guitar_fingering_training.guitarset_split import (
    PURPOSE_DEV_CV,
    PURPOSE_FINAL_EVAL,
    PURPOSE_FIT,
    PURPOSE_VALIDATION_EVAL,
    ROLE_DEVELOPMENT,
    ROLE_UNTOUCHED_FINAL,
    ROLE_VALIDATION,
    assert_role_use,
    build_split_contract,
    frozen_performer_roles,
    source_role,
)

ARCHIVE_SHA256 = "06dc776d1de92021632e30795f0d4f38534fe01ca5342a164e80e8cd287980fe"


def _members() -> list[str]:
    tracks = [f"Style{style:02d}-{variant + 100}-C" for style in range(15) for variant in range(2)]
    return [
        f"annotation/{performer}_{track}_comp.jams"
        for performer in ("00", "01", "02", "03", "04", "05")
        for track in tracks
    ]


class GuitarSetSplitLeakageTests(unittest.TestCase):
    def test_frozen_performer_selection_is_label_blind_and_exact(self):
        roles = frozen_performer_roles(
            ("00", "01", "02", "03", "04", "05"),
            source_archive_sha256=ARCHIVE_SHA256,
        )
        self.assertEqual(roles[ROLE_UNTOUCHED_FINAL], ("02",))
        self.assertEqual(roles[ROLE_VALIDATION], ("03",))
        self.assertEqual(roles[ROLE_DEVELOPMENT], ("00", "01", "04", "05"))
        for _ in range(10):
            self.assertEqual(
                frozen_performer_roles(reversed(("00", "01", "02", "03", "04", "05")), source_archive_sha256=ARCHIVE_SHA256),
                roles,
            )

    def test_contract_is_performer_and_recording_isolated(self):
        contract = build_split_contract(_members(), source_archive_sha256=ARCHIVE_SHA256)
        self.assertEqual(contract["benchmark_target"], "UNSEEN_PERFORMER_SEEN_REPERTOIRE")
        self.assertEqual(contract["recording_counts"], {
            ROLE_DEVELOPMENT: 120,
            ROLE_VALIDATION: 30,
            ROLE_UNTOUCHED_FINAL: 30,
        })
        self.assertEqual(contract["performer_overlap_across_roles"], 0)
        self.assertEqual(contract["recording_overlap_across_roles"], 0)
        self.assertFalse(contract["training_authorized"])
        self.assertFalse(contract["final_access_authorized"])

    def test_track_and_style_overlap_is_explicit_not_hidden(self):
        contract = build_split_contract(_members(), source_archive_sha256=ARCHIVE_SHA256)
        self.assertEqual(contract["shared_track_identity_count_across_roles"], 30)
        self.assertEqual(contract["shared_style_identity_count_across_roles"], 15)
        self.assertEqual(
            contract["track_overlap_policy"],
            "INTENTIONAL_COVARIATE_MATCHING_NOT_UNSEEN_REPERTOIRE",
        )
        self.assertEqual(
            contract["style_overlap_policy"],
            "INTENTIONAL_COVARIATE_MATCHING_NOT_UNSEEN_STYLE",
        )

    def test_topology_drift_fails_closed(self):
        members = _members()
        with self.assertRaisesRegex(ValueError, "exactly 30 recordings"):
            build_split_contract(members[:-1], source_archive_sha256=ARCHIVE_SHA256)
        with self.assertRaisesRegex(ValueError, "duplicate recording"):
            build_split_contract(members + [members[0]], source_archive_sha256=ARCHIVE_SHA256)

    def test_frozen_roles_enforce_fit_validation_and_final_use(self):
        contract = build_split_contract(_members(), source_archive_sha256=ARCHIVE_SHA256)
        self.assertEqual(source_role("annotation/00_Style00-100-C_comp.jams", contract), ROLE_DEVELOPMENT)
        self.assertEqual(source_role("annotation/03_Style00-100-C_comp.jams", contract), ROLE_VALIDATION)
        self.assertEqual(source_role("annotation/02_Style00-100-C_comp.jams", contract), ROLE_UNTOUCHED_FINAL)
        assert_role_use(ROLE_DEVELOPMENT, PURPOSE_FIT)
        assert_role_use(ROLE_DEVELOPMENT, PURPOSE_DEV_CV)
        assert_role_use(ROLE_VALIDATION, PURPOSE_VALIDATION_EVAL)
        assert_role_use(ROLE_UNTOUCHED_FINAL, PURPOSE_FINAL_EVAL)
        with self.assertRaises(ValueError):
            assert_role_use(ROLE_VALIDATION, PURPOSE_FIT)
        with self.assertRaises(ValueError):
            assert_role_use(ROLE_UNTOUCHED_FINAL, PURPOSE_FIT)
        with self.assertRaises(ValueError):
            assert_role_use(ROLE_UNTOUCHED_FINAL, PURPOSE_VALIDATION_EVAL)

    def test_repository_evidence_freezes_current_roles_and_matches_upstream_totals(self):
        root = Path(__file__).parents[1]
        split_path = root / "evidence" / "stage7g_e3_guitarset_split_leakage_v1.json"
        observed_path = root / "evidence" / "stage7g_e3_guitarset_comp_observed_gold_v1.json"
        evidence = json.loads(split_path.read_text(encoding="utf-8"))
        observed = json.loads(observed_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["source_archive_sha256"], ARCHIVE_SHA256)
        self.assertEqual(evidence["source_archive_sha256"], observed["source_archive_sha256"])
        self.assertEqual(evidence["performer_roles"][ROLE_UNTOUCHED_FINAL], ["02"])
        self.assertEqual(evidence["performer_roles"][ROLE_VALIDATION], ["03"])
        self.assertEqual(evidence["performer_roles"][ROLE_DEVELOPMENT], ["00", "01", "04", "05"])
        self.assertEqual(evidence["recording_counts"], {
            ROLE_DEVELOPMENT: 120,
            ROLE_VALIDATION: 30,
            ROLE_UNTOUCHED_FINAL: 30,
        })
        self.assertEqual(sum(evidence["recording_counts"].values()), observed["comp_recording_count"])
        self.assertEqual(sum(evidence["raw_note_counts"].values()), observed["raw_note_count"])
        self.assertEqual(sum(evidence["accepted_note_counts"].values()), observed["accepted_note_count"])
        self.assertEqual(sum(evidence["quarantined_note_counts"].values()), observed["quarantined_note_count"])
        self.assertEqual(sum(evidence["derived_strum_voicing_counts"].values()), observed["derived_strum_voicing_count"])
        self.assertFalse(evidence["training_authorized"])
        self.assertFalse(evidence["final_access_authorized"])
        self.assertEqual(evidence["next_gate"], "OBSERVED_VOICING_MODEL_PREREGISTRATION")


if __name__ == "__main__":
    unittest.main()
