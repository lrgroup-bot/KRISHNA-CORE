import tempfile
import unittest
from pathlib import Path

from kuif.knowledge import KnowledgeStore


class KuifKnowledgeTests(unittest.TestCase):
    def test_project_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(str(Path(tmp) / "memory.db"))
            store.put("krishna", "a", "secret apple")
            store.put("kuber", "b", "public apple")
            self.assertEqual(store.search("krishna", "apple"), [("a", "secret apple")])
            self.assertEqual(store.search("kuber", "secret"), [])


if __name__ == "__main__":
    unittest.main()
