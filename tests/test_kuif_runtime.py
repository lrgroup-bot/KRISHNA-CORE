import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kuif.identity import Principal
from kuif.runtime import Runtime, RuntimeConfig


class KuifRuntimeTests(unittest.TestCase):
    def test_runtime_denies_cross_project_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig(str(Path(tmp) / "memory.db"), str(Path(tmp) / "audit.jsonl"))
            runtime = Runtime(config)
            principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
            with self.assertRaises(PermissionError):
                runtime.search(principal, "kuber", "test")
            event = json.loads((Path(tmp) / "audit.jsonl").read_text(encoding="utf-8").strip())
            self.assertIs(event["allowed"], False)
            self.assertEqual(event["project"], "kuber")

    def test_runtime_scoped_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig(str(Path(tmp) / "memory.db"), str(Path(tmp) / "audit.jsonl"))
            runtime = Runtime(config)
            runtime.memory.put("krishna", "d1", "hello world")
            principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
            self.assertEqual(runtime.search(principal, "krishna", "hello"), [("d1", "hello world")])

    def test_runtime_analyze_mocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(RuntimeConfig(str(Path(tmp) / "memory.db"), str(Path(tmp) / "audit.jsonl")))
            principal = Principal("tester", frozenset({"krishna"}), frozenset({"analyze"}))
            with patch("kuif.runtime.generate", lambda model, prompt: "ok"):
                self.assertEqual(runtime.analyze(principal, "krishna", "hello"), "ok")


if __name__ == "__main__":
    unittest.main()
