import tempfile
import unittest
from krishna_core.garuda_repair_guides import GuideStep, create_guide, save_guide, guide_summary

class RepairGuideTests(unittest.TestCase):
    def test_original_guide_deterministic(self):
        steps=[GuideStep("Observe", "Collect the device error message", verification="Error logged")]
        a=create_guide("Laptop Model A","Investigate startup issue","easy",10,steps)
        b=create_guide("Laptop Model A","Investigate startup issue","easy",10,steps)
        self.assertEqual(a.guide_id,b.guide_id)
        self.assertEqual(guide_summary(a)["steps"],1)
    def test_immutable_storage(self):
        guide=create_guide("Laptop A","Check airflow","easy",5,[GuideStep("Inspect","Check external vents")])
        with tempfile.TemporaryDirectory() as d:
            save_guide(guide,d)
            with self.assertRaises(FileExistsError):
                save_guide(guide,d)
    def test_reject_empty_steps(self):
        with self.assertRaises(ValueError):
            create_guide("Laptop A","Check airflow","easy",5,[])
    def test_reject_invalid_media(self):
        with self.assertRaises(ValueError):
            create_guide("Laptop A","Check airflow","easy",5,[GuideStep("Inspect","Check vents",media_refs=("../bad",))])
if __name__=="__main__":
    unittest.main()
