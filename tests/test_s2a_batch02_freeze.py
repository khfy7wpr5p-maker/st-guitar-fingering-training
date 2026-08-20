from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest


FREEZE = Path('evidence/stage7g_e3_s2a_hc_qualified_reservation_freeze_v1.json')


class S2ABatch02FreezeTests(unittest.TestCase):
    def test_freeze_manifest_is_canonical_and_closed(self):
        payload = json.loads(FREEZE.read_text(encoding='utf-8'))
        self.assertEqual(payload['status'], 'FROZEN')
        stored = payload.pop('manifest_sha256')
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        self.assertEqual(sha256(raw).hexdigest(), stored)
        self.assertEqual(stored, '39c2349695c0679929fbf506fdf1f79cec5a1b7b00823d396c849cd226b56eb6')
        self.assertEqual(payload['reservation']['identity_sha256'], 'cf7faf6f8f86fbd4819be3b393850dd3e43e7647edaf51584c9e9a4593482807')
        self.assertEqual(payload['reservation']['hc_pass_source_count'], 120)
        self.assertEqual(payload['reservation']['hc_fail_source_count'], 0)
        self.assertEqual(payload['freeze_policy']['batch02_source_role'], 'PRIMARY_DEVELOPMENT')
        self.assertFalse(payload['freeze_policy']['batch02_may_use_contingency'])
        self.assertFalse(payload['freeze_policy']['batch02_may_use_untouched_final'])
        self.assertFalse(payload['scientific_boundary']['new_teacher_labels_collected'])
        self.assertFalse(payload['scientific_boundary']['real_model_fit_executed'])


if __name__ == '__main__':
    unittest.main()
