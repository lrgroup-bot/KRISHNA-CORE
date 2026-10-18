import unittest
from tools.sudarshan_reconstruction import ReconstructionRequest, create_plan

class ReconstructionTests(unittest.TestCase):
    def test_requires_authorization(self):
        with self.assertRaises(PermissionError):
            create_plan(ReconstructionRequest("sample app", "android", False, ("search",)))
    def test_independent_feature_plan(self):
        result = create_plan(ReconstructionRequest("sample app", "website", True, ("search", "cart", "search")))
        self.assertEqual(len(result["features"]), 2)
        self.assertFalse(result["release_ready"])
        self.assertFalse(result["execution_enabled"])
        self.assertIn("credentials", result["excluded_material"])
    def test_empty_feature_list_rejected(self):
        with self.assertRaises(ValueError):
            create_plan(ReconstructionRequest("sample app", "desktop", True, ()))
if __name__ == "__main__":
    unittest.main()
