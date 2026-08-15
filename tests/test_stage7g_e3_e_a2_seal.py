from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SEAL_PATH = ROOT / "evidence" / "stage7g_e3_e_a2_family_selection_seal.json"
EXPECTED_STATUS = "FAMILY_DISJOINTNESS_PASS_SELECTION_POLICY_FROZEN_31_ELIGIBLE"
EXPECTED_EXCLUDED = "chopin_ballade1_op23"
EXPECTED_NEXT_GATE = (
    "ELIGIBLE_FOR_FROZEN_SPECIALIST_RECONSTRUCTION_AND_"
    "OPEN_LOW_COMPACT_DISAGREEMENT_INVENTORY_NO_TEACHER_GOLD"
)


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class Stage7GE3EA2SealTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))

    def test_identity_status_and_input_blobs_are_pinned(self) -> None:
        seal = self.seal
        self.assertEqual(seal["schema"], "st-guitar-stage7g-e3-e-a2-family-selection-seal-v1")
        self.assertEqual(seal["stage"], "7G-E3-E-A2")
        self.assertEqual(seal["status"], EXPECTED_STATUS)
        self.assertEqual(seal["base_main_sha"], "2761cc54b3082c092306ba66ae80e0e65b7b32e8")

        inputs = seal["inputs"]
        for key in ("candidate_manifest", "development_manifest", "stage7e_seal"):
            item = inputs[key]
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(_git_blob_sha1(path), item["git_blob_sha1"], item["path"])

        self.assertEqual(inputs["candidate_manifest"]["candidate_families"], 32)
        self.assertEqual(inputs["development_manifest"]["families"], 40)
        self.assertEqual(inputs["stage7e_seal"]["sealed_output_blobs"], 16)
        self.assertEqual(
            inputs["development_manifest"]["source_hash_set_digest_sha256"],
            "0a357177b92504f28d01b7622652e18ea16e314c4987d367bf60731a4edca8a2",
        )
        self.assertEqual(
            inputs["development_manifest"]["family_id_set_digest_sha256"],
            "2a0467979ec29e8fc88bcb16e826e6873cb92aecbb2c08045929399f873f52fd",
        )

    def test_semantic_gate_records_conservative_provenance_not_header_identity(self) -> None:
        semantic = self.seal["semantic_family_audit"]
        self.assertEqual(semantic["development_semantic_overlap_count"], 0)
        self.assertEqual(semantic["development_semantic_overlap_with_candidates"], [])
        self.assertEqual(
            semantic["family_identity_gate"],
            "PASS_CONSERVATIVE_DEVELOPMENT_AND_STAGE7E_SEMANTIC_DISJOINTNESS",
        )

        header = semantic["stage7e_header_metadata"]
        self.assertEqual(header["exact_gp3_blobs_checked"], 16)
        self.assertTrue(header["all_title_artist_album_and_related_info_fields_empty"])
        self.assertFalse(header["musical_content_parsed"])
        self.assertIn("cannot prove family identity", header["interpretation"])

        provenance = semantic["stage7e_generator_provenance"]
        self.assertEqual(provenance["possible_source_file_count"], 9)
        self.assertEqual(provenance["possible_distinct_work_count"], 8)
        self.assertEqual(len(provenance["possible_source_paths_complete_at_pinned_commit"]), 9)
        self.assertEqual(len(provenance["possible_distinct_work_identities"]), 8)
        self.assertFalse(provenance["direct_numbered_output_to_input_mapping_reconstructed"])
        self.assertEqual(provenance["semantic_overlap_with_candidates"], [])
        self.assertEqual(provenance["semantic_overlap_count"], 0)

    def test_selection_policy_is_target_blind_and_fail_closed(self) -> None:
        policy = self.seal["target_free_selection_policy"]
        self.assertEqual(policy["policy_version"], "e3e-a2-v1")
        self.assertEqual(policy["pitch_mode"], "sounding_exact")
        self.assertEqual(policy["tuning_midi"], [64, 59, 55, 50, 45, 40])
        self.assertEqual(policy["mixed_explicit_and_unstaffed_rule"], "FAIL_CLOSED")
        self.assertFalse(policy["uses_physical_candidate_counts"])
        self.assertFalse(policy["uses_specialist_scores"])
        self.assertFalse(policy["uses_router_outputs"])
        self.assertFalse(policy["uses_teacher_gold"])
        self.assertEqual(policy["selection_execution"]["sources_selected"], 32)
        self.assertEqual(policy["selection_execution"]["selection_failures"], 0)

        preflight = policy["target_free_parser_preflight"]
        self.assertEqual(preflight["sources_checked"], 32)
        self.assertEqual(preflight["passes"], 31)
        self.assertEqual(preflight["failures"], 1)
        failure = preflight["failure"]
        self.assertEqual(failure["family_key"], EXPECTED_EXCLUDED)
        self.assertEqual(failure["error"], "backup moved cursor before measure start")
        self.assertEqual(
            failure["resolution"],
            "QUARANTINE_SOURCE_BEFORE_SPECIALIST_SCORING_NO_PARSER_RELAXATION",
        )

    def test_eligible_set_is_exactly_candidate_set_minus_parser_quarantine(self) -> None:
        candidate = json.loads(
            (ROOT / "evidence" / "stage7g_e3_e_a1_source_manifest.json").read_text(encoding="utf-8")
        )
        candidate_keys = {
            row["family_key"] for row in candidate["external_corpus"]["paths"]
        }
        eligible = self.seal["eligible_source_set"]
        selection_rows = eligible["selections"]
        selection_keys = {row["family_key"] for row in selection_rows}

        self.assertEqual(len(candidate_keys), 32)
        self.assertEqual(eligible["candidate_families_before_parser_preflight"], 32)
        self.assertEqual(eligible["parser_incompatible_quarantined"], 1)
        self.assertEqual(eligible["eligible_families"], 31)
        self.assertEqual(eligible["excluded_family_keys"], [EXPECTED_EXCLUDED])
        self.assertEqual(selection_keys, candidate_keys - {EXPECTED_EXCLUDED})
        self.assertEqual(len(selection_rows), 31)
        self.assertNotIn(EXPECTED_EXCLUDED, selection_keys)

        part_counts: dict[str, int] = {}
        staff_counts = {"1": 0, "2": 0, "null": 0}
        for row in selection_rows:
            part_counts[row["part_id"]] = part_counts.get(row["part_id"], 0) + 1
            key = "null" if row["staff_id"] is None else row["staff_id"]
            staff_counts[key] += 1
        self.assertEqual(part_counts, {"P1": 30, "P2": 1})
        self.assertEqual(staff_counts, {"1": 18, "2": 12, "null": 1})
        self.assertEqual(eligible["selected_part_counts"], part_counts)
        self.assertEqual(eligible["selected_staff_counts"], staff_counts)

        standchen = next(
            row for row in selection_rows
            if row["family_key"] == "schubert_standchen_d957_no4_liszt_arr"
        )
        self.assertEqual(standchen["part_id"], "P2")
        self.assertIsNone(standchen["staff_id"])

    def test_next_gate_and_scientific_boundaries_remain_closed(self) -> None:
        self.assertEqual(self.seal["next_gate"], EXPECTED_NEXT_GATE)
        boundary = self.seal["scientific_boundary"]
        for key in (
            "teacher_gold_generated",
            "teacher_gold_answers_read",
            "specialist_scored",
            "router_scored",
            "model_fit",
            "threshold_selected",
            "checkpoint_retained",
            "production_integration",
            "stage7e_musical_content_used_for_development",
            "commercial_or_production_clearance",
        ):
            self.assertFalse(boundary[key], key)
        self.assertTrue(boundary["stage7e_header_metadata_only"])


if __name__ == "__main__":
    unittest.main()
