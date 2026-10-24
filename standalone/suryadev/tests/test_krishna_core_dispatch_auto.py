"""KRISHNA should feed paired SURYADEV without per-task owner URL entry.

All tests run offline. They NEVER initiate a device pairing or trust the
candidate Core IP as authentication.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_feeder import read_plan, paired_core_source_allowed
from suryadev_dashboard_worker import DashboardWorkerControl
from suryadev_fleet_client import FleetClient
from suryadev_liveops import connection_indicators, atomic_json


class CoreDispatchTests(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.folder=Path(__file__).resolve().parents[1]
        self.plan=self.root/"learning-plan.json"
        self.plan.write_text(json.dumps({
            "approved_urls":["https://docs.python.org/3/library/asyncio.html"],
            "approved_feeds":[],"allowed_source_hosts":["docs.python.org"],
            "max_new_per_cycle":5,"max_queued":20,
        }),encoding="utf-8")

    def test_no_pairing_is_local_and_does_not_autostart_or_delegate(self):
        ctl=DashboardWorkerControl(self.root,self.folder)
        self.assertEqual(ctl.snapshot()["dispatch_mode"],"local_only")
        self.assertFalse(ctl.core_pairing()["ready"])
        with self.assertRaisesRegex(ValueError,"Pair KRISHNA"):
            ctl.set_core_delegation(True)
        self.assertFalse(read_plan(self.plan)["paired_core_host_delegation"])

    def test_validated_pairing_boots_one_fleet_worker_not_two(self):
        cfg=self.root/"core-mission-connection.json"
        cfg.write_text('{"schema":"test"}',encoding="utf-8")
        ctl=DashboardWorkerControl(self.root,self.folder)
        class FakeProcess:
            pid=9000
            def poll(self):return None
            def send_signal(self,sig):pass
        mock_config={"device_id":"suryadev-laptop","host":"192.168.0.100",
                     "port":8443,"fingerprint":"a"*64,"credential":"x"*64}
        try:
            with patch("suryadev_krishna_mission.load_config",return_value=mock_config):
                self.assertTrue(ctl.snapshot()["core_dispatch"]["ready"])
                with patch("suryadev_dashboard_worker.subprocess.Popen",return_value=FakeProcess()) as spawn:
                    result=ctl.start(model="qwen3.5:2b")
                    self.assertEqual(result["core_dispatch_mode"],"krishna_fleet")
                    args=spawn.call_args.args[0]
                    self.assertIn("--fleet-mode",args)
                    self.assertIn("--core-mission-config",args)
                    self.assertIn(str(ctl.root / 'core-mission-connection.json'),args)
                    with self.assertRaises(RuntimeError):
                        ctl.start(model="qwen3.5:2b")
                    self.assertEqual(spawn.call_count,1)
        finally:
            ctl.close()

    def test_delegation_once_only_for_existing_hosts_and_real_pairing(self):
        cfg=self.root/"core-mission-connection.json"
        cfg.write_text('{"schema":"test"}',encoding="utf-8")
        ctl=DashboardWorkerControl(self.root,self.folder)
        mock_config={"device_id":"suryadev-laptop"}
        with patch("suryadev_krishna_mission.load_config",return_value=mock_config):
            self.assertEqual(ctl.set_core_delegation(True)["enabled"],True)
            self.assertEqual(ctl.set_core_delegation(True)["state"],"unchanged")
            authorized=read_plan(self.plan)
            self.assertTrue(authorized["paired_core_host_delegation"])
            new="https://docs.python.org/3/library/sqlite3.html"
            with patch("suryadev.validate_url",return_value=new):
                self.assertTrue(paired_core_source_allowed(new, authorized))
            for invalid in (
                "https://unapproved.example/hidden",
                "http://docs.python.org/3/library/asyncio.html",
                "https://user:pass@docs.python.org/3/library/asyncio.html",
                "https://docs.python.org/3/library/asyncio.html#fragment",
                "https://docs.python.org:4443/3/library/asyncio.html",
            ):
                self.assertFalse(paired_core_source_allowed(invalid,authorized))
            self.assertEqual(ctl.set_core_delegation(False)["enabled"],False)
            self.assertFalse(read_plan(self.plan)["paired_core_host_delegation"])
            backups=list(self.root.glob("learning-plan.before-core-delegation-*.json"))
            self.assertEqual(len(backups),2)

    def test_core_source_policy_does_not_assume_any_host_from_token(self):
        updated=json.loads(self.plan.read_text(encoding="utf-8"))
        updated["paired_core_host_delegation"]=True
        self.plan.write_text(json.dumps(updated),encoding="utf-8")
        parsed=read_plan(self.plan)
        self.assertFalse(paired_core_source_allowed("https://evil.example/",parsed))
        with patch("suryadev.validate_url",side_effect=ValueError("private IP")):
            self.assertFalse(paired_core_source_allowed("https://docs.python.org/test",parsed))

    def test_authenticated_heartbeat_connects_only_core_and_expires(self):
        self.assertFalse(connection_indicators(self.root)["krishna"]["connected"])
        import time
        atomic_json(self.root,"krishna-fleet-heartbeat-ack.json",{
            "schema":"suryadev.krishna-authenticated-heartbeat.v1",
            "authenticated_core_reply":True,
            "acknowledged_at":time.time(),
            "knowledge_accepted":False
        })
        state=connection_indicators(self.root)
        self.assertTrue(state["krishna"]["connected"])
        self.assertFalse(state["brahmagyan"]["connected"])
        self.assertFalse(state["rishi"]["connected"])
        atomic_json(self.root,"krishna-fleet-heartbeat-ack.json",{
            "schema":"suryadev.krishna-authenticated-heartbeat.v1",
            "authenticated_core_reply":True,
            "acknowledged_at":time.time()-200})
        self.assertFalse(connection_indicators(self.root)["krishna"]["connected"])

if __name__=="__main__":
    unittest.main()
