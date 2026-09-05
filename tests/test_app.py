import tempfile
import unittest
from pathlib import Path

from core import is_youtube_url, safe_folder_name, scene_frame_targets, unique_output_folder


class AppHelpersTest(unittest.TestCase):
    def test_accepts_youtube_urls(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(is_youtube_url("https://youtu.be/abc"))

    def test_rejects_lookalike_urls(self):
        self.assertFalse(is_youtube_url("https://youtube.com.example.org/watch?v=abc"))
        self.assertFalse(is_youtube_url("not a url"))

    def test_safe_folder_name(self):
        self.assertEqual(safe_folder_name('An: invalid / title?', "abc123"), "An_ invalid _ title_ [abc123]")

    def test_scene_first_and_last_targets(self):
        targets = scene_frame_targets([(0, 10), (10, 25), (25, 26)])
        self.assertEqual(targets[0], ["scene_0001_first.jpg"])
        self.assertEqual(targets[9], ["scene_0001_last.jpg"])
        self.assertEqual(targets[10], ["scene_0002_first.jpg"])
        self.assertEqual(targets[24], ["scene_0002_last.jpg"])
        self.assertEqual(targets[25], ["scene_0003_first.jpg", "scene_0003_last.jpg"])

    def test_rejects_invalid_scene_ranges(self):
        with self.assertRaises(ValueError):
            scene_frame_targets([(5, 5)])

    def test_unique_output_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            (parent / "Video").mkdir()
            self.assertEqual(unique_output_folder(parent, "Video"), parent / "Video (2)")


if __name__ == "__main__":
    unittest.main()
