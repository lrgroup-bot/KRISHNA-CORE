"""One GitHub dashboard: no duplicated dates, video panels, or stale labels."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class _MarkupAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.date_inputs = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "input" and values.get("type") == "date":
            self.date_inputs += 1
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


class UnifiedFrontendContractTests(unittest.TestCase):
    def test_one_html_frontend_with_one_video_and_one_calendar(self):
        html = (ROOT/"dashboard.html").read_text(encoding="utf-8")
        page = _MarkupAudit()
        page.feed(html)
        self.assertEqual(page.date_inputs, 1)
        self.assertEqual(page.ids.count("date-main"), 1)
        self.assertEqual(page.ids.count("video-review"), 1)
        self.assertEqual(page.ids.count("book-ledger-list"), 1)
        self.assertEqual(page.ids.count("book-health"), 0)
        self.assertEqual(len(page.ids), len(set(page.ids)), "Duplicate DOM id detected")
        self.assertEqual(page.links.count("#video-review"), 1)
        self.assertEqual(page.links.count("#date-center"), 1)
        self.assertIn('src="/dashboard-api.js"', html)
        self.assertIn('id="ui-version"', html)
        self.assertNotIn("UI v6.9",html)
        for legacy in ("task-date", "diary-date", "date-today-main-copy",
                       "diary-clear", "diary-today", 'id="book-learning"'):
            self.assertNotIn(legacy, html)

    def test_dynamic_injection_removed_and_book_results_not_repeated(self):
        video = (ROOT/"dashboard-video.js").read_text(encoding="utf-8")
        base = (ROOT/"dashboard.js").read_text(encoding="utf-8")
        self.assertNotIn("section.innerHTML", video)
        self.assertNotIn("insertBefore(section", video)
        self.assertNotIn("nav.insertBefore", video)
        self.assertNotIn("source.append(bookCard)", base)
        self.assertNotIn("bookHealth.replaceChildren", base)
        self.assertIn('window.suryadevRead("/api/live"', base)
        self.assertIn('window.suryadevRead("/api/tasks?"', base)
        netra = (ROOT/"dashboard-garudanetra.js").read_text(encoding="utf-8")
        self.assertEqual(base.count('window.suryadevRead("/api/operations"'), 1)
        self.assertNotIn('window.suryadevRead("/api/operations"', netra)
        self.assertIn('new CustomEvent("suryadev:operations"', base)
        self.assertIn('addEventListener("suryadev:operations"', netra)

    def test_all_frontend_api_calls_share_read_only_retry_helper(self):
        api = (ROOT/"dashboard-api.js").read_text(encoding="utf-8")
        self.assertIn('window.suryadevRead = suryadevRead', api)
        self.assertIn('method !== "GET"', api)
        self.assertIn('attempt < 2', api)
        server = (ROOT/"suryadev_extras.py").read_text(encoding="utf-8")
        install = (ROOT/"install-windows.ps1").read_text(encoding="utf-8")
        self.assertIn('"/dashboard-api.js": "dashboard-api.js"', server)
        self.assertIn("'dashboard-api.js'", install)

    def test_stale_folder_copy_removed(self):
        for name in ("dashboard.html", "dashboard.js",
                     "dashboard-garudanetra.js", "dashboard-books.js"):
            content=(ROOT/name).read_text(encoding="utf-8")
            self.assertNotIn("this production data folder", content)
            self.assertNotIn("Your earlier three-line experiment", content)
            self.assertNotIn("separate test-data book", content)


if __name__ == "__main__":
    unittest.main()
