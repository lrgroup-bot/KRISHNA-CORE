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
        self.assertIn("proven graph edges only", report["evidence_policy"])

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


    def test_cycles_return_closed_edge_evidence(self):
        graph = ProjectGraph()
        for name in ("a", "b", "c"):
            graph.upsert_node(name, "module")
        graph.link("a", "b")
        graph.link("b", "c")
        graph.link("c", "a")
        report = graph.cycles()
        self.assertFalse(report["passed"])
        self.assertEqual(report["cycle_count"], 1)
        self.assertEqual(len(report["cycles"][0]["edges"]), 3)
        self.assertEqual(report["cycles"][0]["nodes"][0], report["cycles"][0]["nodes"][-1])

    def test_architecture_deny_rule_reports_exact_edge(self):
        graph = ProjectGraph()
        graph.upsert_node("ui/home", "ui")
        graph.upsert_node("db/store", "storage")
        graph.link("ui/home", "db/store")
        report = graph.check_architecture_rules([
            {"mode": "deny", "source_kind": "ui", "target_kind": "storage"}
        ])
        self.assertFalse(report["passed"])
        self.assertEqual(report["violation_count"], 1)
        self.assertEqual(
            report["violations"][0]["edge"],
            {"source": "ui/home", "relation": "depends_on", "target": "db/store"},
        )

    def test_architecture_allow_only_rule_accepts_declared_layer(self):
        graph = ProjectGraph()
        graph.upsert_node("ui/home", "ui")
        graph.upsert_node("api/public", "api")
        graph.link("ui/home", "api/public")
        report = graph.check_architecture_rules([
            {"mode": "allow_only", "source_kind": "ui", "target_kinds": ["api"]}
        ])
        self.assertTrue(report["passed"])
        self.assertEqual(report["violation_count"], 0)

    def test_architecture_rules_fail_closed_on_unknown_nodes(self):
        graph = ProjectGraph()
        graph.upsert_node("known", "module")
        graph.link("known", "missing")
        report = graph.check_architecture_rules([])
        self.assertFalse(report["passed"])
        self.assertEqual(report["unknown_edge_count"], 1)
        self.assertEqual(report["unknown_edges"][0]["missing_nodes"], ["missing"])


    def test_impact_confidence_refuses_unknown_seed_safety_claim(self):
        graph = self.make_graph()
        report = graph.impact(["missing.py"])
        self.assertEqual(report["confidence_label"], "INSUFFICIENT")
        self.assertEqual(report["unknown_seeds"], ["missing.py"])
        self.assertFalse(report["safe_to_claim_no_impact"])

    def test_impact_confidence_reports_dangling_graph_nodes(self):
        graph = ProjectGraph()
        graph.upsert_node("api.py", "module")
        graph.link("api.py", "unregistered.py")
        report = graph.impact(["api.py"])
        self.assertEqual(report["confidence_label"], "PARTIAL")
        self.assertEqual(report["graph_evidence"]["dangling_nodes"], ["unregistered.py"])
        self.assertFalse(report["safe_to_claim_no_impact"])

    def test_zero_impact_is_claimable_only_for_complete_known_graph(self):
        graph = ProjectGraph()
        graph.upsert_node("isolated.py", "module")
        report = graph.impact(["isolated.py"])
        self.assertEqual(report["confidence_label"], "GRAPH_COMPLETE_FOR_KNOWN_EDGES")
        self.assertTrue(report["safe_to_claim_no_impact"])


if __name__ == "__main__":
    unittest.main()
