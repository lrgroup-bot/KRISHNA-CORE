import tempfile
import time
import unittest
from pathlib import Path

from krishna_core.durable_event_bus import DurableEventBus
from krishna_core.durable_queue import DurableQueue
from krishna_core.job_runtime import JobRuntime
from krishna_core.krishna_protocol import KrishnaProtocol
from krishna_core.mission_budget import MissionBudgetManager
from krishna_core.mission_engine import MissionEngine, MISSION_STATES
from krishna_core.provider_contract import UnifiedProviderRegistry
from krishna_core.resource_locks import ResourceLockManager
from krishna_core.task_ledger import TaskLedger


class FakeBus:
    def __init__(self):self.events=[]
    def publish(self,topic,payload=None,source="test"):
        self.events.append((topic,payload,source));return {"event":{"topic":topic}}

class FakeActionBus:
    def dispatch(self,action,payload=None,**kwargs):
        return {
            "action_id":"a-1","action":action,"status":"completed","result":{"ok":True},
            "spec":{"mutating":False},
        }


class MissionFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=str(Path(self.temp.name)/"core.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_mission_schema_checkpoint_and_restart_recovery(self):
        bus=DurableEventBus(self.db)
        missions=MissionEngine(self.db,bus)
        row=missions.create(
            "Durable mission",project_id="KRISHNA",session_id="s1",priority=80,
            assigned_agents=["developer"],required_tools=["tests.run"],
            permission_profile="pro",resource_budget={"max_tool_calls":5},
        )
        for field in (
            "mission_id","parent_mission_id","session_id","project_id","goal","status","priority",
            "created_at","started_at","completed_at","current_step","progress","assigned_agents",
            "required_tools","permission_profile","resource_budget","checkpoints","artifacts","evidence",
            "errors","retry_count","verification_status","rollback_point",
        ):
            self.assertIn(field,row)
        self.assertEqual(row["status"],"QUEUED")
        self.assertEqual(set(MISSION_STATES),{
            "QUEUED","PLANNING","RUNNING","WAITING","BLOCKED","ACTION_REQUIRED","VERIFYING",
            "COMPLETED","FAILED","ROLLING_BACK","ROLLED_BACK","CANCELLED",
        })
        missions.transition(row["mission_id"],"RUNNING",current_step="code_changed",progress=.4)
        cp=missions.checkpoint(row["mission_id"],"code_changed",{"commit":"abc"},trusted=True)
        self.assertEqual(cp["seq"],1)
        self.assertEqual(missions.latest_trusted_checkpoint(row["mission_id"])["checkpoint_id"],cp["checkpoint_id"])
        missions.close();bus.close()

        bus2=DurableEventBus(self.db)
        missions2=MissionEngine(self.db,bus2)
        recovered=missions2.recover_interrupted()
        self.assertEqual(len(recovered),1)
        current=missions2.get(row["mission_id"])
        self.assertEqual(current["status"],"WAITING")
        self.assertEqual(current["metadata"]["interrupted_status"],"RUNNING")
        self.assertEqual(current["metadata"]["latest_trusted_checkpoint"],cp["checkpoint_id"])
        missions2.close();bus2.close()

    def test_authoritative_queue_claim_ack_and_restart_requeue(self):
        q=DurableQueue(self.db,lease_seconds=15)
        item=q.enqueue("test.action",{"x":1},mission_id="m1",max_retries=2)
        self.assertEqual(q.status()["pending"],1)
        claimed=q.claim("worker-a",item["queue_id"])
        self.assertEqual(claimed["state"],"processing")
        self.assertFalse(q.drained())
        q.close()

        q2=DurableQueue(self.db,lease_seconds=15)
        recovered=q2.recover_stale_processing(force=True)
        self.assertEqual(recovered[0]["state"],"pending")
        claimed=q2.claim("worker-b",item["queue_id"])
        done=q2.ack(item["queue_id"],{"ok":True},worker_id="worker-b")
        self.assertEqual(done["state"],"completed")
        status=q2.status()
        self.assertEqual(status["pending"],0)
        self.assertEqual(status["processing"],0)
        self.assertTrue(status["drained"])
        self.assertGreaterEqual(status["requeued"],1)
        q2.close()

    def test_resource_locks_block_overlapping_writers_but_allow_readers(self):
        locks=ResourceLockManager(self.db)
        root=Path(self.temp.name)/"project"
        child=root/"src"/"backend"
        first=locks.acquire("TREE_LOCK",str(root/"src"),mode="write",owner_token="dev")
        with self.assertRaises(RuntimeError):
            locks.acquire("EXACT_LOCK",str(child/"app.py"),mode="write",owner_token="other")
        self.assertTrue(locks.release(first["lock_id"],"dev"))
        r1=locks.acquire("TREE_LOCK",str(root/"ui"),mode="read",owner_token="reader-a")
        r2=locks.acquire("EXACT_LOCK",str(root/"ui"/"x.js"),mode="read",owner_token="reader-b")
        self.assertTrue(r1 and r2)
        locks.close()

    def test_event_bus_persists_across_restart(self):
        bus=DurableEventBus(self.db)
        bus.publish("MISSION_CREATED",{"mission_id":"m1"})
        seq=bus.recent()[-1]["seq"]
        bus.close()
        bus2=DurableEventBus(self.db)
        rows=bus2.recent(after_seq=seq-1)
        self.assertEqual(rows[-1]["topic"],"MISSION_CREATED")
        self.assertEqual(rows[-1]["payload"]["mission_id"],"m1")
        bus2.close()

    def test_budget_enforces_tool_limit(self):
        budgets=MissionBudgetManager(self.db)
        budgets.configure("m1",{"max_tool_calls":1,"max_wall_time":100})
        budgets.consume("m1","tool_calls",1)
        with self.assertRaises(RuntimeError):
            budgets.consume("m1","tool_calls",1)
        budgets.close()

    def test_job_runtime_uses_queue_and_mission_then_waits_for_verification(self):
        task=TaskLedger(self.db)
        events=DurableEventBus(self.db)
        missions=MissionEngine(self.db,events)
        queue=DurableQueue(self.db,events)
        budgets=MissionBudgetManager(self.db)
        jobs=JobRuntime(task,FakeActionBus(),missions,queue,budgets,events)
        row=jobs.submit("test.action",{"x":1},resource_budget={"max_tool_calls":5})
        self.assertTrue(row["mission_id"])
        self.assertEqual(queue.get(row["queue_id"])["state"],"completed")
        self.assertEqual(missions.get(row["mission_id"])["status"],"VERIFYING")
        jobs.mark_verified(row["mission_id"],True,"independent checker passed")
        self.assertEqual(missions.get(row["mission_id"])["status"],"COMPLETED")
        budgets.close();queue.close();missions.close();events.close();task.close()

    def test_protocol_and_provider_contract(self):
        msg=KrishnaProtocol.envelope("request","mission.create",{"goal":"x"},surface="mobile")
        self.assertEqual(msg["protocol_version"],"1.0")
        self.assertEqual(KrishnaProtocol.validate(msg)["surface"],"mobile")
        class Router:
            def available(self):
                return [
                    {"provider":"ollama","model":"qwen","available":True,"local":True},
                    {"provider":"cloud","model":"remote","available":True,"local":False,"free_only":False,
                     "capabilities":{"text":True,"vision":True}},
                ]
        reg=UnifiedProviderRegistry(Router())
        rows=reg.list()
        self.assertTrue(all("capabilities" in x for x in rows))
        self.assertEqual(reg.select(privacy="local_only")[0]["provider_id"],"ollama")
        self.assertEqual(reg.select(privacy="approved_cloud",vision=True)[0]["provider_id"],"cloud")


if __name__=="__main__":
    unittest.main()
