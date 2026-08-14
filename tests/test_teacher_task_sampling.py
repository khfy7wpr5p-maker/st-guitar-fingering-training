import json
import unittest

import numpy as np

from st_guitar_fingering_training.intake import GuitarEvent, ParsedSource, Placement
from st_guitar_fingering_training.teacher_task_sampling import (
    build_annotation_sampling_pool,
    internal_sampling_audit,
    select_annotation_batch,
    teacher_facing_manifest,
)


TUNING = (64, 59, 55, 50, 45, 40)


class _AscendingModel:
    def decision_function(self, X):
        return np.arange(len(X), dtype=np.float64)


class _DescendingModel:
    def decision_function(self, X):
        return -np.arange(len(X), dtype=np.float64)


def _models():
    return {
        "open_low": _AscendingModel(),
        "compact": _DescendingModel(),
        "mid_position": _DescendingModel(),
        "high_position": _DescendingModel(),
    }


def _c_major_placements_variant_a():
    return (
        Placement(sounding_midi=48, xml_midi=48, string=5, fret=3),
        Placement(sounding_midi=52, xml_midi=52, string=4, fret=2),
        Placement(sounding_midi=55, xml_midi=55, string=3, fret=0),
        Placement(sounding_midi=60, xml_midi=60, string=2, fret=1),
    )


def _c_major_placements_variant_b():
    # Same pitches, deliberately different valid strings/frets. Stage 7G-B must
    # produce the same candidates and specialist diagnostics because observed
    # source voicing is not a sampling input.
    return (
        Placement(sounding_midi=48, xml_midi=48, string=6, fret=8),
        Placement(sounding_midi=52, xml_midi=52, string=5, fret=7),
        Placement(sounding_midi=55, xml_midi=55, string=4, fret=5),
        Placement(sounding_midi=60, xml_midi=60, string=3, fret=5),
    )


def _source(
    digest: str,
    family: str,
    placements=None,
    event_count: int = 2,
):
    placements = placements or _c_major_placements_variant_a()
    events = tuple(
        GuitarEvent(
            family_id=family,
            source_sha256=digest,
            musicxml_version="4.0",
            software="fixture",
            pitch_mode="physical",
            tuning=TUNING,
            measure=str(index + 1),
            onset=index * 4,
            duration=4,
            voice="1",
            placements=placements,
        )
        for index in range(event_count)
    )
    return ParsedSource(
        family_id=family,
        source_sha256=digest,
        musicxml_version="4.0",
        software="fixture",
        pitch_mode="physical",
        tuning=TUNING,
        selected_staff="2",
        events=events,
    )


class TeacherTaskSamplingTests(unittest.TestCase):
    def test_sampling_is_independent_of_observed_source_voicing(self):
        digest = "a" * 64
        source_a = _source(digest, "family-a", _c_major_placements_variant_a(), event_count=1)
        source_b = _source(digest, "family-a", _c_major_placements_variant_b(), event_count=1)
        kwargs = {
            "source_origins": {digest: "new-corpus/source-a"},
            "specialist_models": _models(),
        }
        pool_a = build_annotation_sampling_pool((source_a,), **kwargs)
        pool_b = build_annotation_sampling_pool((source_b,), **kwargs)
        self.assertEqual(pool_a[0].task.pitches_midi, pool_b[0].task.pitches_midi)
        self.assertEqual(pool_a[0].task.candidates, pool_b[0].task.candidates)
        self.assertEqual(
            pool_a[0].diagnostic.specialist_top1,
            pool_b[0].diagnostic.specialist_top1,
        )
        self.assertEqual(
            pool_a[0].diagnostic.open_low_compact_disagreement,
            pool_b[0].diagnostic.open_low_compact_disagreement,
        )

    def test_open_low_compact_disagreement_is_highest_priority(self):
        digest = "b" * 64
        source = _source(digest, "family-b", event_count=2)
        pool = build_annotation_sampling_pool(
            (source,),
            source_origins={digest: "new-corpus/source-b"},
            specialist_models=_models(),
        )
        self.assertTrue(all(row.diagnostic.open_low_compact_disagreement for row in pool))
        self.assertTrue(all(row.diagnostic.priority_tier == 0 for row in pool))

    def test_family_balanced_selection_prevents_one_source_from_dominating_first_round(self):
        source_a = _source("c" * 64, "family-c", event_count=5)
        source_b = _source("d" * 64, "family-d", event_count=1)
        pool = build_annotation_sampling_pool(
            (source_a, source_b),
            source_origins={
                "c" * 64: "new-corpus/source-c",
                "d" * 64: "new-corpus/source-d",
            },
            specialist_models=_models(),
        )
        batch = select_annotation_batch(pool, max_tasks=2)
        self.assertEqual(batch.selected_families, 2)
        self.assertEqual({task.family_id for task in batch.tasks}, {"family-c", "family-d"})

    def test_teacher_manifest_withholds_source_identity_and_specialist_predictions(self):
        digest = "e" * 64
        source = _source(digest, "family-e", event_count=1)
        pool = build_annotation_sampling_pool(
            (source,),
            source_origins={digest: "new-corpus/secret-source"},
            specialist_models=_models(),
        )
        batch = select_annotation_batch(pool, max_tasks=1)
        teacher_manifest = teacher_facing_manifest(batch)
        audit = internal_sampling_audit(batch)
        serialized_teacher = json.dumps(teacher_manifest, sort_keys=True)
        serialized_audit = json.dumps(audit, sort_keys=True)

        self.assertNotIn("secret-source", serialized_teacher)
        self.assertNotIn(digest, serialized_teacher)
        self.assertNotIn("family-e", serialized_teacher)
        self.assertNotIn("open_low", serialized_teacher)
        self.assertNotIn("compact", serialized_teacher)
        self.assertEqual(teacher_manifest["model_predictions"], "withheld")
        self.assertEqual(teacher_manifest["observed_source_voicing"], "withheld")
        self.assertIn("open_low", serialized_audit)
        self.assertIn("secret-source", serialized_audit)
        self.assertFalse(audit["target_voicing_used_for_sampling"])
        self.assertFalse(audit["observed_string_fret_used_for_sampling"])

    def test_stage7e_hash_and_origin_quarantine_fail_closed(self):
        digest = "f" * 64
        source = _source(digest, "family-f", event_count=1)
        common = {
            "sources": (source,),
            "source_origins": {digest: "stage7e/final-source"},
            "specialist_models": _models(),
        }
        with self.assertRaisesRegex(ValueError, "quarantined source"):
            build_annotation_sampling_pool(
                **common,
                forbidden_source_hashes={digest},
            )
        with self.assertRaisesRegex(ValueError, "quarantined source"):
            build_annotation_sampling_pool(
                **common,
                forbidden_source_origins={"stage7e/final-source"},
            )

    def test_source_origin_and_specialist_metadata_must_match_exactly(self):
        digest = "1" * 64
        source = _source(digest, "family-one", event_count=1)
        with self.assertRaisesRegex(ValueError, "source_origins"):
            build_annotation_sampling_pool(
                (source,),
                source_origins={},
                specialist_models=_models(),
            )
        extra_models = dict(_models())
        extra_models["common_tone"] = _AscendingModel()
        with self.assertRaisesRegex(ValueError, "exactly the four stateless specialists"):
            build_annotation_sampling_pool(
                (source,),
                source_origins={digest: "new-corpus/source-one"},
                specialist_models=extra_models,
            )


if __name__ == "__main__":
    unittest.main()
