import re
import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.rishi_live_research import RishiLiveResearchExecutor


class MemoryStub:
    def __init__(self):
        self.audit_rows=[]
        self.rows=[]
    def audit(self,action,status,details):
        self.audit_rows.append((action,status,details))
    def remember(self,project,kind,content,metadata=None):
        self.rows.append((project,kind,content,metadata or {}))


class GyanStub:
    def __init__(self):
        self.proposals=[]
    def propose(self,*args,**kwargs):
        row={"approval_id":f"g{len(self.proposals)+1}","args":args,"kwargs":kwargs}
        self.proposals.append(row)
        return {"approval_id":row["approval_id"],"stored":False,"requires_user_approval":True}


class GarudaStub:
    def __init__(self):
        self.calls=[]
    def scout(self,project,goal,limit=10):
        self.calls.append((project,goal,limit))
        if "contradicting evidence" in goal:
            rows=[
                {
                    "title":"Independent replication",
                    "url":"https://arxiv.org/abs/2601.00003",
                    "summary":"A separate experiment reports results consistent with the narrow claim.",
                    "source":"arxiv","relevance":5,"suspicious":False,"fingerprint":"fp3",
                }
            ]
        else:
            rows=[
                {
                    "title":"Primary study A",
                    "url":"https://arxiv.org/abs/2601.00001",
                    "summary":"Study A reports a measured effect under defined laboratory conditions.",
                    "source":"arxiv","relevance":5,"suspicious":False,"fingerprint":"fp1",
                },
                {
                    "title":"Primary study B",
                    "url":"https://arxiv.org/abs/2601.00002",
                    "summary":"Study B independently reports the same narrow measured effect with limitations.",
                    "source":"arxiv","relevance":4,"suspicious":False,"fingerprint":"fp2",
                },
            ]
        return {
            "agent":"Garuda","role":"research_and_evidence","project":project,"goal":goal,
            "web":rows,"github":[],"errors":{},"coverage":["research_papers"],
        }


class ModelStub:
    def __init__(self, fail_claim_extraction=False):
        self.calls=[]
        self.fail_claim_extraction=fail_claim_extraction

    @staticmethod
    def ids(prompt):
        return list(dict.fromkeys(re.findall(r"\[([a-f0-9]{20})\]",prompt)))

    @staticmethod
    def claim_ids(prompt):
        return list(dict.fromkeys(re.findall(
            r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
            prompt,re.I
        )))

    def __call__(self,prompt,privacy="approved_cloud",project="KRISHNA",actor="test"):
        import json
        self.calls.append((actor,privacy,project))
        if actor=="rishi-live-claim-extractor":
            if self.fail_claim_extraction:
                return {"provider":"stub","text":"not-json"}
            ids=self.ids(prompt)[:2]
            return {"provider":"stub","text":json.dumps({
                "claims":[{
                    "claim":"A measured effect was reported under defined laboratory conditions.",
                    "knowledge_track":"modern_science",
                    "source_ids":ids,
                    "context_summary":"The supplied primary-study summaries report the effect but do not establish universal validity.",
                    "confidence":0.78,
                    "uncertainties":["External validity remains uncertain."],
                }]
            })}
        if actor=="rishi-live-counter-evidence":
            ids=self.ids(prompt)
            return {"provider":"stub","text":json.dumps({
                "relations":[
                    {"source_id":sid,"relation":"supports","confidence":0.72,"notes":"The snippet reports a consistent result."}
                    for sid in ids
                ]
            })}
        if actor=="rishi-live-gautama":
            ids=self.ids(prompt)
            return {"provider":"stub","text":json.dumps({
                "reviews":[
                    {"source_id":sid,"supported":True,"relation":"supports","confidence":0.8,"notes":"The supplied snippet supports the narrow claim."}
                    for sid in ids
                ],
                "overall_confidence":0.82,
            })}
        if actor=="rishi-live-gautama-debate":
            return {"provider":"stub","text":json.dumps({
                "evidence_sufficient":True,
                "notes":"Multiple independent recorded sources support the narrow claim.",
                "unresolved":["External validity is not established."],
            })}
        if actor=="rishi-live-vyasa-debate":
            return {"provider":"stub","text":json.dumps({
                "synthesis":"The recorded evidence supports the narrow laboratory claim while external validity remains unresolved."
            })}
        if actor.startswith("rishi-live-debate-"):
            ids=self.claim_ids(prompt)
            return {"provider":"stub","text":json.dumps({
                "position":"The narrow claim is supported, but scope and falsification conditions must remain explicit.",
                "claim_ids":ids[:1],
                "objections":["Do not generalize beyond the measured conditions."],
            })}
        if actor=="rishi-live-test-plan":
            ids=self.claim_ids(prompt)
            return {"provider":"stub","text":json.dumps({
                "tests":[
                    {"claim_id":cid,"test":"Replicate the measurement under pre-registered conditions.","required_evidence":["raw measurements","protocol"]}
                    for cid in ids[:1]
                ]
            })}
        if actor=="rishi-live-final-vyasa":
            return {"provider":"stub","text":json.dumps({
                "summary":"The mission produced a source-grounded L4 claim; planned tests were not executed.",
                "supported":["The narrow laboratory claim has multiple supporting sources."],
                "contested":[],
                "unknowns":["External validity remains unknown."],
                "next_evidence":["Run the planned replication."],
            })}
        raise AssertionError(f"unexpected actor {actor}")


