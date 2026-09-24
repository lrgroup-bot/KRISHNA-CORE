import tempfile
import unittest
from pathlib import Path

from krishna_core.brahma_process_qc import BrahmaProcessQC


class FakeBus:
    def __init__(self):
        self.subs={}
        self.events=[]
    def subscribe(self,topic,handler):
        self.subs.setdefault(topic,[]).append(handler)
    def unsubscribe(self,topic,handler):
        if handler in self.subs.get(topic,[]):self.subs[topic].remove(handler)
    def publish(self,topic,payload=None,source="test"):
        event={"event_id":f"e{len(self.events)+1}","topic":topic,"payload":dict(payload or {}),"source":source}
        self.events.append(event)
        results=[]
        for h in tuple(self.subs.get(topic,[]))+tuple(self.subs.get("*",[])):
            results.append(h(dict(event)))
        return {"event":event,"results":results}


class Memory:
    def __init__(self):self.audit_rows=[]
    def audit(self,*args):self.audit_rows.append(args)


class BrahmaProcessQCTests(unittest.TestCase):
    def make_qc(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        bus=FakeBus();memory=Memory()
        qc=BrahmaProcessQC(Path(td.name),bus,memory)
        return qc,bus,memory

    def test_color_contract_matches_working_gods_request(self):
        qc,_,_=self.make_qc()
        self.assertEqual(qc.color("idle"),"red")
        self.assertEqual(qc.color("error"),"red")
        self.assertEqual(qc.color("working"),"yellow")
        self.assertEqual(qc.color("handling"),"yellow")
        self.assertEqual(qc.color("done"),"green")

    def test_non_mutating_action_failure_is_retried_once_and_marked_done(self):
        qc,bus,_=self.make_qc()
        calls=[]
        qc.bind_runtime(
            retry_dispatch=lambda envelope:calls.append(envelope) or {"verified":True},
            consult_krishna=lambda packet:"Retry once, then verify.",
            investigate=lambda project,error:{"project":project,"error":error},
        ).attach()
        bus.publish("action.failed",{
            "action_id":"a1","action":"runtime.read.health","project":"KRISHNA","actor":"ui",
            "payload":{"probe":"health"},"permissions":[],
            "spec":{"mutating":False,"requires_approval":False},
            "error":"RuntimeError",
        },source="shared-action-bus")
        self.assertEqual(len(calls),1)
        status=qc.status()
        self.assertEqual(status["latest_color"],"green")
        self.assertEqual(next(g for g in status["gods"] if g["id"]=="brahma")["color"],"green")
        states=[x["state"] for x in status["notifications"]]
        self.assertIn("error",states)
        self.assertIn("handling",states)
        self.assertIn("done",states)

    def test_mutating_action_failure_is_not_auto_retried(self):
        qc,bus,_=self.make_qc()
        calls=[]
        qc.bind_runtime(
            retry_dispatch=lambda envelope:calls.append(envelope),
            consult_krishna=lambda packet:"Prepare a verified repair, do not bypass approval.",
            investigate=lambda project,error:{"investigated":True},
        ).attach()
        bus.publish("action.failed",{
            "action_id":"a2","action":"promotion.apply","project":"KRISHNA","actor":"ui",
            "payload":{},"permissions":[],
            "spec":{"mutating":True,"requires_approval":True},
            "error":"PermissionError",
        },source="shared-action-bus")
        self.assertEqual(calls,[])
        status=qc.status()
        self.assertEqual(status["latest_color"],"red")
        self.assertIn("verified repair",status["notifications"][-1]["title"].lower())

    def test_brahma_retry_failure_does_not_recursively_retry(self):
        qc,bus,_=self.make_qc()
        calls=[]
        qc.bind_runtime(retry_dispatch=lambda envelope:calls.append(envelope)).attach()
        bus.publish("action.failed",{
            "action_id":"a3","action":"runtime.read.health","project":"KRISHNA","actor":"brahma-qc",
            "payload":{},"permissions":[],
            "spec":{"mutating":False,"requires_approval":False},
            "error":"RuntimeError",
        },source="shared-action-bus")
        self.assertEqual(calls,[])
        self.assertEqual(qc.status()["latest_color"],"red")

    def test_work_and_done_events_update_tiny_god_status(self):
        qc,bus,_=self.make_qc();qc.attach()
        bus.publish("action.requested",{
            "action":"hawkeye.observe","project":"KRISHNA","spec":{"mutating":False}
        },source="shared-action-bus")
        hawkeye=next(g for g in qc.status()["gods"] if g["id"]=="hawkeye")
        self.assertEqual((hawkeye["state"],hawkeye["color"]),("working","yellow"))
        bus.publish("action.completed",{
            "action":"hawkeye.observe","project":"KRISHNA","spec":{"mutating":False}
        },source="shared-action-bus")
        hawkeye=next(g for g in qc.status()["gods"] if g["id"]=="hawkeye")
        self.assertEqual((hawkeye["state"],hawkeye["color"]),("done","green"))


class BrahmaProcessQCWiringTests(unittest.TestCase):
    def test_orchestrator_wires_global_qc(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("from .brahma_process_qc import BrahmaProcessQC",text)
        self.assertIn("self.brahma_process_qc = BrahmaProcessQC",text)
        self.assertIn("consult_krishna=self._brahma_qc_consult",text)
        self.assertIn("self.brahma_process_qc.attach()",text)

    def test_server_exposes_working_gods_and_feeds_internal_errors_to_qc(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/working-gods"',text)
        self.assertIn('"TOOL_ERROR"',text)
        self.assertIn('"process_qc":orch.brahma_process_status()',text)

    def test_desktop_has_compact_overlay_notification_and_main_menu(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        self.assertIn(">Working Gods<",text)
        self.assertIn('id="workingGodsOverlay"',text)
        self.assertIn('id="brahmaNotify"',text)
        self.assertIn("status-red",text)
        self.assertIn("status-yellow",text)
        self.assertIn("status-green",text)
        self.assertIn("async function loadWorkingGods()",text)
        self.assertIn("'/api/working-gods'",text)


if __name__=="__main__":
    unittest.main()
