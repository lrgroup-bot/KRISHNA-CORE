import tempfile
import unittest
from pathlib import Path
from krishna_core.plugin_runtime import PluginRegistry

class PluginRegistryTests(unittest.TestCase):
    def test_builtin_and_arbitrary_plugin_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            ids={p["id"] for p in r.list()}
            for builtin in ("pc","github","ollama","mcp-servers","activepieces"):
                self.assertIn(builtin,ids)
            free={p["id"] for p in r.list() if p.get("free")}
            self.assertTrue({"ollama","mcp-servers","activepieces"}.issubset(free))
            added=r.add({"name":"My Tool","kind":"mcp","permissions":["read"],"project_scope":["*"],"free":True})
            self.assertEqual(added["id"],"my-tool")
            self.assertFalse(added["enabled"])
            with self.assertRaises(RuntimeError):
                r.set_enabled("my-tool",True)
            self.assertEqual(r.set_credential("my-tool","vault-ref")["credential_ref"],"vault-ref")
            self.assertEqual(r.clear_credential("my-tool")["credential_ref"],"")
            self.assertTrue(r.remove("my-tool"))

    def test_retired_marketplaces_are_purged_and_cannot_be_readded(self):
        retired={"amazon-sp-api","amazon-associates","flipkart-seller","flipkart-affiliate","meesho-seller","alibaba-global","shopify"}
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)/"plugins.json"
            state.write_text('[{"id":"shopify","name":"Shopify","kind":"connector","free":true}]',encoding="utf-8")
            r=PluginRegistry(Path(td))
            ids={p["id"] for p in r.list()}
            self.assertTrue(retired.isdisjoint(ids))
            with self.assertRaises(PermissionError):
                r.add({"name":"Amazon helper","kind":"http","endpoint":"https://example.com","free":True})

    def test_only_ready_plugins_can_be_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            self.assertTrue(r.set_enabled("ollama",True)["enabled"])
            with self.assertRaises(RuntimeError):
                r.set_enabled("gmail",True)
            with self.assertRaises(PermissionError):
                r.set_enabled("blackbox-ai",True)
            added=r.add({"name":"Free HTTP","kind":"http","endpoint":"https://example.com","auth_type":"none","free":True})
            self.assertEqual(added["runtime_state"],"ready")
            self.assertTrue(r.set_enabled(added["id"],True)["enabled"])

    def test_builtin_cannot_be_removed(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            with self.assertRaises(PermissionError):
                r.remove("pc")

if __name__=="__main__":
    unittest.main()
