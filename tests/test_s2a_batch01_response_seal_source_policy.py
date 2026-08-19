from __future__ import annotations

import json
from pathlib import Path
import unittest


class S2ABatch01ResponseSealSourcePolicyTests(unittest.TestCase):
    def test_response_seal_requires_source_policy_review(self):
        root = Path(__file__).resolve().parents[1]
        seal = json.loads(
            (root / "evidence" / "stage7g_e3_s2a_batch01_first_pass_response_seal.json").read_text(
                encoding="utf-8"
            )
        )
        boundary = seal["scientific_boundary"]
        self.assertTrue(boundary["source_family_identities_reused_as_label_free_music_sources"])
        self.assertTrue(boundary["source_policy_fit_eligibility_requires_explicit_contract_review_before_any_fit"])

        decision = json.loads(
            (root / "evidence" / "stage7g_e3_s2a_batch01_diagnostic_decision.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(decision["source_policy_review"]["fit_eligibility"])
        self.assertEqual(decision["source_policy_review"]["effective_s2a_fit_rows_from_batch01"], 0)


if __name__ == "__main__":
    unittest.main()
