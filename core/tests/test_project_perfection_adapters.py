import unittest

from krishna_core.project_perfection_adapters import (
    ArtifactRetest, MutationVerifier, RegressionGenerator, RouteStateGraph, VisualEditIntent,
)


class AdapterTests(unittest.TestCase):
    def test_state_graph_and_regression(self):
        graph=RouteStateGraph().build({"url":"http://localhost/","evidence":[
            {"before":"http://localhost/","after":"http://localhost/settings","label":"Settings","ok":True}
        ]})
        self.assertEqual(graph["node_count"],2)
        src=RegressionGenerator().generate("demo",graph)
        self.assertIn("localhost/settings",src)
        self.assertIn("console",src)

    def test_mutation_requires_all_detected(self):
        self.assertFalse(MutationVerifier().score([{"detected":True},{"detected":False}])["passed"])
        self.assertTrue(MutationVerifier().score([{"detected":True}])["passed"])

    def test_artifact_retest_not_build_only(self):
        c=ArtifactRetest().contract("apk","app.apk")
        self.assertIn("install",c["steps"])
        self.assertIn("ui_e2e",c["steps"])

    def test_visual_edit_requires_selector(self):
        with self.assertRaises(ValueError):
            VisualEditIntent().normalize({"action":"move"})
        row=VisualEditIntent().normalize({"action":"move","selector":"#save","to_box":[1,2,3,4]})
        self.assertTrue(row["requires_regression"])


if __name__=="__main__":
    unittest.main()
