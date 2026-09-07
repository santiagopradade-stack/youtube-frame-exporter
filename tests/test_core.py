from pathlib import Path
import unittest

from core import VALID_INTERVALS, is_youtube_url, make_ffmpeg_command, safe_folder_name


class CoreTests(unittest.TestCase):
    def test_intervals_are_exact(self) -> None:
        self.assertEqual(VALID_INTERVALS, (1, 2, 4, 8, 16))

    def test_accepts_youtube_urls(self) -> None:
        for url in (
            "https://youtube.com/watch?v=abc",
            "https://www.youtube.com/watch?v=abc",
            "https://youtu.be/abc",
            "http://m.youtube.com/watch?v=abc",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_youtube_url(url))

    def test_rejects_other_urls(self) -> None:
        for url in ("", "youtube.com/watch?v=abc", "https://example.com/video", "file:///video.mp4"):
            with self.subTest(url=url):
                self.assertFalse(is_youtube_url(url))

    def test_safe_folder_name_removes_windows_characters(self) -> None:
        self.assertEqual(safe_folder_name('Vídeo: prueba?/"', "abc"), "Vídeo_ prueba___ [abc]")

    def test_ffmpeg_uses_selected_interval(self) -> None:
        command = make_ffmpeg_command(
            "ffmpeg.exe", Path("video.mp4"), Path("frame_%06d.jpg"), 16
        )
        self.assertIn("fps=1/16", command)

    def test_ffmpeg_rejects_unknown_interval(self) -> None:
        with self.assertRaises(ValueError):
            make_ffmpeg_command("ffmpeg.exe", Path("video.mp4"), Path("frame.jpg"), 32)


if __name__ == "__main__":
    unittest.main()
