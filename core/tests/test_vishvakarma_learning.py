import tempfile,unittest
from krishna_core.vishvakarma_learning import *
from krishna_core.vishvakarma_curriculum import CURRICULUM
class T(unittest.TestCase):
 def test_curriculum(self):self.assertIn("Playwright CLI",CURRICULUM)
 def test_pipeline(self):
  with tempfile.TemporaryDirectory() as d:
   p=VishvakarmaLearning(d);x=ResearchLesson("repo","commit","MIT","design","selective loading","docs")
   self.assertTrue(p.ingest(x)["brahma_review_required"]);self.assertEqual(p.verify(x)["status"],"verified")
if __name__=="__main__":unittest.main()