class RishiLiveResearchV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.gyan=GyanStub()
        self.bg=BrahmagyanRuntime(Path(self.tmp.name)/"bg",self.gyan,self.memory)
        self.garuda=GarudaStub()

    def tearDown(self):
        self.tmp.cleanup()

    def make_executor(self,model):
        return RishiLiveResearchExecutor(
            Path(self.tmp.name)/"live",self.bg,self.garuda,model,self.memory
        )

    def test_end_to_end_live_run_reaches_only_evidence_supported_maturity(self):
        model=ModelStub()
        live=self.make_executor(model)
        out=live.run(
            "KRISHNA","Laboratory materials science",
            "Does the recorded evidence support the measured effect?",
            rishi_id="kanada",knowledge_track="modern_science",
            stakes="high",privacy="local_only",source_limit=4,max_perspectives=3,max_claims=3,
        )
        self.assertEqual(out["run"]["status"],"completed")
        self.assertEqual(out["mission"]["phase"],"report")
        self.assertEqual(len(out["dossier"]["claims"]),1)
        claim=self.bg.claim(out["dossier"]["claims"][0]["claim_id"])
        self.assertEqual(claim["maturity"],"L4")
        self.assertEqual(claim["verified_by"],"gautama")
        self.assertEqual(claim["compiled_by"],"veda-vyasa")
        self.assertNotIn(claim["maturity"],{"L5","L6"})
        self.assertTrue(out["test_plan"]["tests"])
        self.assertTrue(all(x["executed"] is False for x in out["test_plan"]["tests"]))
        self.assertEqual(len(out["gyan_proposals"]),1)
        self.assertTrue(out["policy"]["gyan_is_proposal_only"])
        self.assertTrue(any(a.startswith("rishi-live-debate-") for a,_,_ in model.calls))
        self.assertIn("rishi-live-gautama-debate",[a for a,_,_ in model.calls])
        self.assertIn("rishi-live-vyasa-debate",[a for a,_,_ in model.calls])

    def test_live_run_persists_checkpointed_failure_without_fake_claims(self):
        model=ModelStub(fail_claim_extraction=True)
        live=self.make_executor(model)
        with self.assertRaises(ValueError):
            live.run(
                "KRISHNA","Failure-path research","Can the executor recover state?",
                rishi_id="gautama",knowledge_track="engineering",
                source_limit=3,max_perspectives=2,max_claims=2,
            )
        status=live.status()
        self.assertEqual(status["failed"],1)
        run=live.list(limit=1)[0]
        self.assertEqual(run["status"],"failed")
        self.assertTrue(run["errors"])
        self.assertTrue(any(x["status"]=="failed" for x in run["checkpoints"]))
        mission=self.bg.mission(run["mission_id"])
        self.assertEqual(mission["phase"],"claims")
        self.assertEqual(mission["claim_ids"],[])

    def test_source_ids_are_validated_before_claim_ingestion(self):
        class BadCitationModel(ModelStub):
            def __call__(self,prompt,privacy="approved_cloud",project="KRISHNA",actor="test"):
                import json
                if actor=="rishi-live-claim-extractor":
                    return {"provider":"stub","text":json.dumps({
                        "claims":[{
                            "claim":"Hallucinated claim",
                            "knowledge_track":"modern_science",
                            "source_ids":["not-a-real-source"],
                            "context_summary":"bad","confidence":0.9,"uncertainties":[]
                        }]
                    })}
                return super().__call__(prompt,privacy,project,actor)
        live=self.make_executor(BadCitationModel())
        out=live.run(
            "KRISHNA","Citation validation","Reject unknown source IDs",
            rishi_id="gautama",knowledge_track="modern_science",
            source_limit=3,max_perspectives=2,max_claims=2,auto_propose=False,
        )
        self.assertEqual(out["dossier"]["scorecard"]["claim_count"],0)
        self.assertEqual(out["gyan_proposals"],[])

    def test_orchestrator_and_http_surfaces_exist(self):
        root=Path(__file__).resolve().parents[1]
        orch=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        server=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for token in (
            "RishiLiveResearchExecutor",
            "brahmagyan.live.run",
            "brahmagyan.live.status",
            "brahmagyan_live_run",
            "brahmagyan_live_status",
        ):
            self.assertIn(token,orch)
        self.assertIn("/api/brahmagyan/live/run",server)
        self.assertIn("/api/brahmagyan/live/status",server)


if __name__=="__main__":
    unittest.main()
