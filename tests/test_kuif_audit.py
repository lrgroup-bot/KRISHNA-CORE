import json
import tempfile
import unittest
from pathlib import Path

from kuif.audit import append_event


class KuifAuditTests(unittest.TestCase):
    def test_append_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "events.jsonl"
            append_event(str(target), project="krishna", actor="user-1", action="read", allowed=True)
            event = json.loads(target.read_text(encoding="utf-8").strip())
            self.assertEqual(event["project"], "krishna")
            self.assertIs(event["allowed"], True)
            self.assertIn("timestamp", event)

    def test_missing_actor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                append_event(str(Path(tmp) / "events.jsonl"), project="krishna", actor="", action="read", allowed=True)


if __name__ == "__main__":
    unittest.main()
