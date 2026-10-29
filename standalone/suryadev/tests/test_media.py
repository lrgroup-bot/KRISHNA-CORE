import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev_media import transcribe_file, youtube_subtitles, capture_page

class MediaSafetyTests(unittest.TestCase):
    def test_reject_unapproved_youtube_url(self):
        for url in ("http://youtube.com/watch?v=abc", "https://evil.example/watch?v=abc",
                    "file:///video.mp4"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                youtube_subtitles(url, output_dir="unused")

    def test_reject_unapproved_media(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "payload.exe"
            p.write_bytes(b"test")
            with self.assertRaises(ValueError):
                transcribe_file(p)

    @patch("suryadev_media.validate_url")
    def test_browser_requires_host_allowlist(self, validate):
        with self.assertRaises(ValueError):
            capture_page("https://example.com/", "capture.png", allow_hosts={"another.example"})

if __name__ == "__main__":
    unittest.main()
