import tempfile
import unittest
from pathlib import Path

from krishna_core.automation_bus import AutomationBus
from krishna_core.critic_verifier import IndependentCriticVerifier
from krishna_core.job_runtime import JobRuntime
from krishna_core.narad.context import build_node_payload
from krishna_core.narad.runtime import NaradRuntime
from krishna_core.narad.workflow_graph import WorkflowGraph
from krishna_core.permission_runtime import PermissionRuntime
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.shared_action_bus import SharedActionBus
from krishna_core.sudarshan_control import SudarshanControlPlane
from krishna_core.task_ledger import TaskLedger
from krishna_core.verification import VerificationEngine


class NaradGraphRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.root=root
        self.policy=PolicyKernel(root/"policy")
        self.permissions=PermissionRuntime()
        self.bus=AutomationBus()
        self.actions=SharedActionBus(
            self.bus,self.policy,permission_resolver=self.permissions.authorize,
        )
        self.ledger=TaskLedger(root/"runtime.db")
        self.jobs=JobRuntime(self.ledger,self.actions)
        self.critic=IndependentCriticVerifier(VerificationEngine(),None)
        self.sudarshan=SudarshanControlPlane(self.actions,self.jobs,self.critic)
        self.narad=NaradRuntime(self.policy,self.bus,state_path=root/"narad.json")
        self.narad.bind_sudarshan(self.sudarshan)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_graph_normalizes_legacy_steps_and_defaults_to_sequential_dependencies(self):
        graph=WorkflowGraph([
            {"action":"publish_event","topic":"one"},
            {"action":"publish_event","topic":"two"},
        ])
        self.assertEqual(graph.order,["step-1","step-2"])
        self.assertEqual(graph.by_id["step-1"].action,"narad.publish_event")
        self.assertEqual(graph.by_id["step-2"].depends_on,("step-1",))

    def test_graph_supports_explicit_dependencies_and_rejects_cycles(self):
        graph=WorkflowGraph([
            {"id":"a","action":"x","depends_on":[]},
            {"id":"b","action":"y","depends_on":[]},
            {"id":"c","action":"z","depends_on":["a","b"]},
        ])
        self.assertEqual(set(graph.order[:2]),{"a","b"})
        self.assertEqual(graph.order[-1],"c")
        with self.assertRaises(ValueError):
            WorkflowGraph([
                {"id":"a","action":"x","depends_on":["b"]},
                {"id":"b","action":"y","depends_on":["a"]},
            ])

    def test_context_mapping_uses_bounded_references_without_eval(self):
        payload=build_node_payload(
            {"value":"${input.name}","prior":"${nodes.first.result.value}","label":"Hello ${input.name}"},
            {"name":"Krishna"},
            {"first":{"result":{"value":42}}},
        )
        self.assertEqual(payload["value"],"Krishna")
        self.assertEqual(payload["prior"],42)
        self.assertEqual(payload["label"],"Hello Krishna")
        with self.assertRaises(KeyError):
            build_node_payload({"x":"${__import__.os.system}"},{},{})

    def test_workflow_executes_every_node_through_sudarshan_and_verifier(self):
        seen=[]
        self.actions.register(
            "test.echo",
            lambda payload,context: seen.append((context["source"],context["actor"])) or {"value":payload["value"]},
            sources=("job",),permissions=(),
        )
        w=self.narad.create_workflow("graph",{"type":"manual"},[
            {"id":"first","action":"test.echo","payload":{"value":7}},
            {"id":"second","action":"test.echo","payload":{"value":"${nodes.first.result.value}"}},
        ])
        self.narad.promote(w["id"],"sandbox")
        out=self.narad.execute(w["id"])
        self.assertEqual(out["execution_authority"],"Sudarshan Control Plane")
        self.assertTrue(out["verification"]["passed"])
        self.assertEqual(out["results"],[{"value":7},{"value":7}])
        self.assertEqual(len(seen),2)
        self.assertTrue(all(source=="job" for source,_ in seen))
        self.assertTrue(all(node["verification"]["passed"] for node in out["nodes"]))

    def test_job_node_uses_same_sudarshan_gate_and_durable_task_ledger(self):
        self.actions.register("test.job",lambda payload,context:{"ok":True},sources=("job",))
        w=self.narad.create_workflow("job",{"type":"manual"},[
            {"id":"worker","action":"test.job","dispatch":"job"},
        ])
        self.narad.promote(w["id"],"sandbox")
        out=self.narad.execute(w["id"])
        node=out["nodes"][0]
        self.assertTrue(node["job_id"])
        self.assertTrue(node["action_id"])
        self.assertEqual(self.ledger.get(node["job_id"])["status"],"completed")

    def test_external_retry_is_single_attempt_unless_explicitly_retry_safe(self):
        calls=[]
        self.actions.register(
            "narad.provider_send",
            lambda payload,context: calls.append(1) or (_ for _ in ()).throw(RuntimeError("provider failed")),
            sources=("job",),permissions=("narad.execute","send_external"),requires_approval=True,
        )
        w=self.narad.create_workflow("external",{"type":"manual"},[
            {"action":"provider_send","provider":"x","operation":"send",
             "retry":{"max_attempts":3,"delay_ms":0}},
        ])
        self.narad.promote(w["id"],"sandbox")
        self.narad.promote(w["id"],"verified",verified=True)
        self.narad.promote(w["id"],"stable",verified=True)
        with self.assertRaises(RuntimeError):
            self.narad.execute(w["id"],approved=True)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.narad.dead_letter_status()["count"],1)

    def test_checkpoint_survives_failure_and_resume_skips_completed_nodes(self):
        calls={"first":0,"second":0}
        def first(payload,context):
            calls["first"]+=1
            return {"value":11}
        def fail_second(payload,context):
            calls["second"]+=1
            raise RuntimeError("temporary failure")
        self.actions.register("test.first",first,sources=("job",))
        self.actions.register("test.second",fail_second,sources=("job",))
        w=self.narad.create_workflow("resume",{"type":"manual"},[
            {"id":"first","action":"test.first"},
            {"id":"second","action":"test.second"},
        ])
        self.narad.promote(w["id"],"sandbox")
        with self.assertRaises(RuntimeError):
            self.narad.execute(w["id"])
        self.assertEqual(calls,{"first":1,"second":1})
        self.assertEqual(len(self.narad.checkpoints),1)
        run_id=next(iter(self.narad.checkpoints))
        self.assertEqual(self.narad.checkpoints[run_id]["completed"],["first"])

        self.actions.register(
            "test.second",
            lambda payload,context: calls.__setitem__("second",calls["second"]+1) or {"value":22},
            sources=("job",),
        )
        restored=NaradRuntime(self.policy,self.bus,state_path=self.root/"narad.json")
        restored.bind_sudarshan(self.sudarshan)
        out=restored.resume_checkpoint(run_id)
        self.assertTrue(out["verification"]["passed"])
        self.assertEqual(calls["first"],1)
        self.assertEqual(calls["second"],2)
        self.assertEqual(restored.checkpoints,{})

    def test_runtime_status_exposes_lean_engine_not_n8n_runtime(self):
        status=self.narad.status()
        self.assertTrue(status["sudarshan_bound"])
        self.assertEqual(status["workflow_engine"],"typed-dag/sudarshan")
        self.assertEqual(status["node_contracts"],["action","job"])
        self.assertNotIn("n8n-runtime",str(status).lower())


if __name__=="__main__":
    unittest.main()
