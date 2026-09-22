from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import tempfile
import threading
import unittest
import zipfile

from krishna_core.privacy_guardian.browser import (
    compare_browser_reports,
    local_fingerprint_identifier,
    summarize_browser_observation,
)
from krishna_core.privacy_guardian.guardian import PrivacyGuardian
from krishna_core.privacy_guardian.mobile import basic_apk_privacy_audit
from krishna_core.privacy_guardian.policy import evaluate_release_gate
from krishna_core.privacy_guardian.regression import compare_reports
from krishna_core.privacy_guardian.store import PrivacyEvidenceStore
from krishna_core.privacy_guardian.tracking import clean_tracking_url
from krishna_core.privacy_guardian.web_security import audit_web_endpoint


class _PrivacyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/plain")
        self.send_header("Content-Security-Policy","default-src 'self'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Cross-Origin-Opener-Policy","same-origin")
        self.send_header("Set-Cookie","sid=super-secret-test-value; HttpOnly; SameSite=Lax")
        self.end_headers()
        self.wfile.write(b"privacy-test")
    def log_message(self,fmt,*args):
        pass


class _FakeBrowser:
    def privacy_probe(self,url="about:blank",profile="BASELINE"):
        observation={
            "userAgent":"FakeBrowser/1",
            "userAgentData":{"brands":[{"brand":"Fake","version":"1"}],"mobile":False,"platform":"Windows"},
            "language":"en-US","languages":["en-US"],"platform":"Win32","timezone":"Asia/Kolkata",
            "screen":{"width":1920,"height":1080,"availWidth":1920,"availHeight":1040,"pixelRatio":1,"colorDepth":24,"pixelDepth":24},
            "hardwareConcurrency":8,"deviceMemory":8,"maxTouchPoints":0,
            "webgl":{"available":True,"renderer":"Fake GPU","vendor":"Fake Vendor"},
            "canvas":"data:image/png;base64,AAAA",
            "audio":{"available":True,"sample":"1.2345"},
            "domRect":{"width":123.45,"height":67.89},
            "textMetrics":{"width":100.25},
            "permissions":{"camera":"prompt","microphone":"prompt","geolocation":"denied"},
            "storage":{"localStorage":True,"sessionStorage":True,"indexedDB":True},
            "gpc":True,"dnt":None,"webdriver":True,
            "voices":[],"plugins":[],"mimeTypes":[],"supportedApis":{"webgl":True},
        }
        return summarize_browser_observation(
            observation,profile=profile,url=url,
            webrtc={"available":True,"candidateTypes":["host"],"candidateCount":1,
                    "hostExposed":True,"publicCandidateExposed":False,
                    "relayObserved":False,"mdnsMasked":True,
                    "rawCandidateValuesStored":False},
            request_urls=[url],
        ) | {"temporary_profile":True,"elapsed_ms":1,"request_count":1}


