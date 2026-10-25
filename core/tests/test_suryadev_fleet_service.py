"""Owner-approved SURYADEV leases, multi-PC allocation and failure behavior."""
import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.rishi_council import RishiCouncil
from krishna_core.suryadev_fleet_service import SuryadevFleetService


NOW = 10000.0


class Catalogue:
    def __init__(self):
        self.missions = [
            {"id":"m1","topic":"Materials failure physics","duration_hours":6,
             "approved_urls":[
                 "https://docs.example.org/alpha",
                 "https://docs.example.org/beta",
                 "https://docs.example.org/research.pdf",
                 "https://www.youtube.com/watch?v=one"]}]
    def _catalogue(self):
        return self.missions, "approved"


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.now=[NOW]
        self.nodes={}
        self.catalogue=Catalogue()
        self.council=RishiCouncil()
        self.fleet=SuryadevFleetService(Path(self.temp.name),
                        curriculum=self.catalogue, council=self.council,
                        node_reader=lambda did:self.nodes[did],
                        clock=lambda:self.now[0])
    def tearDown(self):
        self.temp.cleanup()
    def node(self, n, **changes):
        identity="suryadev-"+str(n)
        row={"device_id":identity,"authenticated":True,"worker_running":True,"network_online":True,
             "last_error":"","thermal_state":"normal",
             "last_seen":self.now[0], "telemetry_sample_at":self.now[0],
             "cpu_percent":40,"ram_percent":50,"disk_percent":35,
             "available_slots":3,"capabilities":["website","pdf","youtube"]}
        row.update(changes)
        self.nodes[identity]=row
        return identity
    def test_two_nodes_multiple_slots_no_double_claim_and_audited_receipt(self):
        a=self.node(1);other=self.node(2)
        first=self.fleet.claim(device_id=a)
        self.assertEqual(first["status"],"leased")
        replay=self.fleet.claim(device_id=a)
        self.assertTrue(replay["replay"])
        self.assertEqual(replay["lease_id"],first["lease_id"])
        second=self.fleet.claim(device_id=a,known_task_ids=[first["task"]["task_id"]])
        self.assertNotEqual(first["task"]["task_id"],second["task"]["task_id"])
        third=self.fleet.claim(device_id=other)
        self.assertNotIn(third["task"]["task_id"],{first["task"]["task_id"],second["task"]["task_id"]})
        with self.assertRaises(PermissionError):
            self.fleet.complete(device_id=other,task_id=first["task"]["task_id"],
                               lease_id=first["lease_id"],outcome="collected",evidence_sha256="a"*64)
        with self.assertRaises(ValueError):
            self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                               lease_id=first["lease_id"],outcome="collected",evidence_sha256="bad")
        result=self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                   lease_id=first["lease_id"],outcome="collected",evidence_sha256="a"*64)
        self.assertTrue(result["acknowledged"])
        self.assertFalse(result["brahmagyan_accepted"])
        self.assertTrue(result["receipt"]["source_evidence_unverified"])
        self.assertTrue(self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                   lease_id=first["lease_id"],outcome="collected",evidence_sha256="a"*64)["idempotent"])
        fresh=SuryadevFleetService(Path(self.temp.name),curriculum=self.catalogue,
                    council=self.council,node_reader=lambda d:self.nodes[d],
                    clock=lambda:self.now[0])
        self.assertEqual(fresh.status()["collected"],1)
    def test_hardware_ceiling_stale_or_unauthenticated_node_excluded(self):
        for idx,changes in enumerate([
                {"cpu_percent":85},{"ram_percent":86},{"last_seen":NOW-151},
                {"telemetry_sample_at":NOW-46},{"capabilities":[]},
                {"worker_running":False}],1):
            with self.subTest(changes=changes):
                did=self.node(idx,**changes)
                self.assertEqual(self.fleet.claim(device_id=did)["status"],"no_eligible_capacity")
    def test_expired_lease_can_move_and_old_result_is_rejected(self):
        a=self.node(1)
        first=self.fleet.claim(device_id=a)
        self.now[0]+=601
        second=self.node(2)
        replacement=self.fleet.claim(device_id=second)
        self.assertEqual(replacement["task"]["task_id"],first["task"]["task_id"])
        self.assertNotEqual(replacement["lease_id"],first["lease_id"])
        with self.assertRaises(PermissionError):
            self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                         lease_id=first["lease_id"],outcome="collected",evidence_sha256="a"*64)
    def test_node_not_allowed_to_claim_without_approved_curriculum(self):
        a=self.node(1)
        self.catalogue.missions=[]
        self.assertEqual(self.fleet.claim(device_id=a)["status"],"no_approved_work")
        self.assertEqual(self.fleet.status()["catalogue_tasks"],0)
    def test_failed_job_not_replayed_to_same_node(self):
        a=self.node(1);b=self.node(2)
        first=self.fleet.claim(device_id=a)
        self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                         lease_id=first["lease_id"],outcome="failed",detail="renderer timeout")
        # Only the other node should be able to claim this exact URL.
        others=[]
        for _ in range(3):
            reply=self.fleet.claim(device_id=a,known_task_ids=list(others))
            if reply["status"]!="leased": break
            others.append(reply["task"]["task_id"])
            self.assertNotEqual(reply["task"]["task_id"],first["task"]["task_id"])
        another=self.fleet.claim(device_id=b)
        self.assertEqual(another["task"]["task_id"],first["task"]["task_id"])
    def test_youtube_429_pauses_all_nodes_and_lease_renewal(self):
        self.catalogue.missions[0]["approved_urls"]=[
            "https://www.youtube.com/watch?v=one",
            "https://www.youtube.com/watch?v=two"]
        a=self.node(1);b=self.node(2)
        first=self.fleet.claim(device_id=a)
        self.assertEqual(first["task"]["kind"],"youtube")
        renewed=self.fleet.renew(device_id=a,task_id=first["task"]["task_id"],
                                lease_id=first["lease_id"])
        self.assertTrue(renewed["renewed"])
        self.fleet.complete(device_id=a,task_id=first["task"]["task_id"],
                         lease_id=first["lease_id"],outcome="rate_limited",detail="HTTP 429")
        self.assertEqual(self.fleet.claim(device_id=b)["status"],"no_approved_work")
        self.assertGreater(self.fleet.status()["youtube_pause_until"],self.now[0])
    def test_video_only_second_node_gets_youtube_without_website_probe(self):
        dedicated = self.node(2, capabilities=["youtube"], available_slots=80,
                              cpu_percent=18, ram_percent=22)
        first = self.fleet.claim(device_id=dedicated)
        self.assertEqual(first["status"], "leased")
        self.assertEqual(first["task"]["kind"], "youtube")
        self.assertEqual(first["task"]["url"], "https://www.youtube.com/watch?v=one")
        # The general-purpose SURYADEV 1 can continue non-video research.
        general = self.node(1, capabilities=["website","pdf"])
        second = self.fleet.claim(device_id=general)
        self.assertEqual(second["status"], "leased")
        self.assertIn(second["task"]["kind"], {"website","pdf"})

    def test_generalist_prefers_nonvideo_and_video_specialist_receives_youtube(self):
        general = self.node(1, capabilities=["website","pdf","youtube"])
        specialist = self.node(2, capabilities=["youtube"])
        first = self.fleet.claim(device_id=general)
        self.assertIn(first["task"]["kind"], {"website","pdf"})
        second = self.fleet.claim(device_id=specialist)
        self.assertEqual(second["task"]["kind"], "youtube")
        self.assertNotEqual(first["task"]["task_id"], second["task"]["task_id"])

    def test_specialist_node_still_obeys_live_hardware_guard(self):
        blocked = self.node(9, capabilities=["youtube"], available_slots=100,
                            ram_percent=87)
        self.assertEqual(self.fleet.claim(device_id=blocked)["status"],
                         "no_eligible_capacity")

    def test_owned_lease_renews_under_hardware_pressure_without_new_admission(self):
        owner = self.node(3, ram_percent=30, available_slots=4)
        first = self.fleet.claim(device_id=owner)
        task_id = first["task"]["task_id"]
        # Same host became RAM-constrained AFTER it accepted the task.
        self.node(3, ram_percent=92, available_slots=0, cpu_percent=88)
        renewed = self.fleet.renew(device_id=owner, task_id=task_id,
                                   lease_id=first["lease_id"])
        self.assertTrue(renewed["renewed"])
        self.assertEqual(self.fleet.claim(device_id=owner,
                         known_task_ids=[task_id])["status"],
                         "no_eligible_capacity")

    def test_unpaired_or_offline_node_cannot_renew_existing_lease(self):
        owner = self.node(7)
        first = self.fleet.claim(device_id=owner)
        tid = first["task"]["task_id"]
        for changes in ({"authenticated":False},{"worker_running":False},
                        {"network_online":False},{"last_seen":NOW-200},
                        {"telemetry_sample_at":NOW-70}):
            self.node(7,**changes)
            with self.subTest(changes=changes), self.assertRaises(PermissionError):
                self.fleet.renew(device_id=owner, task_id=tid, lease_id=first["lease_id"])

    def test_corrupt_ledger_fails_closed(self):
        self.fleet.file.write_text('{"schema":"bad"}',encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"corrupt"):
            self.fleet.claim(device_id=self.node(1))

if __name__=="__main__":
    unittest.main()
