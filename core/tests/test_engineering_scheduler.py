import unittest

from krishna_core.engineering_scheduler import EngineeringScheduler


class EngineeringSchedulerTests(unittest.TestCase):
    def test_dependency_waves_and_cloud_truth_boundary(self):
        s = EngineeringScheduler(max_workers=8)
        plan = s.plan([
            {"id": "api", "role": "backend", "estimate_minutes": 60, "privacy": "approved_cloud"},
            {"id": "ui", "role": "frontend", "estimate_minutes": 50, "privacy": "approved_cloud"},
            {"id": "integrate", "role": "integration", "estimate_minutes": 20, "depends_on": ["api", "ui"], "privacy": "local_only"},
        ], deadline_minutes=90, local_slots=2, free_cloud_available=True)
        self.assertEqual(plan["dependency_waves"][0]["parallel_ready"], 2)
        self.assertEqual(plan["dependency_waves"][1]["parallel_ready"], 1)
        first = plan["dependency_waves"][0]["batches"][0][0]
        self.assertTrue(first["reasoning_route"]["cloud_allowed"])
        final = plan["dependency_waves"][1]["batches"][0][0]
        self.assertFalse(final["reasoning_route"]["cloud_allowed"])
        self.assertFalse(plan["execution_truth"]["free_cloud_is_compute_node"])

    def test_cycle_is_rejected(self):
        s = EngineeringScheduler()
        with self.assertRaises(ValueError):
            s.plan([
                {"id": "a", "role": "backend", "estimate_minutes": 10, "depends_on": ["b"]},
                {"id": "b", "role": "frontend", "estimate_minutes": 10, "depends_on": ["a"]},
            ], deadline_minutes=30)


if __name__ == "__main__":
    unittest.main()
