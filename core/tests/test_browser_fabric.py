import os
import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.browser_fabric import BrowserAdapterRegistry, GarudanetraBrowserFabric
from krishna_core.garudanetra_session import BrowserSession, GarudanetraSessionManager


class BrowserFabricTests(unittest.TestCase):
    def test_adapter_registry_keeps_playwright_canonical(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ,{
            "KRISHNA_BROWSER_HARNESS_CMD":"",
            "KRISHNA_BROWSER_VISION_RECOVERY_CMD":"",
            "KRISHNA_AGENT_BROWSER_CMD":"",
            "KRISHNA_BROWSERCODE_CMD":"",
            "KRISHNA_OPENDEVBROWSER_CMD":"",
            "KRISHNA_RUSTWRIGHT_CMD":"",
            "KRISHNA_LUCARNE_CMD":"",
            "KRISHNA_PROMPTWRIGHT_CMD":"",
            "KRISHNA_SKYVERN_CMD":"",
            "KRISHNA_RRWEB_CMD":"",
            "KRISHNA_CEREON_BROWSER_ENDPOINT":"",
        },clear=False):
            status=BrowserAdapterRegistry(Path(td)).status()
            self.assertEqual(status["canonical"],"playwright")
            names={x["name"] for x in status["adapters"]}
            for name in (
                "playwright","browser_harness","agent_browser","browsercode",
                "opendevbrowser","rustwright","lucarne","promptwright","skyvern",
                "rrweb","browser_use","cereon_browser_operator","vision_recovery_bridge",
            ):
                self.assertIn(name,names)
            self.assertIn("one Garudanetra fabric",status["policy"])

    def test_fabric_exposes_one_session_authority(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraBrowserFabric(Path(td))
            self.assertIs(fabric.sessions,self_ref:=fabric.sessions)
            status=fabric.status()
            self.assertEqual(status["owner"],"garudanetra-browser-fabric")
            self.assertEqual(status["canonical_engine"],"playwright")
            self.assertIn("semantic_snapshot_refs",status["capabilities"])
            self.assertIn("cdp_screencast",status["capabilities"])
            self.assertIn("bounded_replay",status["capabilities"])
            self.assertIs(self_ref,fabric.sessions)

    def test_semantic_refs_frame_metadata_and_replay_gate_without_browser(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(Path(td))
            session=BrowserSession("s","KRISHNA","https://example.com")
            session.semantic_revision=2
            session.semantic_items=[{"ref":"e1","selector":"#go","role":"button","name":"Go"}]
            session.frame=b"abc"
            session.frame_mime="image/jpeg"
            session.frame_seq=7
            session.stream_mode="cdp_screencast"
            session.recording=[
                {"action":"scroll","payload":{"dy":100},"status":"ok"},
                {"action":"click","payload":{"ref":"e1"},"status":"ok"},
                {"action":"fill","payload":{"ref":"e1","value":"[REDACTED]"},"status":"ok"},
            ]
            m._sessions["s"]=session
            m._commands["s"]=queue.Queue(maxsize=100)

            semantic=m.semantic_snapshot("s")
            self.assertEqual(semantic["revision"],2)
            self.assertEqual(semantic["items"][0]["ref"],"e1")
            frame=m.frame_info("s")
            self.assertEqual(frame["mime"],"image/jpeg")
            self.assertEqual(frame["seq"],7)

            gated=m.replay("s",approved=False)
            self.assertEqual(gated["queued"],["scroll"])
            self.assertTrue(any(x["action"]=="click" for x in gated["blocked"]))
            approved=m.replay("s",steps=[{"action":"click","payload":{"ref":"e1"},"status":"ok"}],approved=True)
            self.assertEqual(approved["queued"],["click"])

    def test_recording_redacts_entered_values_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(Path(td))
            session=BrowserSession("s","KRISHNA","https://example.com")
            m._sessions["s"]=session
            m._commands["s"]=queue.Queue()
            m._record_action(session,"fill",{"ref":"e1","value":"secret-value"},"ok")
            m._record_action(session,"fill",{"ref":"e1","value":"public-value","remember_value":True},"ok")
            rows=m.recording("s")["steps"]
            self.assertEqual(rows[0]["payload"]["value"],"[REDACTED]")
            self.assertEqual(rows[1]["payload"]["value"],"public-value")
            self.assertNotIn("remember_value",rows[1]["payload"])


if __name__=="__main__":
    unittest.main()
