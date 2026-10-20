import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev import Library, TextExtractor, validate_url

class StandaloneTests(unittest.TestCase):
    def test_html_extraction(self):
        p = TextExtractor()
        p.feed("<title>Test</title><h1>Useful lesson</h1><script>secret</script>")
        self.assertEqual(p.title, "Test")
        self.assertIn("Useful lesson", " ".join(p.parts))
        self.assertNotIn("secret", " ".join(p.parts))

    def test_reject_unsafe_urls(self):
        for url in ["http://example.com", "https://127.0.0.1/", "file:///etc/passwd",
                    "https://localhost/", "https://user:pass@example.com/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    @patch("suryadev.validate_url", return_value="https://example.com/doc")
    @patch("suryadev_garudanetra.render_website", return_value=("Example", "A test research finding.", {"kind":"website","coverage_status":"garudanetra_rendered_text_unverified","browser_tab_opened":True,"full_rendered_page_verified":False}))
    def test_persist_and_recover(self, fetch, validate):
        with tempfile.TemporaryDirectory() as temp:
            lib = Library(temp)
            job_id = lib.add("https://example.com/doc")
            self.assertEqual(lib.run_next(use_ollama=False)["status"], "done")
            self.assertEqual(lib.stats()["done"], 1)
            self.assertEqual(len(lib.search("test research")), 1)
            lib.db.close()
            reopened = Library(temp)
            self.assertEqual(len(reopened.search("test research")), 1)
            reopened.db.close()

    @patch("suryadev.validate_url", return_value="https://example.com/doc")
    @patch("suryadev_garudanetra.render_website", side_effect=ValueError("blocked"))
    def test_failure_recorded(self, fetch, validate):
        with tempfile.TemporaryDirectory() as temp:
            lib = Library(temp)
            lib.add("https://example.com/doc")
            self.assertEqual(lib.run_next(use_ollama=False)["status"], "failed")
            self.assertEqual(lib.stats()["failed"], 1)
            lib.db.close()

if __name__ == "__main__":
    unittest.main()
