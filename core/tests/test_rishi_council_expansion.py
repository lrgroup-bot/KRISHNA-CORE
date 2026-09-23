import tempfile
import unittest
from pathlib import Path

from krishna_core.grand_challenges import BUILTIN_GRAND_CHALLENGES, GrandChallengeRegistry
from krishna_core.rishi_council import RishiCouncil
from krishna_core.rishi_learning import RISHI_RESEARCH_CHARTERS
from krishna_core.science_atlas import FIELD_RISHI_MAP, ScienceAtlas


class MemoryStub:
    def audit(self,*args,**kwargs):
        pass


class ExpandedRishiCouncilTests(unittest.TestCase):
    def setUp(self):
        self.council=RishiCouncil()

    def test_council_expands_to_twenty_nine_permanent_profiles(self):
        ids={x["id"] for x in self.council.list()}
        self.assertEqual(len(ids),29)
        for rid in (
            "aryabhata","brahmagupta","bhaskaracharya","madhava","varahamihira",
            "dhanvantari","nagarjuna","chanakya","baudhayana","pingala",
            "shalihotra","parashara","vishvakarma",
        ):
            self.assertIn(rid,ids)

    def test_every_council_member_has_a_learning_charter(self):
        ids={x["id"] for x in self.council.list()}
        self.assertEqual(set(RISHI_RESEARCH_CHARTERS),ids)
        for rid in ids:
            row=RISHI_RESEARCH_CHARTERS[rid]
            self.assertTrue(row["primary_subjects"])
            self.assertTrue(row["frontier_focus"])
            self.assertTrue(row["classical_lens"])

    def test_new_specialist_subjects_are_present(self):
        self.assertIn("scientific computing",RISHI_RESEARCH_CHARTERS["aryabhata"]["primary_subjects"])
        self.assertIn("drug discovery",RISHI_RESEARCH_CHARTERS["dhanvantari"]["primary_subjects"])
        self.assertIn("meteorology",RISHI_RESEARCH_CHARTERS["varahamihira"]["primary_subjects"])
        self.assertIn("economics",RISHI_RESEARCH_CHARTERS["chanakya"]["primary_subjects"])
        self.assertIn("veterinary science",RISHI_RESEARCH_CHARTERS["shalihotra"]["primary_subjects"])
        self.assertIn("agriculture",RISHI_RESEARCH_CHARTERS["parashara"]["primary_subjects"])

    def test_science_atlas_fields_route_to_new_specialists(self):
        self.assertIn("aryabhata",FIELD_RISHI_MAP["mathematics"])
        self.assertIn("nagarjuna",FIELD_RISHI_MAP["chemistry"])
        self.assertIn("varahamihira",FIELD_RISHI_MAP["earth and planetary sciences"])
        self.assertIn("dhanvantari",FIELD_RISHI_MAP["pharmacology, toxicology and pharmaceutics"])
        self.assertIn("chanakya",FIELD_RISHI_MAP["economics, econometrics and finance"])
        self.assertIn("shalihotra",FIELD_RISHI_MAP["veterinary"])
        self.assertIn("parashara",FIELD_RISHI_MAP["agricultural and biological sciences"])

    def test_topic_router_uses_new_specialists(self):
        with tempfile.TemporaryDirectory() as tmp:
            atlas=ScienceAtlas(Path(tmp),self.council,MemoryStub())
            math_ids=[x["id"] for x in atlas.route("nonlinear optimization and numerical analysis","Mathematics",None,8)["rishis"]]
            self.assertIn("aryabhata",math_ids)
            self.assertIn("bhaskaracharya",math_ids)
            drug_ids=[x["id"] for x in atlas.route("drug discovery and precision medicine","Pharmacology, Toxicology and Pharmaceutics",None,8)["rishis"]]
            self.assertIn("dhanvantari",drug_ids)


class GrandChallengeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.council=RishiCouncil()
        self.registry=GrandChallengeRegistry(Path(self.tmp.name),self.council)

    def tearDown(self):
        self.tmp.cleanup()

    def test_has_broad_builtin_grand_challenge_portfolio(self):
        self.assertGreaterEqual(len(BUILTIN_GRAND_CHALLENGES),27)
        required={
            "amrita","sanjeevani","anuvansh","karkata","manas","aushadhi","raksha_bio",
            "vajra","agni","akash","varsha","anna","yantra","setu","bodhi","shunya",
            "satya","artha","saraswati","suraksha",
        }
        self.assertTrue(required.issubset(set(BUILTIN_GRAND_CHALLENGES)))

    def test_every_project_references_real_rishis(self):
        valid={x["id"] for x in self.council.list()}
        for project in self.registry.list():
            self.assertTrue(project["leads"])
            self.assertTrue(set(project["leads"]).issubset(valid))
            self.assertTrue(set(project["support"]).issubset(valid))

    def test_route_maps_human_problem_to_projects(self):
        ids=[x["project_id"] for x in self.registry.route("DNA repair epigenetic aging longevity",10)]
        self.assertIn("amrita",ids)
        self.assertIn("anuvansh",ids)
        cancer=[x["project_id"] for x in self.registry.route("cancer metastasis drug resistance",10)]
        self.assertIn("karkata",cancer)

    def test_custom_projects_can_be_added_without_source_edit(self):
        row=self.registry.create_custom(
            "my_new_project","My New Project","Research safe water purification",
            ["water purification","sanitation"],["varahamihira","nagarjuna"],
            ["gautama","bharadvaja"],
        )
        self.assertEqual(row["project_id"],"my_new_project")
        reopened=GrandChallengeRegistry(Path(self.tmp.name),self.council)
        self.assertEqual(reopened.get("my_new_project")["name"],"My New Project")

    def test_unknown_rishi_is_rejected_in_custom_project(self):
        with self.assertRaises(ValueError):
            self.registry.create_custom(
                "bad","Bad","Bad",["x"],["not-a-rishi"],[],
            )

    def test_http_and_orchestrator_project_surfaces_exist(self):
        root=Path(__file__).resolve().parents[1]
        orch=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        server=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn("GrandChallengeRegistry",orch)
        self.assertIn("brahmagyan.projects.status",orch)
        self.assertIn("brahmagyan.projects.add",orch)
        self.assertIn("/api/brahmagyan/projects",server)
        self.assertIn("/api/brahmagyan/projects/add",server)


if __name__=="__main__":
    unittest.main()
