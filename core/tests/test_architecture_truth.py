import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.architecture_truth import ArchitectureTruthAudit


class ArchitectureTruthAuditTests(unittest.TestCase):
    def test_scan_separates_canonical_legacy_drift_and_requirement_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"core"/"krishna_core").mkdir(parents=True)
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            (root/"GARUDANETRA_SOURCE"/"core"/"krishna_core").mkdir(parents=True)

            (root/"core"/"krishna_core"/"alpha.py").write_text("VALUE=1\n",encoding="utf-8")
            (root/"core"/"krishna_core"/"beta.py").write_text("from .alpha import VALUE\n",encoding="utf-8")
            (root/"core"/"krishna_core"/"orphan.py").write_text("VALUE=3\n",encoding="utf-8")
            (root/"core"/"krishna_core"/"data").mkdir()
            (root/"core"/"krishna_core"/"data"/"corpus.json").write_text("{}",encoding="utf-8")
            (root/"GARUDANETRA_SOURCE"/"core"/"krishna_core"/"alpha.py").write_text("VALUE=1\n",encoding="utf-8")
            (root/"KRISHNA_SOURCE_TREE.txt").write_text(
                "core\\krishna_core\\alpha.py\ncore\\krishna_core\\old.py\ncore\\krishna_core\\data\\corpus.json\n",
                encoding="utf-8",
            )
            ledger={
                "schema":2,
                "version":"test",
                "groups":[],
                "implementation_index":[
                    {"id":"a","status":"IMPLEMENTED_NOT_VERIFIED","evidence":["core/krishna_core/alpha.py"]},
                    {"id":"missing","status":"PARTIAL","evidence":["core/krishna_core/not-here.py"]},
                ],
            }
            (root/"core"/"requirements"/"krishna_chat_requirements.json").write_text(
                json.dumps(ledger),encoding="utf-8"
            )

            report=ArchitectureTruthAudit(root).scan()
            self.assertEqual(report["requirements"]["version"],"test")
            self.assertEqual(len(report["requirements"]["evidence_missing"]),1)
            self.assertTrue(any(x["root"]=="GARUDANETRA_SOURCE" for x in report["legacy_roots"]))
            duplicate=[x for x in report["duplicates"]["identical_content"] if len(x["paths"])==2]
            self.assertTrue(duplicate)
            self.assertIn(
                "core\\krishna_core\\beta.py",
                report["source_tree_drift"]["missing_current_modules"],
            )
            self.assertIn(
                "core\\krishna_core\\old.py",
                report["source_tree_drift"]["stale_entries"],
            )
            self.assertNotIn(
                "core\\krishna_core\\data\\corpus.json",
                report["source_tree_drift"]["stale_entries"],
            )
            self.assertTrue(any(x["module"]=="orphan" for x in report["orphan_candidates"]))
            self.assertFalse(any(x["module"]=="alpha" for x in report["orphan_candidates"]))

    def test_status_vocabulary_contains_product_truth_states(self):
        self.assertTrue({
            "VERIFIED","IMPLEMENTED_NOT_VERIFIED","PARTIAL","MISSING","ROADMAP","SUPERSEDED"
        }.issubset(ArchitectureTruthAudit.STATUS_VALUES))


if __name__=="__main__":
    unittest.main()
