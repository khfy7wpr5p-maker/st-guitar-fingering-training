from __future__ import annotations

from collections import Counter
import unittest

from st_guitar_fingering_training.s2a_batch import (
    S2A_BATCH_EXPECTED_FAMILIES,
    S2A_BATCH_SESSION_COUNT,
    S2A_BATCH_TARGET_PER_CELL,
    S2AEventPackage,
    batch_summary,
    build_event_packages,
    select_balanced_batch,
    split_sessions,
)
from st_guitar_fingering_training.s2a_teacher import S2A_FIRST_PASS_PROVENANCE
from st_guitar_fingering_training.target_free_musicxml import TargetFreeEvent, TargetFreeSource


CELLS = tuple(
    (pair_type, stratum)
    for pair_type in ("FINGER_ONLY", "MIXED")
    for stratum in ("NEAR", "MID", "FAR")
)


def _fake_event_package(family_index: int, event_index: int) -> S2AEventPackage:
    family_id = f"family{family_index:02d}"
    event_id = f"event-{family_index:02d}-{event_index:02d}"
    tasks = []
    audits = []
    for cell_index, (pair_type, stratum) in enumerate(CELLS):
        task_id = f"task-{family_index:02d}-{event_index:02d}-{cell_index}"
        tasks.append(
            {
                "task_id": task_id,
                "pitches_midi": [48, 52, 55],
                "tuning": [64, 59, 55, 50, 45, 40],
                "options": [
                    {
                        "option_id": "A",
                        "assignment_id": f"a-{task_id}",
                        "placements": [{"pitch_midi": 48, "string": 5, "fret": 3, "finger": 1}],
                        "barres": [],
                    },
                    {
                        "option_id": "B",
                        "assignment_id": f"b-{task_id}",
                        "placements": [{"pitch_midi": 48, "string": 5, "fret": 3, "finger": 2}],
                        "barres": [],
                    },
                ],
                "allowed_responses": ["A", "B", "EQUAL_OR_UNSURE"],
            }
        )
        audits.append(
            {
                "task_id": task_id,
                "pair_id": f"pair-{task_id}",
                "family_id": family_id,
                "event_id": event_id,
                "pitches_midi": [48, 52, 55],
                "tuning": [64, 59, 55, 50, 45, 40],
                "pair_type": pair_type,
                "distance_stratum": stratum,
                "distance_l1": float(cell_index + 1),
                "A_assignment_id": f"a-{task_id}",
                "B_assignment_id": f"b-{task_id}",
                "A_candidate_id": "candidate-a",
                "B_candidate_id": "candidate-b",
                "A_features": [0.0] * 30,
                "B_features": [0.0] * 30,
            }
        )
    return S2AEventPackage(family_id, event_id, tuple(tasks), tuple(audits))


def _contains_exact_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_exact_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact_key(item, key) for item in value)
    return False


class S2ABatchTests(unittest.TestCase):
    def test_real_hc_event_package_contains_finger_assignments_not_old_labels(self):
        tuning = (64, 59, 55, 50, 45, 40)
        event = TargetFreeEvent(
            family_id="family-real",
            source_sha256="a" * 64,
            musicxml_version="4.0",
            software="test",
            pitch_mode="sounding_exact",
            tuning=tuning,
            measure="1",
            onset=0,
            duration=4,
            voice="1",
            pitches_midi=(48, 52, 55, 60, 64),
        )
        source = TargetFreeSource(
            family_id="family-real",
            source_sha256="a" * 64,
            musicxml_version="4.0",
            software="test",
            pitch_mode="sounding_exact",
            tuning=tuning,
            part_id="P1",
            selected_staff="2",
            events=(event,),
        )
        packages = build_event_packages((source,))
        self.assertEqual(len(packages), 1)
        self.assertGreaterEqual(len(packages[0].teacher_tasks), 1)
        option = packages[0].teacher_tasks[0]["options"][0]
        self.assertTrue(option["assignment_id"].startswith("fingering-sha256:"))
        self.assertTrue(all("finger" in placement for placement in option["placements"]))
        self.assertFalse(_contains_exact_key(packages[0].teacher_tasks, "teacher_preference"))
        self.assertFalse(_contains_exact_key(packages[0].teacher_tasks, "historical_response"))

    def test_balanced_720_batch_forces_40_families_and_at_least_200_events(self):
        packages = tuple(
            _fake_event_package(family_index, event_index)
            for family_index in range(1, S2A_BATCH_EXPECTED_FAMILIES + 1)
            for event_index in range(1, 7)
        )
        selected = select_balanced_batch(packages)
        self.assertEqual(len(selected), S2A_BATCH_TARGET_PER_CELL * len(CELLS))
        self.assertEqual(len({row.family_id for row in selected}), 40)
        self.assertGreaterEqual(len({row.event_id for row in selected}), 200)
        cell_counts = Counter(row.cell for row in selected)
        self.assertEqual(set(cell_counts), set(CELLS))
        self.assertTrue(all(cell_counts[cell] == 120 for cell in CELLS))
        self.assertLessEqual(max(Counter(row.event_id for row in selected).values()), 4)
        self.assertLessEqual(max(Counter(row.family_id for row in selected).values()), 24)
        self.assertEqual(
            tuple(row.task_id for row in selected),
            tuple(row.task_id for row in select_balanced_batch(packages)),
        )

    def test_six_sessions_are_120_tasks_and_keep_sampling_metadata_hidden(self):
        packages = tuple(
            _fake_event_package(family_index, event_index)
            for family_index in range(1, 41)
            for event_index in range(1, 7)
        )
        selected = select_balanced_batch(packages)
        sessions = split_sessions(selected)
        self.assertEqual(len(sessions), S2A_BATCH_SESSION_COUNT)
        all_task_ids = set()
        for manifest, audit in sessions:
            self.assertEqual(manifest["provenance"], S2A_FIRST_PASS_PROVENANCE)
            self.assertEqual(manifest["task_count"], 120)
            self.assertEqual(audit["task_count"], 120)
            self.assertFalse(audit["historical_teacher_response_used"])
            self.assertFalse(_contains_exact_key(manifest, "family_id"))
            self.assertFalse(_contains_exact_key(manifest, "pair_type"))
            self.assertFalse(_contains_exact_key(manifest, "distance_stratum"))
            ids = {row["task_id"] for row in manifest["tasks"]}
            self.assertFalse(all_task_ids & ids)
            all_task_ids |= ids
            audit_cells = Counter((row["pair_type"], row["distance_stratum"]) for row in audit["rows"])
            self.assertTrue(all(audit_cells[cell] == 20 for cell in CELLS))
        self.assertEqual(len(all_task_ids), 720)

        summary = batch_summary(selected, sessions)
        self.assertEqual(summary["task_count"], 720)
        self.assertEqual(summary["family_count"], 40)
        self.assertGreaterEqual(summary["event_count"], 200)
        self.assertEqual(summary["pair_type_counts"], {"FINGER_ONLY": 360, "MIXED": 360})
        self.assertEqual(summary["distance_stratum_counts"], {"FAR": 240, "MID": 240, "NEAR": 240})
        self.assertFalse(summary["historical_teacher_responses_reused"])

    def test_family_with_insufficient_eligible_events_fails_closed(self):
        packages = tuple(
            _fake_event_package(family_index, event_index)
            for family_index in range(1, 41)
            for event_index in range(1, 7 if family_index != 40 else 5)
        )
        with self.assertRaisesRegex(ValueError, "lacks 5 eligible H-C events"):
            select_balanced_batch(packages)


if __name__ == "__main__":
    unittest.main()
