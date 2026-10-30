"""Mock-transport laptop/Core flow: approved URLs, durable leases, evidence ACK.

No network download is performed. Real paired HTTPS/TLS transport is tested
separately; this exercise uses its dependency-injected authenticated interface.
"""
import json
import time
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "standalone" / "suryadev"))

from krishna_core.suryadev import SuryadevAgent
from suryadev import Library
from suryadev_fleet_client import FleetClient
from suryadev_evidence import save_evidence


class FleetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.core=SuryadevAgent(self.root/"core")
        curriculum=self.core.mission_backlog.catalogue
        curriculum.write_text(json.dumps({
            "schema":"krishna.suryadev.approved-curriculum.v1",
            "allowed_source_hosts":["docs.example.org"],
            "missions":[{"id":"electronics-101","topic":"Semiconductor engineering",
                         "approved_urls":["https://docs.example.org/a",
                                          "https://docs.example.org/b"]}]
        }),encoding="utf-8")
        self.local=self.root/"suryadev-data"
        self.local.mkdir()
        self.plan=self.local/"learning-plan.json"
        self.plan.write_text(json.dumps({
            "approved_urls":["https://docs.example.org/a","https://docs.example.org/b"],
            "approved_feeds":[],"allowed_source_hosts":["docs.example.org"],
            "max_new_per_cycle":20,"max_queued":75}),encoding="utf-8")
        self.cred=self.local/"secret.token"
        self.cred.write_text("X"*64,encoding="ascii")
        self.config=self.local/"pair.json"
        self.config.write_text(json.dumps({
            "schema":"suryadev.krishna-mission-connection.v1",
            "endpoint":"https://127.0.0.1:8766",
            "cert_sha256":"a"*64,"device_id":"suryadev-test-one",
            "token_file":str(self.cred)}),encoding="utf-8")
        self.clock=[time.time()]
        self.core.clock=lambda:self.clock[0]
        self.core.fleet.clock=lambda:self.clock[0]
        self.calls=[]
        def transport(config,path,payload):
            self.calls.append(path)
            device=config["device_id"]
            self.assertEqual(device,payload["device_id"])
            if path.endswith("/device/heartbeat"):
                # This path represents the successful paired-auth Core route.
                result=self.core.device_heartbeat({**payload,"device_id":device}, authenticated=True)
                return result
            if path.endswith("/fleet/claim"):
                return self.core.fleet.claim(device_id=device,
                              known_task_ids=payload.get("known_task_ids"))
            if path.endswith("/fleet/renew"):
                return self.core.fleet.renew(device_id=device,
                              task_id=payload["task_id"],lease_id=payload["lease_id"])
            if path.endswith("/fleet/complete"):
                result=self.core.fleet.complete(device_id=device,
                              task_id=payload["task_id"],lease_id=payload["lease_id"],
                              outcome=payload["outcome"],
                              evidence_sha256=payload.get("evidence_sha256",""),
                              source_excerpt=payload.get("source_excerpt",""),
                              detail=payload.get("detail",""))
                # Emulate the authenticated HTTP route's durable
                # BRAHMAGYAN candidate-inbox acknowledgment.
                if result.get("receipt"):
                    receipt=result["receipt"]
                    self.assertEqual(receipt["evidence_sha256"],
                                     payload["evidence_sha256"])
                    result["candidate_recorded"]=True
                return result
            self.fail("unexpected route "+path)
        self.transport=transport
        self.lib=Library(self.local)
        self.client=FleetClient(self.local,self.plan,self.config,transport=transport,
                                clock=lambda:self.clock[0])
        self.telemetry={"sample_age_seconds":0,"cpu_percent":20,"ram_percent":20,
                        "disk_percent":25,"ram_total_gb":16,"disk_free_gb":100,
                        "max_total":3,"capabilities":["website","pdf","youtube","book"],
                        "logical_cpus":12,"cpu_name":"test i7","platform":"Windows",
                        "gpu_name":"test GPU","gpu_inference":False}
    def tearDown(self):
        self.lib.db.close()
        self.tmp.cleanup()
    def test_many_approved_jobs_and_evidence_receipt_survive_restart(self):
        with (patch("suryadev_fleet_client.hardware_report",return_value=self.telemetry),
              patch("suryadev.validate_url",side_effect=lambda url:url)):
            first=self.client.tick(self.lib)
            self.assertEqual(first["state"],"owner_approved_lease_accepted")
            self.clock[0]+=16
            second=self.client.tick(self.lib)
            self.assertEqual(second["state"],"owner_approved_lease_accepted")
            self.assertNotEqual(first["task_id"],second["task_id"])
            self.assertEqual(self.core.fleet.status()["active_leases"],2)
            self.assertEqual(len(self.client.state["assignments"]),2)
            evidence=save_evidence(self.local, "text", source=first["source_url"])
            self.lib.db.execute(
                "UPDATE jobs SET status='done' WHERE id=?", (first["job_id"],))
            self.lib.db.execute(
                "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                "VALUES(?,?,?,?,?,?,?,?)",(
                    first["job_id"],first["source_url"],evidence["sha256"],
                    "Verified acquisition","candidate evidence","text",self.clock[0],"extractive_preview"))
            self.lib.db.commit()
            self.clock[0]+=1
            self.client.tick(self.lib)
            self.assertEqual(self.core.fleet.status()["collected"],1)
            receipt=self.core.fleet._load()["receipts"][first["task_id"]]
            self.assertEqual(receipt["source_excerpt"],"text")
            self.assertTrue(receipt["untrusted_source_text"])
            self.assertFalse(self.client.state["receipts"][first["task_id"]]["brahmagyan_accepted"])
            self.assertTrue(self.client.state["receipts"][first["task_id"]]["brahmagyan_candidate_recorded"])
            resumed=FleetClient(self.local,self.plan,self.config,
                                transport=self.transport,clock=lambda:self.clock[0])
            self.assertIn(second["task_id"],resumed.state["assignments"])
            self.assertIn(first["task_id"],resumed.state["receipts"])
    def test_locally_unapproved_url_never_enters_sqlite(self):
        self.plan.write_text(json.dumps({"approved_urls":[],
             "allowed_source_hosts":["docs.example.org"]}),encoding="utf-8")
        with (patch("suryadev_fleet_client.hardware_report",return_value=self.telemetry),
              patch("suryadev.validate_url",side_effect=lambda url:url)):
            result=self.client.tick(self.lib)
        self.assertEqual(result["state"],"locally_rejected_unapproved_url")
        self.assertEqual(self.lib.stats().get("queued",0),0)
        self.assertEqual(self.core.fleet.status()["collected"],0)

if __name__=="__main__":
    unittest.main()
