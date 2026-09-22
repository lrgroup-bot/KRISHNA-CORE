import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.rishi_council import RishiCouncil, MEDICAL_ENGINEERING_DOMAINS


class MemoryStub:
    def audit(self,*args,**kwargs):
        pass
    def remember(self,*args,**kwargs):
        pass


class GyanStub:
    def propose(self,*args,**kwargs):
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class MedicalEngineeringRishiTests(unittest.TestCase):
    def setUp(self):
        self.council=RishiCouncil()

    def test_all_eight_medical_engineering_domains_are_registered(self):
        expected={
            "biomedical_engineering",
            "biomechanical_engineering",
            "neural_engineering",
            "medical_imaging",
            "biomaterials",
            "clinical_engineering",
            "medical_radiation_sciences",
            "medical_ai_engineering",
        }
        self.assertEqual(set(MEDICAL_ENGINEERING_DOMAINS),expected)

    def test_biomechanics_routes_to_sushruta_kanada_and_bharadvaja(self):
        team=self.council.specialist_team(
            "Biomechanical engineering for gait, tissue mechanics and implant loading",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("kanada",ids)
        self.assertIn("bharadvaja",ids)
        self.assertIn("gautama",ids)
        self.assertIn("veda-vyasa",ids)

    def test_neural_engineering_routes_medical_cognition_and_method_experts(self):
        team=self.council.specialist_team(
            "Neural engineering and brain-computer interface research",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("kapila",ids)
        self.assertIn("patanjali",ids)
        self.assertIn("bharadvaja",ids)
        self.assertIn("gautama",ids)

    def test_medical_imaging_routes_physics_observation_and_clinical_experts(self):
        team=self.council.specialist_team(
            "Medical imaging with MRI CT ultrasound and reconstruction physics",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("kanada",ids)
        self.assertIn("atri",ids)
        self.assertIn("gautama",ids)

    def test_biomaterials_routes_materials_and_frontier_experts(self):
        team=self.council.specialist_team(
            "Biomaterials and tissue scaffold biocompatibility",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("kanada",ids)
        self.assertIn("vishwamitra",ids)
        self.assertIn("bharadvaja",ids)

    def test_clinical_engineering_adds_reliability_and_governance(self):
        team=self.council.specialist_team(
            "Clinical engineering and hospital medical equipment lifecycle management",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("bharadvaja",ids)
        self.assertIn("jamadagni",ids)
        self.assertIn("vashistha",ids)

    def test_radiation_sciences_routes_physics_observation_and_safety(self):
        team=self.council.specialist_team(
            "Medical radiation sciences, dosimetry and nuclear medicine",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("kanada",ids)
        self.assertIn("atri",ids)
        self.assertIn("jamadagni",ids)

    def test_medical_ai_routes_clinical_ai_evidence_and_security(self):
        team=self.council.specialist_team(
            "AI and engineering for medical applications including diagnostic AI",6
        )
        ids=[x["id"] for x in team["members"]]
        self.assertIn("sushruta",ids)
        self.assertIn("vishwamitra",ids)
        self.assertIn("bharadvaja",ids)
        self.assertIn("gautama",ids)
        self.assertIn("jamadagni",ids)

    def test_specialist_team_has_historical_role_disclaimer(self):
        team=self.council.specialist_team("biomedical engineering",6)
        self.assertIn("do not claim",team["policy"].lower())

    def test_brahmagyan_perspective_plan_inherits_medical_domain_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bg=BrahmagyanRuntime(Path(tmp),GyanStub(),MemoryStub())
            m=bg.create_mission(
                "KRISHNA",
                "Neural engineering brain-computer interface",
                rishi_id="sushruta",
                knowledge_track="modern_science",
            )
            p=bg.perspective_plan(m["mission_id"],6)
            ids={x["rishi_id"] for x in p["perspectives"]}
            self.assertIn("sushruta",ids)
            self.assertIn("kapila",ids)
            self.assertIn("patanjali",ids)
            self.assertIn("gautama",ids)


if __name__=="__main__":
    unittest.main()
