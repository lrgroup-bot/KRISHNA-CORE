import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.rishi_council import RishiCouncil
from krishna_core.science_atlas import (
    ScienceAtlas, ScienceFrontierScheduler, FIELD_RISHI_MAP, OPENALEX_COUNTS
)


class MemoryStub:
    def __init__(self):
        self.audit_rows=[]
        self.rows=[]
    def audit(self,*args):
        self.audit_rows.append(args)
    def remember(self,*args):
        self.rows.append(args)


class GyanStub:
    def propose(self,*args,**kwargs):
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class FakeAtlas(ScienceAtlas):
    def _list_endpoint(self,name,select=None,max_rows=None):
        rows={
            "domains":[
                {"id":"https://openalex.org/domains/1","display_name":"Life Sciences","description":"life","works_count":10,"cited_by_count":20}
            ],
            "fields":[
                {"id":"https://openalex.org/fields/13","display_name":"Biochemistry, Genetics and Molecular Biology",
                 "description":"genes","domain":{"id":"https://openalex.org/domains/1","display_name":"Life Sciences"},
                 "works_count":100,"cited_by_count":200}
            ],
            "subfields":[
                {"id":"https://openalex.org/subfields/1311","display_name":"Genetics",
                 "description":"genetics","domain":{"id":"https://openalex.org/domains/1","display_name":"Life Sciences"},
                 "field":{"id":"https://openalex.org/fields/13","display_name":"Biochemistry, Genetics and Molecular Biology"},
                 "works_count":80,"cited_by_count":160}
            ],
            "topics":[
                {"id":"https://openalex.org/topics/T1","display_name":"Epigenetic Regulation and Aging",
                 "description":"aging and epigenetics","keywords":["epigenetics","aging"],
                 "domain":{"id":"https://openalex.org/domains/1","display_name":"Life Sciences"},
                 "field":{"id":"https://openalex.org/fields/13","display_name":"Biochemistry, Genetics and Molecular Biology"},
                 "subfield":{"id":"https://openalex.org/subfields/1311","display_name":"Genetics"},
                 "works_count":500,"cited_by_count":900},
                {"id":"https://openalex.org/topics/T2","display_name":"DNA Repair and Cancer",
                 "description":"dna repair oncology","keywords":["DNA repair","cancer"],
                 "domain":{"id":"https://openalex.org/domains/1","display_name":"Life Sciences"},
                 "field":{"id":"https://openalex.org/fields/13","display_name":"Biochemistry, Genetics and Molecular Biology"},
                 "subfield":{"id":"https://openalex.org/subfields/1311","display_name":"Genetics"},
                 "works_count":700,"cited_by_count":1200},
            ],
        }[name]
        return rows[:max_rows] if max_rows else rows


class ScienceAtlasTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.council=RishiCouncil()
        self.atlas=FakeAtlas(Path(self.tmp.name)/"atlas",self.council,self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_openalex_reference_hierarchy_matches_current_design(self):
        self.assertEqual(OPENALEX_COUNTS["domains"],4)
        self.assertEqual(OPENALEX_COUNTS["fields"],26)
        self.assertEqual(OPENALEX_COUNTS["subfields"],252)
        self.assertGreaterEqual(OPENALEX_COUNTS["topics"],4500)
        self.assertEqual(len(FIELD_RISHI_MAP),26)

    def test_full_taxonomy_sync_is_persistent_and_searchable(self):
        status=self.atlas.sync_openalex(include_topics=True)
        self.assertEqual(status["loaded_counts"]["domains"],1)
        self.assertEqual(status["loaded_counts"]["fields"],1)
        self.assertEqual(status["loaded_counts"]["subfields"],1)
        self.assertEqual(status["loaded_counts"]["topics"],2)
        found=self.atlas.search("aging","topics",10)
        self.assertEqual(len(found),1)
        reopened=ScienceAtlas(Path(self.tmp.name)/"atlas",self.council,self.memory)
        self.assertEqual(reopened.status()["loaded_counts"]["topics"],2)

    def test_dna_routes_to_genetics_medical_physical_and_evidence_rishis(self):
        out=self.atlas.route(
            "DNA repair, genomic stability and epigenetic aging",
            "Biochemistry, Genetics and Molecular Biology",
            "Life Sciences",8
        )
        ids=[x["id"] for x in out["rishis"]]
        for rid in ("kashyapa","sushruta","kanada","gautama","veda-vyasa"):
            self.assertIn(rid,ids)
        self.assertEqual(out["safety"]["mode"],"biomedical_conceptual_research")

    def test_frontier_dna_questions_go_beyond_definition_without_wet_lab_protocol(self):
        out=self.atlas.frontier_questions("DNA, aging and cancer",limit=12)
        text="\n".join(out["questions"]).lower()
        self.assertIn("causal",text)
        self.assertIn("reversible",text)
        self.assertIn("cancer",text)
        self.assertIn("preclinical",text)
        self.assertNotIn("guide rna sequence",text)
        self.assertNotIn("transfection protocol",text)
        self.assertNotIn("culture at",text)
        self.assertIn("wet-lab genome editing",out["safety"]["blocked"])

    def test_biosecurity_subject_is_forced_to_high_level_only(self):
        out=self.atlas.frontier_questions("pathogen virulence and immune evasion",limit=5)
        self.assertEqual(out["safety"]["mode"],"biosecurity_high_level_only")
        self.assertIn("blocked",out["safety"])
        self.assertIn("procedural pathogen enhancement",out["safety"]["blocked"])

    def test_science_field_routing_assigns_capability_specific_teams(self):
        physics=self.atlas.route("quantum sensing","Physics and Astronomy","Physical Sciences",8)
        pids=[x["id"] for x in physics["rishis"]]
        self.assertIn("kanada",pids)
        self.assertIn("atri",pids)
        self.assertIn("vishwamitra",pids)

        ecology=self.atlas.route("climate ecology","Environmental Science","Life Sciences",8)
        eids=[x["id"] for x in ecology["rishis"]]
        self.assertIn("kashyapa",eids)
        self.assertIn("agastya",eids)
        self.assertIn("atri",eids)

    def test_research_coverage_prioritizes_unresearched_topics(self):
        self.atlas.sync_openalex(True)
        first=self.atlas.next_subject("topic")
        self.assertEqual(first["subject"],"DNA Repair and Cancer")
        self.atlas.record_research(first["id"],"m1","r1","L4",0)
        second=self.atlas.next_subject("topic")
        self.assertEqual(second["subject"],"Epigenetic Regulation and Aging")

    def test_seed_curiosity_creates_mechanism_counterfactual_queue(self):
        bg=BrahmagyanRuntime(Path(self.tmp.name)/"bg",GyanStub(),self.memory)
        out=self.atlas.seed_curiosity(bg,"DNA, aging and cancer",project="KRISHNA",limit=6)
        self.assertEqual(len(out["queued"]),6)
        queued=bg.curiosity_queue("KRISHNA",10)
        self.assertEqual(len(queued),6)
        self.assertTrue(all(x["signals"].get("science_atlas")==1.0 for x in queued))

    def test_preferred_science_team_survives_brahmagyan_perspective_planning(self):
        bg=BrahmagyanRuntime(Path(self.tmp.name)/"bg2",GyanStub(),self.memory)
        m=bg.create_mission(
            "KRISHNA","DNA repair and cancer aging","What mechanisms matter?",
            rishi_id="kashyapa",knowledge_track="modern_science",
        )
        out=bg.perspective_plan(
            m["mission_id"],8,
            preferred_rishis=["kashyapa","sushruta","kanada","bharadvaja","gautama","veda-vyasa"],
        )
        ids=[x["rishi_id"] for x in out["perspectives"]]
        for rid in ("kashyapa","sushruta","kanada","bharadvaja","gautama","veda-vyasa"):
            self.assertIn(rid,ids)

    def test_scheduler_is_resource_bounded_and_not_busy_loop(self):
        calls=[]
        scheduler=ScienceFrontierScheduler(lambda:calls.append("tick") or {"ran":False},interval_seconds=1)
        self.assertGreaterEqual(scheduler.interval_seconds,300)
        self.assertEqual(scheduler.run_count,0)
        self.assertFalse(scheduler.status()["running"])

    def test_orchestrator_and_http_science_surfaces_exist(self):
        root=Path(__file__).resolve().parents[1]
        orch=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        server=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for token in (
            "ScienceAtlas",
            "brahmagyan.science.status",
            "brahmagyan.science.sync",
            "brahmagyan.science.frontier.seed",
            "brahmagyan.science.frontier.run",
            "brahmagyan.science.background.tick",
        ):
            self.assertIn(token,orch)
        self.assertIn("/api/brahmagyan/science/status",server)
        self.assertIn("/api/brahmagyan/science/frontier",server)
        self.assertIn("KRISHNA_SCIENCE_RESEARCH_INTERVAL_SECONDS",server)


if __name__=="__main__":
    unittest.main()
