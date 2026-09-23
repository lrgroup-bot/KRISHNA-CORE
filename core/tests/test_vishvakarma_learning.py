import tempfile
import unittest

from krishna_core.vishvakarma_curriculum import CURRICULUM
from krishna_core.vishvakarma_learning import ResearchLesson, VishvakarmaLearning


class VishvakarmaLearningTests(unittest.TestCase):
    def test_curriculum_contains_browser_and_component_evidence(self):
        self.assertIn("Playwright CLI",CURRICULUM)
        self.assertIn("Storybook",CURRICULUM)

    def test_candidate_requires_provenance_and_brahma_review(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=VishvakarmaLearning(td)
            lesson=ResearchLesson("repo","commit","MIT","design","selective loading","docs")
            row=runtime.ingest(lesson)
            self.assertTrue(row["brahma_review_required"])
            verified=runtime.verify(lesson)
            self.assertEqual(verified["status"],"verified")
            self.assertFalse(verified["brahma_review_required"])

    def test_missing_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=VishvakarmaLearning(td)
            with self.assertRaises(ValueError):
                runtime.ingest(ResearchLesson("repo","commit","MIT","design","lesson",""))


if __name__=="__main__":
    unittest.main()
