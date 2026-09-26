import tempfile
import unittest
from pathlib import Path

from krishna_core.autonomy_supervisor import AutonomySupervisor
from krishna_core.commitment_ledger import CommitmentLedger
from krishna_core.resource_governor import ResourceGovernor

class Memory:
    def __init__(self): self.rows=[]
    def remember(self,project,kind,content,metadata=None): self.rows.append((project,kind,content,metadata or {}))

class VanijyaStub:
    def __init__(self,calls):self.calls=calls
    def autopilot_plan(self,*,sync_products=True):
        self.calls.append(("vanijya_plan",sync_products))
        return {
            "status":"READY","ready_product_count":1,"lead_count":2,"deal_count":1,
            "agent_queue":[{"agent":"lead-qualifier"}],
            "external_send_performed":False,"spend_performed":False,
        }

class AdvisorStub:
    def advise(self,question,dashboard):
        return {"status":"OK","text":"Prioritize the qualified no-cost opportunity.","paid_fallback":False}

class CRMStub:
    def dashboard(self):return {"kpis":{"leads":2},"zero_spend":True}

class FakeOrchestrator:
    def __init__(self,path):
        self.commitments=CommitmentLedger(path)
        self.governor=ResourceGovernor(max_concurrent_jobs=1)
        self.memory=Memory()
        self.calls=[]
        self.vanijya=VanijyaStub(self.calls)
        self.manibhadra_advisor=AdvisorStub()
        self.manibhadra_crm=CRMStub()
    def investigate(self,goal,project,components):
        self.calls.append(("investigate",goal,project))
        return {"investigation_id":"i1","status":"observed","hypotheses":[]}
    def garuda_scout(self,project,goal,limit):
        self.calls.append(("research",goal,project))
        return {"web":[{"url":"https://example.com"}],"github":[],"handover":{"to":"KRISHNA"}}
    def index_project(self,project):
        self.calls.append(("index",project))
        return {"file_count":3,"symbols":[1,2]}

class AutonomySupervisorTests(unittest.TestCase):
    def test_only_explicit_safe_commitments_run(self):
        with tempfile.TemporaryDirectory() as td:
            o=FakeOrchestrator(Path(td)/"x.db")
            disabled=o.commitments.add("KRISHNA","disabled",{"goal":"x"},"test","planned")
            enabled=o.commitments.add("KRISHNA","enabled",{"goal":"check health","autonomy":{"enabled":True,"operation":"investigate","interval_seconds":60}},"test","planned")
            a=AutonomySupervisor(o,poll_seconds=60)
            out=a.run_once(now=1000)
            self.assertEqual(out["executed"],1)
            self.assertEqual(o.calls,[("investigate","check health","KRISHNA")])
            self.assertEqual(o.commitments.get(disabled["commitment_id"])["status"],"planned")
            row=o.commitments.get(enabled["commitment_id"])
            self.assertEqual(row["status"],"in_progress")
            self.assertEqual(row["detail"]["autonomy"]["last_status"],"ok")
            self.assertEqual(row["detail"]["autonomy"]["run_count"],1)
            o.commitments.close()

    def test_vanijya_plan_is_safe_read_only_unattended_operation(self):
        with tempfile.TemporaryDirectory() as td:
            o=FakeOrchestrator(Path(td)/"x.db")
            row=o.commitments.add(
                "KRISHNA","vanijya",
                {"goal":"review sales","autonomy":{"enabled":True,"operation":"vanijya_plan","interval_seconds":60}},
                "test","planned",
            )
            a=AutonomySupervisor(o,poll_seconds=60)
            out=a.run_once(now=1000)
            self.assertEqual(out["executed"],1)
            self.assertEqual(o.calls,[("vanijya_plan",False)])
            summary=out["results"][0]["summary"]
            self.assertFalse(summary["external_send_performed"])
            self.assertFalse(summary["spend_performed"])
            self.assertEqual(summary["queued_actions"],1)
            o.commitments.close()

    def test_unsafe_operation_is_never_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            o=FakeOrchestrator(Path(td)/"x.db")
            row=o.commitments.add("KRISHNA","unsafe",{"autonomy":{"enabled":True,"operation":"shell","interval_seconds":60}},"test","planned")
            a=AutonomySupervisor(o,poll_seconds=60)
            self.assertFalse(a.eligible(row,1000))
            self.assertEqual(a.run_once(now=1000)["executed"],0)
            o.commitments.close()

    def test_waiting_approval_is_never_resumed(self):
        with tempfile.TemporaryDirectory() as td:
            o=FakeOrchestrator(Path(td)/"x.db")
            row=o.commitments.add("KRISHNA","approval",{"autonomy":{"enabled":True,"operation":"research","interval_seconds":60}},"test","waiting_approval")
            a=AutonomySupervisor(o,poll_seconds=60)
            self.assertFalse(a.eligible(row,1000))
            o.commitments.close()

if __name__=="__main__": unittest.main()
