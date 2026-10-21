"""Dynamic 1/5/10 SURYADEV machine scheduling across Council research tasks."""
import unittest
import tempfile
from pathlib import Path
from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.suryadev_fleet_policy import plan_rishi_collection


NOW = 10000


def node(index, **overrides):
    result = {
        "device_id": f"suryadev-{index:02d}",
        "authenticated": True,
        "worker_running": True,
        "network_online": True,
        "last_error": "",
        "thermal_state": "normal",
        "last_seen": NOW,
        "telemetry_sample_at": NOW,
        "cpu_percent": 35,
        "ram_percent": 45,
        "disk_percent": 30,
        "available_slots": 5,
        "capabilities": ["website", "youtube", "pdf", "book"],
        "gpu_inference": False,
    }
    result.update(overrides)
    return result


def tasks(size=35):
    kinds = ["website", "youtube", "pdf", "book"]
    return [
        {"task_id": f"task-{i:02d}", "rishi_id": f"rishi-{i:02d}",
         "kind": kinds[i % len(kinds)], "priority": 50,
         "status": "queued", "approved": True}
        for i in range(size)
    ]


class FleetPolicyTests(unittest.TestCase):
    def run_plan(self, task_list, node_list, council=None):
        return plan_rishi_collection(
            task_list, node_list, now=NOW,
            council_ids=council if council is not None else
            [f"rishi-{i:02d}" for i in range(35)])

    def test_one_five_ten_nodes_are_dynamic_not_rishi_partitions(self):
        all_tasks = tasks()
        for count, assigned in [(1, 5), (5, 25), (10, 35)]:
            with self.subTest(nodes=count):
                result = self.run_plan(all_tasks, [node(i) for i in range(count)])
                self.assertEqual(len(result["assignments"]), assigned)
                self.assertEqual(len(result["deferred"]), 35 - assigned)
                self.assertEqual(result["rishi_count"], 35)
                self.assertTrue(all(x["dispatch_state"]=="proposed_not_leased"
                                    for x in result["assignments"]))
                self.assertEqual(len(set(x["task_id"] for x in result["assignments"])), assigned)

    def test_node_not_permanently_owned_by_rishi_and_specialist_can_use_many_nodes(self):
        work = [
            {"task_id": f"q{i}", "rishi_id": "kanada", "kind": "website",
             "priority": 60, "approved": True, "status": "queued"}
            for i in range(4)
        ]
        result=self.run_plan(work,[node(1,available_slots=2),
                                   node(2,available_slots=2)],["kanada"])
        self.assertEqual(len(result["assignments"]),4)
        self.assertEqual(len({a["node_id"] for a in result["assignments"]}),2)

    def test_untrusted_stale_hot_and_unmeasured_nodes_are_never_assigned(self):
        problematic=[
            node(1, authenticated=False),
            node(2, last_seen=NOW-151),
            node(3, cpu_percent=85),
            node(4, telemetry_sample_at=NOW-46),
            node(5, ram_percent=None),
            node(6, thermal_state="critical"),
            node(7, available_slots=0),
        ]
        result=self.run_plan(tasks(2),problematic)
        self.assertEqual(result["assignments"],[])
        self.assertEqual(result["eligible_nodes"],0)
        self.assertEqual(len(result["excluded_nodes"]),len(problematic))

    def test_hardware_pressure_reduces_slots_and_gpu_capability_is_required(self):
        work = [
            {"task_id":"a","rishi_id":"kanada","kind":"pdf","priority":55,"approved":True,"status":"queued"},
            {"task_id":"b","rishi_id":"kanada","kind":"pdf","priority":55,"approved":True,"status":"queued"},
            {"task_id":"c","rishi_id":"kanada","kind":"experiment","priority":99,
             "approved":True,"status":"queued","requires_gpu":True},
        ]
        result=self.run_plan(work,[node(1,cpu_percent=78,available_slots=6,capabilities=["pdf","experiment"])],["kanada"])
        self.assertEqual(len(result["assignments"]),1)
        self.assertEqual(result["assignments"][0]["task_id"],"a")
        self.assertEqual(len(result["deferred"]),2)

    def test_unknown_approval_and_not_queued_rejected(self):
        work=tasks(3)
        work[0]["approved"]=False
        work[1]["rishi_id"]="unrecognized"
        work[2]["status"]="done"
        result=self.run_plan(work,[node(1)])
        self.assertEqual(result["assignments"],[])
        self.assertEqual(len(result["deferred"]),3)


    def test_brahmagyan_rishi_roster_drives_real_mission_plan(self):
        class Memory:
            def audit(self, *args, **kwargs): pass
        with tempfile.TemporaryDirectory() as folder:
            brain = BrahmagyanRuntime(Path(folder), object(), Memory())
            mission = brain.create_mission("KRISHNA","Materials science",knowledge_track="engineering")
            work = [{"task_id":"research-001","mission_id":mission["mission_id"],
                     "rishi_id":"kanada","kind":"website","priority":90,
                     "approved":True,"status":"queued"}]
            plan = brain.draft_suryadev_fleet_plan(
                mission["mission_id"],work,[node(1)],now=NOW)
            self.assertEqual(len(plan["assignments"]),1)
            self.assertEqual(plan["assignments"][0]["rishi_id"],"kanada")
            self.assertEqual(plan["rishi_count"],len(brain.council.list()))
            self.assertEqual(plan["execution_authority"],
                             "BRAHMA authenticated task lease (not implemented)")
            with self.assertRaisesRegex(ValueError,"belong"):
                brain.draft_suryadev_fleet_plan(mission["mission_id"],[
                    {**work[0],"mission_id":"other"}],[node(1)],now=NOW)


if __name__=="__main__":
    unittest.main()
