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
            added=r.add({"name":"My Tool","kind":"mcp","permissions":["read"],"project_scope":["*"]})
            self.assertEqual(added["id"],"my-tool")
            self.assertFalse(added["enabled"])
            self.assertTrue(r.set_enabled("my-tool",True)["enabled"])
            self.assertEqual(r.set_credential("my-tool","vault-ref")["credential_ref"],"vault-ref")
            self.assertEqual(r.clear_credential("my-tool")["credential_ref"],"")
            self.assertTrue(r.remove("my-tool"))

    def test_builtin_cannot_be_removed(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            with self.assertRaises(PermissionError):
                r.remove("pc")

if __name__=="__main__":
    unittest.main()
