"""Offline tests for paired fleet source allowlists, evidence ACK and crash journal."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_fleet_client import FleetClient
from suryadev_evidence import save_evidence

URL="https://docs.python.org/3/library/asyncio.html"
NOW=1000.0


class FleetClientTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.root=Path(self.folder.name)
        self.plan=self.root/"learning-plan.json"
        self.plan.write_text(json.dumps({
            "approved_urls":[URL],"approved_feeds":[],
            "allowed_source_hosts":["docs.python.org"],
            "max_new_per_cycle":5,"max_queued":20,
        }),encoding="utf-8")
        self.lib=Library(self.root)
        self.config=self.root/"config.json"
        self.config.write_text("{}",encoding="utf-8")
        self.mock_config={"device_id":"suryadev-01"}
        self.fake_health={
            "sample_age_seconds":0,"cpu_percent":32.0,"ram_percent":43.0,
            "disk_percent":25.0,"ram_total_gb":16,"disk_free_gb":30,
            "max_total":3,"capabilities":["website","pdf","youtube"],
            "logical_cpus":12,"gpu_inference":False,
        }
        self.calls=[]
        self.lease_id="a"*32
        self.task_id="fleet-"+"b"*28
        self.url=URL
    def tearDown(self):
        self.lib.db.close()
        self.folder.cleanup()

    def transport(self,config,path,payload):
        self.calls.append((path,payload))
        if path.endswith("/heartbeat"):
            return {"accepted":True,"device_id":"suryadev-01"}
        if path.endswith("/claim"):
            return {"status":"leased","lease_id":self.lease_id,
                    "task":{"task_id":self.task_id,"url":self.url,
                            "kind":"website","rishi_id":"kanada"},
                    "expires_at":NOW+600}
        if path.endswith("/complete"):
            return {"acknowledged":True,"brahmagyan_accepted":False,
                    "candidate_recorded":True,
                    "receipt":{"task_id":payload["task_id"],
                               "device_id":config["device_id"],
                               "lease_id":payload["lease_id"],
                               "evidence_sha256":payload.get("evidence_sha256","")}}
        if path.endswith("/renew"):
            return {"renewed":True,"lease_id":self.lease_id,"expires_at":NOW+700}
        raise AssertionError(path)

    def create(self):
        return FleetClient(self.root,self.plan,self.config,
                           transport=self.transport,clock=lambda:NOW)

    def test_approved_collection_keeps_exact_source_and_reuses_sqlite(self):
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=self.fake_health)):
            worker=self.create()
            result=worker.tick(self.lib)
            self.assertEqual(result["state"],"owner_approved_lease_accepted")
            self.assertEqual(self.lib.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],1)
            # Network loss and process restart preserve the SQLite job pointer.
            restarted=self.create()
            self.assertIn(self.task_id,restarted.state["assignments"])
            self.assertEqual(restarted.state["assignments"][self.task_id]["url"],URL)
            job_id=result["job_id"]
            digest = save_evidence(self.root, "Source text",
                                   source=URL)["sha256"]
            with self.lib.db:
                self.lib.db.execute("UPDATE jobs SET status='done' WHERE id=?",(job_id,))
                self.lib.db.execute(
                    "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (job_id,URL,digest,"Verified source identity",
                     "Extraction only","Source text",NOW,"extractive_preview"))
            ended=restarted.tick(self.lib)
            self.assertIn(self.task_id,restarted.state["receipts"])
            self.assertFalse(restarted.state["receipts"][self.task_id]["brahmagyan_accepted"])
            self.assertTrue(restarted.state["receipts"][self.task_id]["brahmagyan_candidate_recorded"])
            self.assertFalse(restarted.state["receipts"][self.task_id]["rishi_exam_verified"])
            self.assertEqual(self.lib.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],1)
            self.assertTrue(any(path.endswith("/complete") for path,_ in self.calls))

    def test_done_without_matching_evidence_does_not_complete_core_lease(self):
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=self.fake_health)):
            worker=self.create()
            assigned=worker.tick(self.lib)
            with self.lib.db:
                self.lib.db.execute("UPDATE jobs SET status='done' WHERE id=?",
                                    (assigned["job_id"],))
                self.lib.db.execute(
                    "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (assigned["job_id"], URL, "a"*64, "Unverified","Bad","Bad",
                     NOW,"extractive_preview"))
            worker.tick(self.lib)
            self.assertFalse(any(path.endswith("/complete") for path,_ in self.calls))
            self.assertEqual(worker.state["assignments"][self.task_id]["state"],
                             "local_evidence_integrity_failed")
            self.assertNotIn(self.task_id,worker.state["receipts"])

    def test_missing_candidate_ack_never_completes_local_receipt(self):
        evidence = save_evidence(self.root, "Verified source text",
                                 source=URL)
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=self.fake_health)):
            worker=self.create()
            assigned=worker.tick(self.lib)
            with self.lib.db:
                self.lib.db.execute("UPDATE jobs SET status='done' WHERE id=?",
                                    (assigned["job_id"],))
                self.lib.db.execute(
                    "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (assigned["job_id"],URL,evidence["sha256"],"Page",
                     "Extractive","Verified source text",NOW,"extractive_preview"))
            def uncommitted(config,path,payload):
                if path.endswith("/complete"):
                    return {"acknowledged":True}
                return self.transport(config,path,payload)
            worker.transport=uncommitted
            reply=worker.tick(self.lib)
            self.assertEqual(reply["state"],"offline_retry")
            self.assertIn(self.task_id,worker.state["assignments"])
            self.assertNotIn(self.task_id,worker.state["receipts"])

    def test_delegated_paired_core_url_is_queued_once_within_host(self):
        # This approval delegates only source selection to the paired,
        # already-authorized Core task, not an arbitrary remote hostname.
        original=json.loads(self.plan.read_text(encoding="utf-8"))
        original["paired_core_host_delegation"]=True
        self.plan.write_text(json.dumps(original),encoding="utf-8")
        self.url="https://docs.python.org/3/library/sqlite3.html"
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=self.fake_health),
              patch("suryadev.validate_url",return_value=self.url)):
            worker=self.create()
            result=worker.tick(self.lib)
            self.assertEqual(result["state"],"owner_approved_lease_accepted")
            self.assertEqual(self.lib.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],1)
            self.assertEqual(self.lib.db.execute("SELECT url FROM jobs").fetchone()[0],self.url)

    def test_scheduled_rest_reports_resting_and_claims_no_new_work(self):
        from suryadev_liveops import atomic_json
        atomic_json(self.root,"mission-cycle-runtime.json",{
            "schema":"suryadev.mission-cycle.v1",
            "phase":"rest",
            "rest_until":1600,
            "admission_allowed":False})
        health=dict(self.fake_health,temperature_max_c=86,
                    temperature_available=True)
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=health)):
            worker=self.create()
            self.assertIsNone(worker.tick(self.lib,allow_claim=False))
        heartbeats=[payload for path,payload in self.calls if path.endswith("/heartbeat")]
        self.assertEqual(len(heartbeats),1)
        self.assertEqual(heartbeats[0]["learning_state"],"resting")
        self.assertEqual(heartbeats[0]["thermal_state"],"hot")
        self.assertFalse(any(path.endswith("/claim") for path,_ in self.calls))

    def test_unapproved_url_rejected_without_local_fetch(self):
        self.url="https://unapproved.example.net/learn"
        with (patch("suryadev_fleet_client.load_config",return_value=self.mock_config),
              patch("suryadev_fleet_client.hardware_report",return_value=self.fake_health)):
            worker=self.create()
            result=worker.tick(self.lib)
            self.assertEqual(result["state"],"locally_rejected_unapproved_url")
            self.assertEqual(self.lib.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],0)
            self.assertTrue(any(path.endswith("/complete") and
                                payload.get("outcome")=="rejected"
                                for path,payload in self.calls))

if __name__=="__main__":
    unittest.main()
