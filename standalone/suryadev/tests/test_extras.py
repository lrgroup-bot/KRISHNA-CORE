import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from suryadev import Library
from suryadev_extras import parse_transcript, import_transcript

class ExtrasTests(unittest.TestCase):
    def test_srt(self):
        source = "1\n00:00:01,000 --> 00:00:02,000\nFirst lesson\n\n2\n00:00:03,000 --> 00:00:04,000\nSecond lesson"
        self.assertEqual(parse_transcript(source), "First lesson\nSecond lesson")

    def test_import_persist_and_dedupe(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "lesson.vtt"
            file.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nLearn Python", encoding="utf-8")
            lib = Library(Path(tmp) / "data")
            first = import_transcript(lib, file, use_ollama=False)
            self.assertEqual(first["status"], "done")
            self.assertIn("duplicate_of", import_transcript(lib, file, use_ollama=False))
            self.assertEqual(len(lib.search("Python")), 1)
            lib.db.close()
            again = Library(Path(tmp) / "data")
            self.assertEqual(len(again.search("Python")), 1)
            again.db.close()

    def test_reject_nontranscript(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "file.exe"
            file.write_text("x")
            lib = Library(Path(tmp) / "data")
            with self.assertRaises(ValueError):
                import_transcript(lib, file, use_ollama=False)
            lib.db.close()

if __name__ == "__main__":
    unittest.main()
