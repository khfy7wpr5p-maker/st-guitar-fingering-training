from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Stage7GE3EA1LiveAuditExecutionTests(unittest.TestCase):
    def test_live_source_structure_audit(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "stage7g_e3_e_a1_live_audit.json"
            work = tmp_path / "mxl"
            command = [
                sys.executable,
                "scripts/audit_stage7g_e3_e_a1_sources.py",
                "--manifest",
                "evidence/stage7g_e3_e_a1_source_manifest.json",
                "--development-source-manifest",
                "evidence/stage7g_c_r1_animetab_batch01_manifest.json",
                "--stage7e-seal",
                "evidence/stage7e_final_test_seal.json",
                "--output",
                str(output),
                "--work-dir",
                str(work),
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
            )
            print("LIVE_AUDIT_STDOUT_BEGIN")
            print(completed.stdout)
            print("LIVE_AUDIT_STDOUT_END")
            if completed.stderr:
                print("LIVE_AUDIT_STDERR_BEGIN")
                print(completed.stderr)
                print("LIVE_AUDIT_STDERR_END")
            self.assertEqual(
                completed.returncode,
                0,
                msg=f"live audit failed closed with return code {completed.returncode}: {completed.stderr}",
            )

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                report["status"],
                "STRUCTURE_AUDIT_PASS_FAMILY_DISJOINTNESS_NOT_YET_SEALED",
            )
            self.assertEqual(report["source_file_count"], 32)
            self.assertEqual(report["candidate_family_count"], 32)
            self.assertEqual(
                report["development_quarantine"]["exact_source_sha256_overlap"],
                0,
            )
            self.assertEqual(
                report["stage7e_quarantine"]["exact_git_blob_overlap"],
                0,
            )
            self.assertEqual(
                report["family_identity_gate"],
                "PENDING_CONSERVATIVE_SEMANTIC_FAMILY_AUDIT",
            )
            self.assertEqual(report["part_staff_selection_policy"], "NOT_YET_FROZEN")

            safety = report["safety"]
            for key in (
                "contains_teacher_gold_labels",
                "teacher_gold_answers_read",
                "specialist_scored",
                "router_scored",
                "model_fit",
                "threshold_selected",
                "checkpoint_retained",
                "production_integration",
                "stage7e_used_for_modeling",
                "raw_external_mxl_committed_to_training_repo",
            ):
                self.assertFalse(safety[key], msg=f"safety flag must remain false: {key}")

            concise = {
                "schema": report["schema"],
                "stage": report["stage"],
                "status": report["status"],
                "repository": report["repository"],
                "repository_commit": report["repository_commit"],
                "source_file_count": report["source_file_count"],
                "candidate_family_count": report["candidate_family_count"],
                "single_part_sources": report["single_part_sources"],
                "multi_part_sources": report["multi_part_sources"],
                "sources_with_multi_staff_part": report["sources_with_multi_staff_part"],
                "development_quarantine": report["development_quarantine"],
                "stage7e_quarantine": report["stage7e_quarantine"],
                "family_identity_gate": report["family_identity_gate"],
                "part_staff_selection_policy": report["part_staff_selection_policy"],
                "safety": report["safety"],
                "sources": [
                    {
                        "family_id": row["family_id"],
                        "family_key": row["family_key"],
                        "source_path": row["source_path"],
                        "git_blob_sha1": row["git_blob_sha1"],
                        "source_sha256": row["source_sha256"],
                        "bytes": row["bytes"],
                        "structure": row["structure"],
                    }
                    for row in report["sources"]
                ],
            }
            print("LIVE_AUDIT_REPORT_BEGIN")
            print(json.dumps(concise, ensure_ascii=False, sort_keys=True))
            print("LIVE_AUDIT_REPORT_END")


if __name__ == "__main__":
    unittest.main()
