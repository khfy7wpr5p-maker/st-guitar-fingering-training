import unittest

from st_guitar_fingering_training.guitarset_voicing_prereg_v2 import (
    EXPECTED_FEATURE_SCHEMA_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GUITARSET_OBSERVED_VOICING_MODEL_VERSION,
    GUITARSET_VOICING_MAX_FRET,
    assert_frozen_protocol,
    feature_schema_sha256,
    protocol_payload,
    protocol_sha256,
)


class GuitarSetVoicingPreregV2Tests(unittest.TestCase):
    def test_frozen_v2_identity_and_domain(self):
        assert_frozen_protocol()
        self.assertEqual(GUITARSET_OBSERVED_VOICING_MODEL_VERSION, "GUITARSET-OBSERVED-VOICING-MODEL.v2")
        self.assertEqual(GUITARSET_VOICING_MAX_FRET, 20)
        self.assertEqual(feature_schema_sha256(), EXPECTED_FEATURE_SCHEMA_SHA256)
        self.assertEqual(protocol_sha256(), EXPECTED_PROTOCOL_SHA256)

    def test_v2_preserves_scientific_and_authority_boundaries(self):
        protocol = protocol_payload()
        self.assertTrue(protocol["training_authorized"])
        self.assertFalse(protocol["checkpoint_authorized"])
        self.assertFalse(protocol["runtime_connection_authorized"])
        self.assertFalse(protocol["production_authorized"])
        self.assertFalse(protocol["final_access_authorized"])
        self.assertEqual(protocol["candidate_set"]["max_fret"], 20)
        self.assertEqual(protocol["domain_extension"]["source_observed_max_fret"], 19)
        self.assertEqual(protocol["domain_extension"]["observed_fret20_positive_gold_expected"], 0)
        self.assertFalse(protocol["domain_extension"]["fret20_quality_authority"])


if __name__ == "__main__":
    unittest.main()
