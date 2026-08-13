import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from st_guitar_fingering_training.dataset import valid_chord_voicings
from st_guitar_fingering_training.intake import parse_guitar_musicxml
from st_guitar_fingering_training.synthetic import (
    MAX_SYNTH_FRET,
    STANDARD_TUNING,
    family_to_musicxml,
    generate_synthetic_corpus,
    generate_synthetic_family,
)


class SyntheticCorpusTests(unittest.TestCase):
    def test_family_is_deterministic_and_not_teacher_gold(self):
        first = generate_synthetic_family(17, events_per_family=8)
        second = generate_synthetic_family(17, events_per_family=8)
        self.assertEqual(first, second)
        self.assertEqual(first.label_class, "RULE_PREFERRED")
        self.assertFalse(first.teacher_gold)
        self.assertEqual(len(first.events), 8)

    def test_preferred_voicings_are_physical_and_ambiguous(self):
        family = generate_synthetic_family(7, events_per_family=12)
        for event in family.events:
            candidates = tuple(
                voicing for voicing in valid_chord_voicings(event.pitches_midi, STANDARD_TUNING)
                if max(fret for _, _, fret in voicing) <= MAX_SYNTH_FRET
            )
            self.assertIn(event.preferred, candidates)
            self.assertGreaterEqual(event.candidate_count, 2)
            self.assertEqual(event.candidate_count, len(candidates))
            self.assertEqual(len({string for _, string, _ in event.preferred}), len(event.preferred))

    def test_musicxml_roundtrip_preserves_chord_events(self):
        family = generate_synthetic_family(3, events_per_family=8)
        with TemporaryDirectory() as td:
            path = Path(td) / "family.xml"
            path.write_text(family_to_musicxml(family), encoding="utf-8")
            parsed = parse_guitar_musicxml(path, family_id=family.family_id)
        self.assertEqual(parsed.pitch_mode, "sounding_exact")
        self.assertEqual(parsed.tuning, STANDARD_TUNING)
        self.assertEqual(len(parsed.events), 8)
        self.assertTrue(all(event.is_chord for event in parsed.events))

    def test_small_corpus_writes_manifest_and_family_map(self):
        with TemporaryDirectory() as td:
            summary = generate_synthetic_corpus(td, families=5, events_per_family=8)
            root = Path(td)
            family_map = json.loads((root / "family_map.json").read_text(encoding="utf-8"))
            manifest = [json.loads(line) for line in (root / "synthetic_manifest.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(summary["families"], 5)
        self.assertEqual(summary["events"], 40)
        self.assertEqual(len(family_map), 5)
        self.assertEqual(len(manifest), 40)
        self.assertTrue(all(item["label_class"] == "RULE_PREFERRED" for item in manifest))
        self.assertTrue(all(item["teacher_gold"] is False for item in manifest))


if __name__ == "__main__":
    unittest.main()
