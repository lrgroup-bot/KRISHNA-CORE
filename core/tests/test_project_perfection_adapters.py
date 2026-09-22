import unittest
from unittest.mock import patch

from krishna_core.project_perfection_adapters import (
    ApiFuzzAdapter, ArtifactRetest, MutationVerifier, RegressionGenerator, RouteStateGraph, VisualEditIntent,
)


class AdapterTests(unittest.TestCase):
    def test_state_graph_and_regression(self):
        graph=RouteStateGraph().build({"url":"http://localhost/","evidence":[
            {"before":"http://localhost/","after":"http://localhost/settings","label":"Settings","ok":True}
        ]})
        self.assertEqual(graph["node_count"],2)
        src=RegressionGenerator().generate("demo",graph)
        self.assertIn("/settings",src)
        self.assertIn("KRISHNA_BASE_URL",src)
        self.assertIn("console",src)

    def test_api_fuzz_prefers_current_st_cli_and_url_flag(self):
        with patch("krishna_core.project_perfection_adapters.shutil.which") as which:
            which.side_effect=lambda name: "/tools/st" if name=="st" else None
            cmd=ApiFuzzAdapter.command("http://localhost/openapi.json","http://localhost:9000")
        self.assertEqual(cmd[:3],["/tools/st","run","http://localhost/openapi.json"])
        self.assertIn("--url",cmd)
        self.assertNotIn("--base-url",cmd)

    def test_api_fuzz_can_use_uvx_provisioning(self):
        with patch("krishna_core.project_perfection_adapters.shutil.which") as which, \
             patch("krishna_core.project_perfection_adapters.importlib.util.find_spec",return_value=None):
            which.side_effect=lambda name: "/tools/uvx" if name=="uvx" else None
            cmd=ApiFuzzAdapter.command("schema.yaml")
        self.assertEqual(cmd[:3],["/tools/uvx","schemathesis","run"])

    def test_generated_regression_replays_discovered_state_locator(self):
        graph={"nodes":[{"url":"http://localhost/"}],"edges":[{
            "source":"http://localhost/","target":"http://localhost/settings",
            "action":"click","role":"button","name":"Settings","selector":"#settings"
        }]}
        src=RegressionGenerator().generate("demo",graph)
        self.assertIn("getByRole",src)
        self.assertIn("Settings",src)
        self.assertIn("state 1",src)

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
