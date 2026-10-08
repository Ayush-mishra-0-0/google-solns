"""Unit tests that run without credentials, network, Manim or an ffmpeg binary."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autochannel.pipeline import read_config, validate_storyboard, verify_video
from autochannel.research import topic_score


def sample_story():
    beats = []
    styles = ["concept", "comparison", "graph", "equation", "timeline"]
    for style in styles:
        beat = {
            "heading": "A useful mathematical idea",
            "body": "Understand the intuition before calculating anything.",
            "narration": "This visual explains the intuition carefully before we work through a concrete example and connect the ideas together.",
            "layout": style,
        }
        if style == "comparison":
            beat.update(left="Before transformation", right="After transformation")
        if style == "graph":
            beat["curve"] = "sin"
        if style == "equation":
            beat["equation"] = r"\sin(x)+\cos(x)"
        if style == "timeline":
            beat["steps"] = ["Intuition", "Derivation", "Application"]
        beats.append(beat)
    return {
        "title": "Five ways to understand a difficult math concept",
        "description": "A visual, step-by-step learning journey with a concrete example and practical intuition.",
        "beats": beats,
    }


class ValidationTests(unittest.TestCase):
    def test_accepts_diverse_valid_story(self):
        self.assertEqual(validate_storyboard(sample_story())["beats"][2]["curve"], "sin")

    def test_requires_three_templates(self):
        data = sample_story()
        for beat in data["beats"]:
            beat["layout"] = "concept"
        with self.assertRaisesRegex(ValueError, "repetitive"):
            validate_storyboard(data)

    def test_rejects_unsafe_manim_tex(self):
        data = sample_story()
        data["beats"][3]["equation"] = r"\input{secret.txt}"
        with self.assertRaisesRegex(ValueError, "unsafe"):
            validate_storyboard(data)

    def test_rejects_unbounded_narration(self):
        data = sample_story()
        data["beats"][0]["narration"] = "n" * 851
        with self.assertRaisesRegex(ValueError, "narration"):
            validate_storyboard(data)

    def test_invalid_graph_function(self):
        data = sample_story()
        data["beats"][2]["curve"] = "__import__('os').system('echo bad')"
        with self.assertRaisesRegex(ValueError, "curve"):
            validate_storyboard(data)

    def test_validates_channel_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.json"
            p.write_text(json.dumps({"channel_id": "wrong",
                                     "topic_seeds": ["calculus"]}))
            with self.assertRaisesRegex(ValueError, "channel_id"):
                read_config(p)

    def test_topic_novelty_penalizes_near_duplicates(self):
        signals = [{"views_per_day": 1000.0}]
        novel = topic_score("Bayes theorem", signals, [])
        repeated = topic_score("Bayes theorem", signals, ["Bayes theorem"])
        self.assertGreater(novel, repeated)

    @patch("autochannel.pipeline.probe")
    def test_requires_audio_stream(self, probe):
        data = sample_story()
        probe.return_value = {
            "format": {"duration": "100"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "final.mp4"
            file.write_bytes(b"0" * 150_000)
            with self.assertRaisesRegex(ValueError, "Audio track missing"):
                verify_video(file, data)


if __name__ == "__main__":
    unittest.main()
