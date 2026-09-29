import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_scan_reuses_recent_report_without_rescanning(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"core"/"krishna_core").mkdir(parents=True)
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            (root/"core"/"krishna_core"/"alpha.py").write_text("VALUE=1\n",encoding="utf-8")
            audit=ArchitectureTruthAudit(root)
            first=audit.scan()
            with patch.object(audit,"_duplicate_inventory",side_effect=AssertionError("unexpected rescan")):
                second=audit.scan()
            self.assertIs(first,second)

    def test_generated_directories_are_pruned_from_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"core"/"krishna_core").mkdir(parents=True)
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            (root/"mobile_v3"/"src").mkdir(parents=True)
            (root/"mobile_v3"/"node_modules"/"pkg").mkdir(parents=True)
            (root/"mobile_v3"/"build"/"generated").mkdir(parents=True)
            (root/"mobile_v3"/"src"/"keep.txt").write_text("same",encoding="utf-8")
            (root/"mobile_v3"/"node_modules"/"pkg"/"skip.txt").write_text("same",encoding="utf-8")
            (root/"mobile_v3"/"build"/"generated"/"skip2.txt").write_text("same",encoding="utf-8")
            audit=ArchitectureTruthAudit(root)
            paths={audit._relative(p) for p in audit._files("mobile_v3")}
            self.assertIn("mobile_v3/src/keep.txt",paths)
            self.assertFalse(any("node_modules" in p or "/build/" in p for p in paths))

    def test_merge_integrity_detects_real_same_scope_and_registration_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            core=root/"core"/"krishna_core"
            tests=root/"core"/"tests"
            req=root/"core"/"requirements"
            core.mkdir(parents=True);tests.mkdir(parents=True);req.mkdir(parents=True)

            (core/"dupe.py").write_text(
                "def x():\n    return 1\ndef x():\n    return 2\n",
                encoding="utf-8",
            )
            (core/"orchestrator.py").write_text(
                "class O:\n"
                "    def f(self):\n"
                "        self.action_bus.register('same',None)\n"
                "        self.action_bus.register('same',None)\n"
                "        self.agent_runtime.register('agent',None)\n"
                "        self.agent_runtime.register('agent',None)\n",
                encoding="utf-8",
            )
            (core/"server.py").write_text(
                "class H:\n"
                "    def _get(self):\n"
                "        if path == '/same': pass\n"
                "        if path == '/same': pass\n"
                "    def _post(self):\n"
                "        if post_path == '/same': pass\n",
                encoding="utf-8",
            )
            (core/"specialist_registry.py").write_text(
                "Specialist('dup','a',())\nSpecialist('dup','b',())\n",
                encoding="utf-8",
            )
            (core/"rishi_council.py").write_text(
                "RishiProfile('dup','a','r','r',(),'q','c')\n"
                "RishiProfile('dup','b','r','r',(),'q','c')\n",
                encoding="utf-8",
            )
            (core/"three_d_model_router.py").write_text(
                "ThreeDProvider('dup','a','a','MIT',0,True,True,'allowed')\n"
                "ThreeDProvider('dup','b','b','MIT',0,True,True,'allowed')\n",
                encoding="utf-8",
            )

            integrity=ArchitectureTruthAudit(root)._merge_integrity()
            self.assertEqual(len(integrity["same_scope_python_redefinitions"]),1)
            self.assertEqual(integrity["duplicate_action_bus_registrations"][0]["name"],"same")
            self.assertEqual(integrity["duplicate_agent_runtime_registrations"][0]["name"],"agent")
            self.assertEqual(integrity["duplicate_http_routes_same_handler"][0]["handler"],"_get")
            self.assertEqual(integrity["duplicate_specialist_ids"][0]["name"],"dup")
            self.assertEqual(integrity["duplicate_rishi_ids"][0]["name"],"dup")
            self.assertEqual(integrity["duplicate_3d_provider_ids"][0]["name"],"dup")

    def test_merge_integrity_allows_cross_scope_names_and_get_post_route_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            core=root/"core"/"krishna_core"
            (root/"core"/"tests").mkdir(parents=True)
            (root/"core"/"requirements").mkdir(parents=True)
            core.mkdir(parents=True)
            (core/"ok.py").write_text(
                "class A:\n"
                "    def verify(self): return True\n"
                "class B:\n"
                "    def verify(self): return True\n",
                encoding="utf-8",
            )
            (core/"server.py").write_text(
                "class H:\n"
                "    def _get(self):\n"
                "        if path == '/same': pass\n"
                "    def _post(self):\n"
                "        if post_path == '/same': pass\n",
                encoding="utf-8",
            )
            integrity=ArchitectureTruthAudit(root)._merge_integrity()
            self.assertFalse(integrity["same_scope_python_redefinitions"])
            self.assertFalse(integrity["duplicate_http_routes_same_handler"])

    def test_current_repository_has_no_dangerous_merge_collisions(self):
        repo=Path(__file__).resolve().parents[2]
        integrity=ArchitectureTruthAudit(repo)._merge_integrity()
        for key in (
            "same_scope_python_redefinitions",
            "duplicate_action_bus_registrations",
            "duplicate_agent_runtime_registrations",
            "duplicate_http_routes_same_handler",
            "duplicate_specialist_ids",
            "duplicate_rishi_ids",
            "duplicate_3d_provider_ids",
            "parse_errors",
        ):
            self.assertEqual(integrity[key],[],msg=f"{key}: {integrity[key]}")

    def test_status_vocabulary_contains_product_truth_states(self):
        self.assertTrue({
            "VERIFIED","IMPLEMENTED_NOT_VERIFIED","PARTIAL","MISSING","ROADMAP","SUPERSEDED"
        }.issubset(ArchitectureTruthAudit.STATUS_VALUES))


if __name__=="__main__":
    unittest.main()
