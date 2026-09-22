import os
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from krishna_core.browser_operator import BrowserOperator


@unittest.skipUnless(os.getenv("KRISHNA_PROJECT_PERFECTION_BROWSER_E2E")=="1","real browser E2E disabled")
class ProjectPerfectionBrowserE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        root=Path(cls.tmp.name)
        (root/"index.html").write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QA Home</title>
<style>body{font-family:sans-serif}main{max-width:800px;margin:auto}.row{display:flex;gap:12px}</style></head>
<body><main><h1>QA Home</h1><a href="/second.html">Second</a>
<label>Name <input id="name" name="name"></label>
<label>Choice <select id="choice"><option value="a">A</option><option value="b">B</option></select></label>
<div class="row"><button id="ping" onclick="document.getElementById('out').textContent='pong'">Ping</button></div>
<p id="out">ready</p></main></body></html>""",encoding="utf-8")
        (root/"second.html").write_text("""<!doctype html><html lang="en"><head><title>Second</title></head>
<body><main><h1>Second</h1><a href="/index.html">Home</a><button>Okay</button></main></body></html>""",encoding="utf-8")
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,format,*args):pass
        handler=partial(Quiet,directory=str(root))
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f"http://127.0.0.1:{cls.server.server_address[1]}/index.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3);cls.tmp.cleanup()

    def test_real_perfection_browser_stack(self):
        browser=BrowserOperator(headless=True,timeout_ms=10000)
        crawl=browser.crawl_application(self.url,max_pages=5,max_depth=2,max_controls_per_page=20)
        self.assertTrue(crawl["ok"],crawl)
        self.assertGreaterEqual(crawl["visited_pages"],2)
        self.assertGreaterEqual(sum(x.get("field_count",0) for x in crawl["nodes"]),2)

        scan=browser.perfection_scan(self.url,viewports=[390,1440])
        self.assertTrue(scan["ok"],scan)
        self.assertEqual(len(scan["viewports"]),2)
        self.assertGreater(len(scan["viewports"][0]["geometry"]),0)

        a11y=browser.accessibility_scan(self.url)
        self.assertTrue(a11y["passed"],a11y)
        self.assertTrue(a11y["axe"]["available"],a11y)

        chaos=browser.chaos_scan(self.url)
        self.assertTrue(chaos["passed"],chaos)
        self.assertTrue(any(x["name"]=="offline_reload" for x in chaos["scenarios"]))


if __name__=="__main__":
    unittest.main()
