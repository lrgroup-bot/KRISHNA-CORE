"""Real local Chromium integration proof; skipped only when Playwright is absent.

Never reaches the internet: a private 127.0.0.1 HTTPServer hosts the test UI.
The CI privacy-browser job installs Chromium before executing this module.
"""
import base64
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
import sys

# Core CI runs with PYTHONPATH=core; root tools live alongside core/.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.sudarshan_ui_guardian import run_browser
from tools.sudarshan_evidence_archive import load, verify


class LocalPage(BaseHTTPRequestHandler):
    def do_GET(self):
        suffix='<script>console.error("intentional UI test failure")</script>' if self.path=='/error' else ''
        html=(
            '<!doctype html><html><body>'
            '<button id="go" onclick="document.getElementById(\'result\').textContent=\'Clicked!\'">'
            'Go</button><p id="result">Idle</p>'+suffix+'</body></html>'
        ).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self,*args):
        pass


class RealChromiumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = os.getenv('KRISHNA_SUDARSHAN_CHROMIUM_REQUIRED') == '1'
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            if required:
                raise RuntimeError('Required Chromium test dependency is missing') from error
            raise unittest.SkipTest('Playwright unavailable: browser test NOT executed') from error
        with sync_playwright() as playwright:
            browser_executable = Path(playwright.chromium.executable_path)
        if not browser_executable.is_file():
            if required:
                raise RuntimeError('Required Chromium browser binary is not installed')
            raise unittest.SkipTest('Chromium absent: dedicated browser E2E is required')
        cls.web=ThreadingHTTPServer(('127.0.0.1',0),LocalPage)
        cls.thread=Thread(target=cls.web.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.web.shutdown()
        cls.web.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.url='http://127.0.0.1:%d/' % self.web.server_address[1]

    def test_click_assert_and_archive_real_screenshot(self):
        plan={'url':self.url,'steps':[
            {'action':'click','selector':'#go'},
            {'action':'expect_text','selector':'#result','value':'Clicked!'},
            {'action':'expect_count','selector':'button','value':1}]}
        result=run_browser(plan,authorized=True,evidence_root=self.root,project_id='test-project')
        self.assertEqual(result.status,'passed',result.summary)
        self.assertTrue(verify(self.root,'test-project','UI_GUARDIAN',result.evidence_id))
        artifact=load(self.root,'test-project','UI_GUARDIAN',result.evidence_id)
        self.assertEqual(artifact['step_count'],3)
        self.assertEqual(artifact['service_workers'],'block')
        self.assertTrue(base64.b64decode(artifact['screenshot_png_base64']).startswith(b'\x89PNG'))

    def test_console_errors_fail_closed(self):
        plan={'url':self.url+'error',
              'steps':[{'action':'expect_visible','selector':'body'}]}
        result=run_browser(plan,authorized=True)
        self.assertEqual(result.status,'failed')
        self.assertFalse(result.evidence_id)

if __name__=='__main__':
    unittest.main()