class PrivacyGuardianTests(unittest.TestCase):
    def test_tracking_cleaner_removes_only_known_tracking_parameters(self):
        out=clean_tracking_url("https://example.com/p?id=42&utm_source=x&fbclid=y&next=%2Fhome&custom=z")
        self.assertTrue(out["changed"])
        self.assertIn("id=42",out["after"])
        self.assertIn("next=%2Fhome",out["after"])
        self.assertIn("custom=z",out["after"])
        self.assertNotIn("utm_source",out["after"])
        self.assertNotIn("fbclid",out["after"])
        self.assertTrue(out["preserved_unknown"])

    def test_store_redacts_secrets_ips_and_sensitive_keys(self):
        with tempfile.TemporaryDirectory() as td:
            store=PrivacyEvidenceStore(td)
            safe=store.sanitize({
                "token":"abc123456789",
                "public_ip":"198.51.100.10",
                "note":"token=super-secret-value from 203.0.113.8",
                "nested":{"password":"dont-store-me"},
            })
            blob=json.dumps(safe)
            self.assertNotIn("abc123456789",blob)
            self.assertNotIn("198.51.100.10",blob)
            self.assertNotIn("super-secret-value",blob)
            self.assertNotIn("dont-store-me",blob)
            self.assertIn("REDACTED",blob)

    def test_local_fingerprint_never_uploads_and_profile_compare_is_descriptive(self):
        obs={
            "userAgent":"X","platform":"Win32","timezone":"UTC","screen":{"width":1},
            "webgl":{"available":True,"renderer":"GPU"},"canvas":"abc",
            "audio":{"available":True,"sample":"1"},"domRect":{"width":1},"textMetrics":{"width":2},
        }
        a={"fingerprint":local_fingerprint_identifier(obs),"browser":{"x":1},"surfaces":{},"permissions":{},"storage":{},"webrtc":{}}
        b={"fingerprint":local_fingerprint_identifier(obs),"browser":{"x":1},"surfaces":{},"permissions":{},"storage":{},"webrtc":{}}
        self.assertFalse(a["fingerprint"]["uploaded"])
        result=compare_browser_reports(a,b)
        self.assertTrue(result["same_local_fingerprint"])
        self.assertEqual(result["linkability"],"HIGH LINKABILITY")
        self.assertIn("does not prove",result["interpretation"])

    def test_browser_summary_does_not_retain_raw_webrtc_candidates(self):
        obs={
            "userAgent":"X","language":"en","languages":["en"],"platform":"Win32","timezone":"UTC",
            "screen":{"width":100,"height":100},"hardwareConcurrency":4,"deviceMemory":4,"maxTouchPoints":0,
            "webgl":{"available":False},"canvas":None,"audio":{"available":False},
            "permissions":{},"storage":{},"voices":[],"plugins":[],"mimeTypes":[],"supportedApis":{},
        }
        out=summarize_browser_observation(
            obs,profile="INCOGNITO",url="https://example.com",
            webrtc={"available":True,"candidateTypes":["srflx"],"candidateCount":1,
                    "hostExposed":False,"publicCandidateExposed":True,
                    "relayObserved":False,"mdnsMasked":False,
                    "candidate":"candidate:1 1 UDP 1 198.51.100.4 123 typ srflx"},
            request_urls=["https://example.com/a","https://tracker.invalid/x"],
        )
        encoded=json.dumps(out)
        self.assertNotIn("198.51.100.4",encoded)
        self.assertNotIn("candidate:1",encoded)
        self.assertEqual(out["webrtc"]["candidateTypes"],["srflx"])

    def test_web_endpoint_audit_executes_real_http_request_and_hides_cookie_value(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),_PrivacyHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/"
            out=audit_web_endpoint(url,owned=True)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(out["status"],200)
        findings={x["test"]:x for x in out["findings"]}
        self.assertEqual(findings["web.csp"]["state"],"enabled")
        self.assertEqual(findings["web.referrer_policy"]["state"],"enabled")
        cookies=findings["web.cookies"]["evidence"]["cookies"]
        self.assertEqual(cookies[0]["name"],"sid")
        self.assertFalse(cookies[0]["value_included"])
        self.assertNotIn("super-secret-test-value",json.dumps(out))

    def test_mobile_static_audit_executes_against_apk_zip(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/"krishna-test.apk"
            with zipfile.ZipFile(apk,"w") as z:
                z.writestr("classes.dex",b"xxxx com/facebook/appevents yyyy http://tracker.example/path zzzz")
                z.writestr("AndroidManifest.xml",b"binary-placeholder")
            out=basic_apk_privacy_audit(apk)
            findings={x["test"]:x for x in out["findings"]}
            self.assertIn("facebook_sdk",findings["mobile.trackers.static"]["evidence"]["tracker_signatures"])
            self.assertIn("tracker.example",findings["mobile.cleartext_urls"]["evidence"]["cleartext_hosts"])
            self.assertTrue(out["apk_sha256"])

    def test_regression_records_methodology_and_worsening(self):
        previous={"audit_id":"a","test_suite_version":"v1","profile":"BASELINE","findings":[
            {"test":"browser.webrtc","state":"observed","risk_class":"LOW EXPOSURE"}
        ]}
        current={"audit_id":"b","test_suite_version":"v1","profile":"BASELINE","findings":[
            {"test":"browser.webrtc","state":"observed","risk_class":"MODERATE EXPOSURE"}
        ]}
        result=compare_reports(previous,current,mission_id="m1",configuration_change="browser update")
        self.assertTrue(result["compatible_methodology"])
        self.assertEqual(result["regression_count"],1)
        self.assertEqual(result["regressions"][0]["mission_id"],"m1")

    def test_release_gate_requires_policy_tests_but_does_not_block_informational_findings(self):
        report={"target_type":"web","findings":[
            {"test":"web.https","state":"enabled","risk_class":"LOW EXPOSURE"},
            {"test":"web.hsts","state":"missing","risk_class":"MODERATE EXPOSURE"},
            {"test":"web.csp","state":"enabled","risk_class":"LOW EXPOSURE"},
            {"test":"web.referrer_policy","state":"enabled","risk_class":"LOW EXPOSURE"},
            {"test":"web.permissions_policy","state":"enabled","risk_class":"LOW EXPOSURE"},
            {"test":"web.x_content_type_options","state":"nosniff","risk_class":"LOW EXPOSURE"},
            {"test":"web.frame_protection","state":"enabled","risk_class":"LOW EXPOSURE"},
            {"test":"web.cookies","state":"observed","risk_class":"LOW EXPOSURE"},
        ]}
        gate=evaluate_release_gate(report,"WEB_RELEASE")
        self.assertTrue(gate["passed"])
        report["findings"][1]["state"]="failed"
        self.assertFalse(evaluate_release_gate(report,"WEB_RELEASE")["passed"])

    def test_guardian_binds_fake_browser_stores_redacted_history_and_emits_status(self):
        with tempfile.TemporaryDirectory() as td:
            guardian=PrivacyGuardian(td,browser=_FakeBrowser())
            report=guardian.audit_browser(url="https://example.com",profile="BASELINE")
            self.assertEqual(report["target_type"],"browser")
            self.assertTrue(report["history_storage"]["stored"])
            self.assertTrue(report["metadata"]["temporary_profile"])
            status=guardian.status()
            self.assertTrue(status["internal_only"])
            self.assertFalse(status["main_menu"])
            self.assertFalse(status["anti_detection"])
            self.assertTrue(status["implemented"]["fingerprint_surface_inspector"])
            self.assertIn("requires owner-controlled external DNS",status["conditional_or_external"]["dns_leak_probe"])


if __name__=="__main__":
    unittest.main()
