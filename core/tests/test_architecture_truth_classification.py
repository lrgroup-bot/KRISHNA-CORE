import tempfile
import unittest
from pathlib import Path

from krishna_core.architecture_truth import ArchitectureTruthAudit


class ArchitectureTruthClassificationTests(unittest.TestCase):
    def test_generated_cache_and_normal_init_names_are_not_duplicate_noise(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"core"/"krishna_core"/"pkg").mkdir(parents=True)
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            (root/"core"/"krishna_core"/"__init__.py").write_text("",encoding="utf-8")
            (root/"core"/"krishna_core"/"pkg"/"__init__.py").write_text("",encoding="utf-8")
            cache=root/"core"/"krishna_core"/"__pycache__"
            cache.mkdir()
            (cache/"x.pyc").write_bytes(b"generated")
            report=ArchitectureTruthAudit(root)._duplicate_inventory()
            names={x["name"] for x in report["same_basename"]}
            self.assertNotIn("__init__.py",names)
            self.assertFalse(any("__pycache__" in p for row in report["identical_content"] for p in row["paths"]))

    def test_known_compatibility_module_is_classified_not_orphan(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"core"/"krishna_core").mkdir(parents=True)
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            (root/"core"/"krishna_core"/"autonomy_loop.py").write_text("VALUE=1\n",encoding="utf-8")
            audit=ArchitectureTruthAudit(root)
            self.assertFalse(any(x["module"]=="autonomy_loop" for x in audit._orphan_candidates()))
            classified=audit._classified_non_entry_modules()
            self.assertTrue(any(x["module"]=="autonomy_loop" for x in classified))


if __name__=="__main__":
    unittest.main()
