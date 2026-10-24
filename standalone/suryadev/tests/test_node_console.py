"""Node Control v9 UI contract: truthful evidence and no model requirement."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.scripts=[]
        self.anchors=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if "id" in d:self.ids.append(d["id"])
        if tag=="script" and d.get("src"):self.scripts.append(d["src"])
        if tag=="a" and d.get("href"):self.anchors.append(d["href"])


class NodeConsoleTests(unittest.TestCase):
    def test_homepage_is_clean_console_with_unmodified_advanced_evidence(self):
        html=(ROOT/"node-console.html").read_text(encoding="utf-8")
        p=Tags();p.feed(html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        for name in ("worker-state","action-status","learning-model",
                     "stat-queued","job-list","job-dialog","health-grid","core-status"):
            self.assertIn(name,p.ids)
        self.assertIn("/advanced",p.anchors)
        self.assertIn("/dashboard-api.js",p.scripts)
        self.assertIn("/node-console.js",p.scripts)
        self.assertNotIn('id="video-auto-url"',html)
        self.assertNotIn('id="learning-enable-sources"',html)
        self.assertEqual(html.count('<option value="collector"'),1)
        self.assertTrue((ROOT/"dashboard.html").is_file())

    def test_live_only_read_api_and_csrf_mutations(self):
        js=(ROOT/"node-console.js").read_text(encoding="utf-8")
        server=(ROOT/"suryadev_extras.py").read_text(encoding="utf-8")
        installer=(ROOT/"install-windows.ps1").read_text(encoding="utf-8")
        verifier=(ROOT/"verify_runtime_package.py").read_text(encoding="utf-8")
        self.assertIn('window.suryadevRead(path)',js)
        for endpoint in ("/api/learning/control","/api/operations","/api/live",
                         "/api/tasks?","/api/tasks/","/api/operator/settings"):
            self.assertIn(endpoint,js)
        self.assertIn('"X-SURYADEV-CSRF":state.csrf',js)
        self.assertIn('method:"POST"',js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("ollama pull",js)
        self.assertNotIn("localStorage",js)
        self.assertIn('"/": "node-console.html"',server)
        self.assertIn('"/advanced": "dashboard.html"',server)
        self.assertIn('"/node-console.js": "node-console.js"',server)
        self.assertIn("'node-console.js'",installer)
        self.assertIn('"node-console.js"',verifier)

    def test_old_advanced_console_is_in_browser_smoke(self):
        smoke=(ROOT/"dashboard_ui_smoke.py").read_text(encoding="utf-8")
        self.assertIn("browser_node_console_check",smoke)
        self.assertIn("/advanced",smoke)
        self.assertIn("SURYADEV_NODE_CONTROL_UI_REPORT",smoke)


if __name__ == "__main__":
    unittest.main()
