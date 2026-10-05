import unittest

from krishna_core.project_graph import ProjectGraph


class ProjectGraphIntelligenceTests(unittest.TestCase):
    def make_graph(self):
        graph = ProjectGraph()
        graph.upsert_node("core.py", "module")
        graph.upsert_node("service.py", "module")
        graph.upsert_node("api.py", "module")
        graph.upsert_node("test_api.py", "test", {"test": True})
        graph.upsert_node("unrelated.py", "module")
        graph.link("service.py", "core.py")
        graph.link("api.py", "service.py")
        graph.link("test_api.py", "api.py", "tests")
        return graph

    def test_impact_walks_reverse_dependencies_with_evidence(self):
        report = self.make_graph().impact(["core.py"], depth=4)
        names = [row["name"] for row in report["impacted"]]
        self.assertIn("service.py", names)
        self.assertIn("api.py", names)
        self.assertNotIn("unrelated.py", names)
        self.assertEqual([row["name"] for row in report["tests"]], ["test_api.py"])
        api = next(row for row in report["impacted"] if row["name"] == "api.py")
        self.assertEqual(api["distance"], 2)
        self.assertEqual(api["path"], ["core.py", "service.py", "api.py"])
        self.assertEqual(api["evidence"][-1]["target"], "service.py")
        self.assertEqual(report["evidence_policy"], "proven graph edges only; missing relationships remain unknown")

    def test_impact_prefers_shortest_proven_path(self):
        graph = self.make_graph()
        graph.link("api.py", "core.py")
        api = next(row for row in graph.impact(["core.py"])["impacted"] if row["name"] == "api.py")
        self.assertEqual(api["distance"], 1)
        self.assertEqual(api["path"], ["core.py", "api.py"])

    def test_hotspots_use_observed_history_and_return_evidence(self):
        graph = self.make_graph()
        report = graph.change_hotspots([
            ["core.py", "service.py"],
            ["core.py", "service.py"],
            ["core.py", "api.py"],
            ["unrelated.py"],
        ])
        self.assertEqual(report["commit_count"], 4)
        self.assertFalse(report["mutated"])
        by_name = {row["name"]: row for row in report["hotspots"]}
        self.assertEqual(by_name["core.py"]["changes"], 3)
        self.assertEqual(by_name["core.py"]["cochange_weight"], 3)
        partners = {x["name"]: x["count"] for x in by_name["core.py"]["cochange_partners"]}
        self.assertEqual(partners["service.py"], 2)
        self.assertEqual(partners["api.py"], 1)
        self.assertGreater(by_name["core.py"]["score"], by_name["unrelated.py"]["score"])

    def test_hotspot_analysis_deduplicates_files_inside_a_commit(self):
        graph = ProjectGraph()
        report = graph.change_hotspots([["a.py", "a.py", "b.py"]])
        rows = {row["name"]: row for row in report["hotspots"]}
        self.assertEqual(rows["a.py"]["changes"], 1)
        self.assertEqual(rows["a.py"]["cochange_weight"], 1)


if __name__ == "__main__":
    unittest.main()
