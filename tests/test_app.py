import unittest
from pathlib import Path

from core import is_youtube_url, make_ffmpeg_command, safe_folder_name


class AppHelpersTest(unittest.TestCase):
    def test_accepts_youtube_urls(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(is_youtube_url("https://youtu.be/abc"))
        self.assertTrue(is_youtube_url("https://music.youtube.com/watch?v=abc"))

    def test_rejects_lookalike_and_non_http_urls(self):
        self.assertFalse(is_youtube_url("https://youtube.com.example.org/watch?v=abc"))
        self.assertFalse(is_youtube_url("file://youtube.com/video"))
        self.assertFalse(is_youtube_url("not a url"))

    def test_safe_folder_name(self):
        self.assertEqual(safe_folder_name('An: invalid / title?', "abc123"), "An_ invalid _ title_ [abc123]")

    def test_ffmpeg_command_exports_one_jpg_per_second(self):
        command = make_ffmpeg_command("ffmpeg.exe", Path("video.mp4"), Path("frame_%06d.jpg"))
        self.assertIn("fps=1", command)
        self.assertIn("-start_number", command)
        self.assertEqual(command[-1], "frame_%06d.jpg")


if __name__ == "__main__":
    unittest.main()
