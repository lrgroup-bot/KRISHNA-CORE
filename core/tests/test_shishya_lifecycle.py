import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.ephemeral_workers import EphemeralWorkerRuntime
from krishna_core.rishi_learning import RishiLearningLedger
from krishna_core.rishi_council import RishiCouncil


class MemoryStub:
    def __init__(self):
        self.rows=[]
        self.audit_rows=[]
    def remember(self,*args):
        self.rows.append(args)
    def audit(self,*args):
        self.audit_rows.append(args)


class GyanStub:
    def propose(self,*args,**kwargs):
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class RouterStub:
    def coding_plan(self,privacy):
        return [
            {"provider":"stub-a","model":"model-a"},
            {"provider":"stub-b","model":"model-b"},
        ]
    def ask(self,provider,prompt):
        specialty=""
        for line in prompt.splitlines():
            if line.startswith("Specialty:"):
                specialty=line.split(":",1)[1].strip()
        return json.dumps({
            "summary":f"Completed {specialty}",
            "findings":[{
                "finding":f"{specialty} produced a candidate finding.",
                "evidence":["evidence item"],
                "sources":["https://example.org/source"],
                "confidence":0.72,
                "knowledge_track":"modern_science",
                "status":"supported",
            }],
            "successful_methods":["source comparison"],
            "failed_approaches":["weak keyword-only search"],
            "corrections":[],
            "reusable_skills":["evidence triage"],
            "evaluation_results":["candidate requires Gautama verification"],
            "unresolved_questions":[f"What remains unknown for {specialty}?"],
            "cross_domain_relationships":["linked to adjacent specialty"],
        })


class KabachStub:
    def gate_external_evidence(self,text,source):
        return {"allowed":True,"source":source}


class AutonomousShishyaLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.bg=BrahmagyanRuntime(Path(self.tmp.name)/"bg",GyanStub(),self.memory)
        self.ledger=RishiLearningLedger(Path(self.tmp.name)/"learning",RishiCouncil(),self.memory)
        self.workers=EphemeralWorkerRuntime(RouterStub(),self.memory,KabachStub(),max_workers=8)

    def tearDown(self):
        self.tmp.cleanup()

    def test_any_rishi_can_parent_shishyas_for_a_mission(self):
        m=self.bg.create_mission(
            "KRISHNA","Cancer genomics","What evidence matters?",
            rishi_id="sushruta",knowledge_track="modern_science",
        )
        plan=self.bg.shishya_plan(
            m["mission_id"],["Genomics","Replication"],2,parent_rishi="kashyapa"
        )
        self.assertEqual(plan["parent_rishi"],"kashyapa")
        self.assertEqual(plan["requested_count"],2)

    def test_large_rishi_request_is_split_into_bounded_waves(self):
        m=self.bg.create_mission("KRISHNA","Large research mission",rishi_id="gautama")
        with patch.dict("os.environ",{
            "KRISHNA_SHISHYA_MAX_PER_REQUEST":"20",
            "KRISHNA_SHISHYA_MAX_CONCURRENT":"3",
        },clear=False):
            plan=self.bg.shishya_plan(m["mission_id"],count=11,parent_rishi="gautama")
        self.assertEqual(plan["requested_count"],11)
        self.assertEqual(plan["wave_count"],4)
        self.assertTrue(all(len(w)<=3 for w in plan["waves"]))

    def test_ephemeral_worker_identity_is_destroyed_but_findings_return(self):
        request={
            "status":"approved","approved_by":"KRISHNA",
            "requested_count":2,"role":"research-shishya",
            "manager":"rishi:kashyapa","parent_rishi":"kashyapa",
            "retention_policy":"findings_and_provenance_only",
            "assignments":[
                {"specialty":"Genomics","task":"Review genomics evidence"},
                {"specialty":"Replication","task":"Find replication evidence"},
            ],
        }
        batch=self.workers.execute("KRISHNA",request,"Mission context","local_only")
        self.assertTrue(batch["destroyed"])
        self.assertFalse(batch["live_after_return"])
        self.assertEqual(self.workers.status()["live_count"],0)
        self.assertEqual(len(batch["workers"]),2)
        self.assertTrue(all(x.get("worker_id_hash") for x in batch["workers"]))
        self.assertTrue(all("worker_id" not in x for x in batch["workers"]))
        # Persistent worker-batch memory is compact and excludes raw model output.
        stored=[x for x in self.memory.rows if len(x)>=2 and x[1]=="ephemeral_worker_batch"][-1]
        compact=stored[3]
        self.assertNotIn("workers",compact)
        self.assertEqual(compact["retention_policy"],"findings_and_provenance_only")

    def test_handover_stores_findings_not_live_shishya(self):
        m=self.bg.create_mission(
            "KRISHNA","DNA repair","Investigate repair mechanisms",
            rishi_id="kashyapa",knowledge_track="modern_science",
        )
        request={
            "status":"approved","approved_by":"KRISHNA",
            "requested_count":1,"role":"research-shishya",
            "manager":"rishi:kashyapa","parent_rishi":"kashyapa",
            "retention_policy":"findings_and_provenance_only",
            "assignments":[{"specialty":"DNA Repair","task":"Review DNA repair evidence"}],
        }
        batch=self.workers.execute("KRISHNA",request,"Mission context","local_only")
        handover=self.bg.absorb_shishya(m["mission_id"],batch,parent_rishi="kashyapa")
        self.assertTrue(handover["destroyed"])
        self.assertTrue(handover["findings"])
        self.assertNotIn("result",handover["workers"][0])
        self.assertIn("handover",handover["workers"][0])

        learned=self.ledger.ingest_shishya_handover(m,handover)
        self.assertEqual(learned["parent_rishi"],"kashyapa")
        profile=self.ledger.profile("kashyapa")
        self.assertEqual(profile["findings"][-1]["role"],"shishya_handover")
        self.assertEqual(profile["findings"][-1]["maturity"],"L1")
        self.assertTrue(profile["open_questions"])

    def test_shishya_handover_counts_as_parent_direct_learning(self):
        self.ledger.record_finding(
            "kashyapa","genomics","delegated finding",
            role="shishya_handover",maturity="L1",evidence_status="candidate",
        )
        status=self.ledger.bootstrap_status()
        row=[x for x in status["rishis"] if x["rishi_id"]=="kashyapa"][0]
        self.assertTrue(row["ready"])
        self.assertEqual(row["direct_finding_count"],1)

    def test_absorb_refuses_non_destroyed_batch(self):
        m=self.bg.create_mission("KRISHNA","Safety","Check lifecycle",rishi_id="gautama")
        with self.assertRaises(RuntimeError):
            self.bg.absorb_shishya(
                m["mission_id"],
                {"batch_id":"b1","destroyed":False,"workers":[]},
                parent_rishi="gautama",
            )

    def test_orchestrator_implements_multi_wave_retirement_and_learning(self):
        root=Path(__file__).resolve().parents[1]
        source=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        self.assertIn("execute_tree",source)
        self.assertIn("ingest_shishya_handover",source)
        self.assertIn("all_shishyas_retired",source)
        self.assertIn("findings_and_provenance_only",source)
        self.assertIn("descendants inherit parent scope",source)




class NestedRouterStub(RouterStub):
    def ask(self,provider,prompt):
        specialty=""
        for line in prompt.splitlines():
            if line.startswith("Specialty:"):
                specialty=line.split(":",1)[1].strip()
        children=[]
        if specialty=="Root Biology":
            children=[
                {"specialty":"Child Evidence","task":"Check independent evidence","reason":"Independent evidence is separable."},
                {"specialty":"Child Replication","task":"Check replication","reason":"Replication is a separate uncertainty."},
            ]
        elif specialty=="Child Evidence":
            children=[
                {"specialty":"Grandchild Statistics","task":"Audit statistics","reason":"Statistical validity needs a specialist."}
            ]
        return json.dumps({
            "summary":f"Completed {specialty}",
            "findings":[{
                "finding":f"{specialty} finding",
                "evidence":["evidence"],
                "sources":["https://example.org/"+specialty.replace(" ","-").lower()],
                "confidence":0.7,
                "knowledge_track":"modern_science",
                "status":"supported",
            }],
            "successful_methods":["review"],
            "failed_approaches":[],
            "corrections":[],
            "reusable_skills":["triage"],
            "evaluation_results":[],
            "unresolved_questions":[],
            "cross_domain_relationships":[],
            "sub_shishya_requests":children,
        })


