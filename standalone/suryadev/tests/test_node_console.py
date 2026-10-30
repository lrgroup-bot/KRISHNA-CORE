"""One SURYADEV Learning Intelligence frontend, with merged node controls.

No duplicate dashboard on either URL: / and /advanced use the same HTML and
API-backed worker. Historical video-review links remain valid.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.scripts = []
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if "id" in fields:
            self.ids.append(fields["id"])
        if tag == "script" and fields.get("src"):
            self.scripts.append(fields["src"])
        if tag == "a" and fields.get("href"):
            self.anchors.append(fields["href"])


class UnifiedLearningDashboardTests(unittest.TestCase):
    def test_single_learning_intelligence_ui_keeps_existing_sections(self):
        html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
        p = Tags()
        p.feed(html)
        self.assertEqual(len(p.ids), len(set(p.ids)))
        for name in ("learning-start", "learning-stop", "learning-model",
                     "garudanetra", "assignments", "video-review",
                     "books-evidence", "book-ledger-list", "sources",
                     "date-center", "server-settings-dialog",
                     "storage-settings-dialog", "node-control-profile",
                     "node-control-plan", "node-control-pairing",
                     "node-control-capacity", "netra-total-capacity"):
            self.assertIn(name, p.ids)
        for anchor in ("#video-review", "#books-evidence", "#date-center"):
            self.assertIn(anchor, p.anchors)
        self.assertIn("/dashboard-api.js", p.scripts)
        self.assertIn("/dashboard-learning.js", p.scripts)
        self.assertNotIn("/node-console.js", p.scripts)
        self.assertEqual(html.count('id="learning-start"'), 1)
        self.assertEqual(html.count('id="learning-model"'), 1)
        self.assertNotIn('id="video-auto-url"', html)

    def test_routes_alias_same_html_with_no_node_console_route(self):
        server = (ROOT / "suryadev_extras.py").read_text(encoding="utf-8")
        self.assertIn('"/": "dashboard.html"', server)
        self.assertIn('"/advanced": "dashboard.html"', server)
        self.assertIn('"/dashboard.html": "dashboard.html"', server)
        self.assertNotIn('"/": "node-console.html"', server)
        self.assertNotIn('"/node-console.js": "node-console.js"', server)
        self.assertNotIn('"/node-console.css": "node-console.css"', server)
        self.assertIn('"has_single_learning_intelligence_frontend": True', server)

    def test_merged_worker_controls_use_original_csrf_and_read_api(self):
        js = (ROOT / "dashboard-learning.js").read_text(encoding="utf-8")
        netra = (ROOT / "dashboard-garudanetra.js").read_text(encoding="utf-8")
        self.assertIn('window.suryadevRead("/api/learning/control")', js)
        self.assertIn('"/api/operator/learning/start"', js)
        self.assertIn('"/api/operator/learning/stop"', js)
        self.assertIn('"X-SURYADEV-CSRF":token', js)
        self.assertIn('node-control-profile', js)
        self.assertIn('node-control-pairing', js)
        self.assertIn('node-control-capacity', netra)
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('localStorage', js)
        self.assertNotIn('ollama pull', js)

    def test_real_browser_smoke_checks_both_aliases(self):
        smoke = (ROOT / "dashboard_ui_smoke.py").read_text(encoding="utf-8")
        self.assertIn('for route in ("/", "/advanced"):', smoke)
        self.assertIn('single_learning_intelligence_frontend', smoke)
        self.assertIn('browser_video_review_check', smoke)


if __name__ == "__main__":
    unittest.main()
