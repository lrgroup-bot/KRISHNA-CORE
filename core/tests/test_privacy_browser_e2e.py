"""Real Playwright privacy regression against the live KRISHNA Core route.

Skipped during normal unit discovery. The dedicated CI job enables it after installing
Playwright Chromium so Privacy Guardian is not declared browser-ready from mocks alone.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


@unittest.skipUnless(os.getenv("KRISHNA_PRIVACY_BROWSER_E2E")=="1","dedicated Playwright privacy E2E only")
class PrivacyBrowserE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));cls.port=sock.getsockname()[1]
        env=dict(os.environ,
                 KRISHNA_DB=str(cls.root/"core.db"),
                 KRISHNA_HOST="127.0.0.1",
                 KRISHNA_PORT=str(cls.port),
                 KRISHNA_ALLOW_ACTIONS="0")
        cls.log=(cls.root/"privacy-e2e-server.log").open("w")
        cls.proc=subprocess.Popen(
            [sys.executable,"-m","krishna_core.server"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,stdout=cls.log,stderr=cls.log,
        )
        for _ in range(160):
            try:
                if cls.call("/health")[0]==200:break
            except OSError:time.sleep(.1)
        else:
            cls.log.flush()
            details=(cls.root/"privacy-e2e-server.log").read_text(encoding="utf-8",errors="replace")[-8000:]
            raise RuntimeError("privacy E2E Core failed to start\n"+details)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:cls.proc.kill()
        cls.log.close();cls.temp.cleanup()

    @classmethod
    def call(cls,path,data=None):
        req=urllib.request.Request(
            f"http://127.0.0.1:{cls.port}"+path,
            data=None if data is None else json.dumps(data).encode(),
            headers={"Content-Type":"application/json"},
        )
        try:resp=urllib.request.urlopen(req,timeout=40)
        except urllib.error.HTTPError as exc:resp=exc
        with resp:
            return resp.status,json.loads(resp.read().decode())

    def test_real_browser_privacy_route_against_krishna_dashboard(self):
        status=self.call("/api/kabach/privacy/status")[1]
        self.assertTrue(status["browser_runtime_bound"])

        code,report=self.call("/api/kabach/privacy/audit",{
            "target_type":"browser",
            "url":f"http://127.0.0.1:{self.port}/dashboard",
            "profile":"FRESH_PROFILE",
            "policy":"STRICT",
        })
        self.assertEqual(code,200)
        self.assertEqual(report["target_type"],"browser")
        self.assertTrue(report["metadata"]["temporary_profile"])
        self.assertTrue(report["metadata"]["fingerprint"]["identifier"])
        self.assertFalse(report["metadata"]["fingerprint"]["uploaded"])
        tests={x["test"] for x in report["findings"]}
        self.assertIn("browser.canvas",tests)
        self.assertIn("browser.webgl",tests)
        self.assertIn("browser.webrtc",tests)
        self.assertIn("browser.permissions",tests)
        self.assertIn("browser.storage",tests)
        raw=json.dumps(report)
        self.assertNotIn("candidate:",raw)

        third=next(x for x in report["findings"] if x["test"]=="browser.third_party_requests")
        self.assertEqual(third["evidence"]["third_party_domains"],[])

        code,baseline=self.call("/api/kabach/privacy/baseline",{
            "name":"ci-live-dashboard","report":report
        })
        self.assertEqual(code,200);self.assertTrue(baseline["stored"])
        code,comparison=self.call("/api/kabach/privacy/compare",{
            "name":"ci-live-dashboard","report":report
        })
        self.assertEqual(code,200);self.assertEqual(comparison["regression_count"],0)


if __name__=="__main__":
    unittest.main()