class NestedShishyaTreeTests(unittest.TestCase):
    def setUp(self):
        self.memory=MemoryStub()
        self.workers=EphemeralWorkerRuntime(NestedRouterStub(),self.memory,KabachStub(),max_workers=8)

    def _request(self,**overrides):
        row={
            "status":"approved","approved_by":"KRISHNA",
            "requested_count":1,"role":"research-shishya",
            "manager":"rishi:kashyapa","parent_rishi":"kashyapa",
            "retention_policy":"findings_and_provenance_only",
            "assignments":[{"specialty":"Root Biology","task":"Investigate root problem"}],
            "max_tree_depth":3,
            "max_tree_nodes":10,
            "max_children_per_worker":3,
            "max_concurrent":3,
        }
        row.update(overrides)
        return row

    def test_nested_tree_branches_and_collapses(self):
        tree=self.workers.execute_tree("KRISHNA",self._request(),"Mission","local_only")
        self.assertEqual(tree["node_count"],4)
        self.assertEqual(tree["max_depth_reached"],3)
        self.assertEqual(tree["level_counts"],{"1":1,"2":2,"3":1})
        self.assertEqual(len(tree["edges"]),3)
        self.assertTrue(tree["destroyed"])
        self.assertTrue(tree["all_nodes_destroyed"])
        self.assertFalse(tree["live_after_return"])
        self.assertEqual(self.workers.status()["live_count"],0)

    def test_depth_limit_stops_grandchildren(self):
        tree=self.workers.execute_tree(
            "KRISHNA",self._request(max_tree_depth=2),"Mission","local_only"
        )
        self.assertEqual(tree["node_count"],3)
        self.assertEqual(tree["max_depth_reached"],2)
        self.assertFalse(any(x.get("tree_depth")==3 for x in tree["workers"]))

    def test_total_node_budget_stops_branch_expansion(self):
        tree=self.workers.execute_tree(
            "KRISHNA",self._request(max_tree_nodes=2),"Mission","local_only"
        )
        self.assertEqual(tree["node_count"],2)
        self.assertTrue(tree["budget"]["budget_exhausted"])

    def test_tree_persistent_memory_is_compact(self):
        self.workers.execute_tree("KRISHNA",self._request(),"Mission","local_only")
        stored=[x for x in self.memory.rows if len(x)>=2 and x[1]=="ephemeral_shishya_tree"][-1]
        compact=stored[3]
        self.assertNotIn("workers",compact)
        self.assertNotIn("edges",compact)
        self.assertEqual(compact["node_count"],4)
        self.assertTrue(compact["all_nodes_destroyed"])

    def test_planner_caps_root_count_to_total_tree_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            bg=BrahmagyanRuntime(Path(tmp)/"bg",GyanStub(),MemoryStub())
            m=bg.create_mission("KRISHNA","Large nested study",rishi_id="kashyapa")
            with patch.dict("os.environ",{
                "KRISHNA_SHISHYA_MAX_PER_REQUEST":"32",
                "KRISHNA_SHISHYA_MAX_TREE_NODES":"5",
            },clear=False):
                plan=bg.shishya_plan(m["mission_id"],count=12)
            self.assertEqual(plan["requested_count"],5)
            self.assertEqual(plan["tree_policy"]["max_nodes"],5)


if __name__=="__main__":
    unittest.main()
