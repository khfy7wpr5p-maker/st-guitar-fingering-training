from __future__ import annotations

import unittest

from st_guitar_fingering_training.guitarset_teacher_voicing_blind import (
    build_complete_blinded_teacher_voicing_task,
)


class GuitarSetTeacherVoicingBlindTests(unittest.TestCase):
    def test_complete_candidate_seam_refuses_partial_display(self):
        with self.assertRaisesRegex(ValueError, "refuses partial candidate display"):
            build_complete_blinded_teacher_voicing_task(
                event_id="too-many-candidates",
                pitches_midi=(64, 67),
                observed_placements=((64, 1, 0), (67, 2, 8)),
                option_cap=6,
            )

    def test_complete_candidate_seam_keeps_all_options_for_eligible_task(self):
        task, audit = build_complete_blinded_teacher_voicing_task(
            event_id="eligible-two-candidates",
            pitches_midi=(40, 47, 55),
            observed_placements=((40, 6, 0), (47, 5, 2), (55, 3, 0)),
            option_cap=6,
        )
        self.assertEqual(task["option_count"], task["full_candidate_count"])
        self.assertEqual(task["full_candidate_count"], 2)
        self.assertIn(
            audit["observed_candidate_id"],
            {row["candidate_id"] for row in task["options"]},
        )
        self.assertNotIn("observed_candidate_id", task)


if __name__ == "__main__":
    unittest.main()
