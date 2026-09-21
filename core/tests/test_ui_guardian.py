import tempfile
import unittest
from pathlib import Path

from krishna_core.ui_guardian import UIGuardian, UIGuardianRegistry

class FakeBrowser:
    def __init__(self, overflow=False, findings=None):
        self.overflow=overflow
        self.findings=findings or []
        self.calls=[]
    def inspect(self,url,screenshot_path=None,viewport=None,actions=None):
        self.calls.append((url,viewport,screenshot_path))
        return {
            "url":url,"final_url":url,"title":"x","ok":not self.findings and not self.overflow,
            "findings":list(self.findings),"network":[],"visible_text":"ok","screenshot":screenshot_path,
            "layout":{
                "viewport_width":viewport["width"],"viewport_height":viewport["height"],
                "scroll_width":viewport["width"]+(10 if self.overflow else 0),
                "scroll_height":viewport["height"],"document_width":viewport["width"],
                "document_height":viewport["height"],"horizontal_overflow":self.overflow,
            }
        }

class UIGuardianTests(unittest.TestCase):
    def test_registry_requires_verified_pass_for_stable(self):
        with tempfile.TemporaryDirectory() as td:
            reg=UIGuardianRegistry(Path(td)/"registry.json")
            item=reg.register("KRISHNA UI","KRISHNA","http://127.0.0.1:8766","candidate")
            with self.assertRaises(PermissionError):
                reg.transition(item["id"],"stable",verified=True)
            reg.set_evaluation(item["id"],{"passed":True})
            with self.assertRaises(PermissionError):
                reg.transition(item["id"],"stable",verified=False)
            out=reg.transition(item["id"],"stable",verified=True)
            self.assertEqual(out["state"],"stable")

    def test_matrix_runs_all_four_viewports(self):
        with tempfile.TemporaryDirectory() as td:
            reg=UIGuardianRegistry(Path(td)/"registry.json")
            browser=FakeBrowser()
            g=UIGuardian(browser,reg,Path(td)/"shots")
            out=g.evaluate("KRISHNA","http://127.0.0.1:8766")
            self.assertTrue(out["passed"])
            self.assertEqual(len(out["reports"]),4)
            self.assertEqual({x["viewport"]["width"] for x in out["reports"]},{1920,1440,1024,390})

    def test_horizontal_overflow_is_objective_defect(self):
        with tempfile.TemporaryDirectory() as td:
            reg=UIGuardianRegistry(Path(td)/"registry.json")
            g=UIGuardian(FakeBrowser(overflow=True),reg,Path(td)/"shots")
            out=g.evaluate("KRISHNA","http://127.0.0.1:8766")
            self.assertFalse(out["passed"])
            self.assertTrue(any(x["kind"]=="horizontal_overflow" for x in out["defects"]))

if __name__=="__main__": unittest.main()
