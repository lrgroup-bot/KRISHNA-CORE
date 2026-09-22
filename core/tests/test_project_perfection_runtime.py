import unittest
from unittest.mock import Mock

from krishna_core.project_perfection_runtime import ProjectPerfectionRuntime


class RuntimeTests(unittest.TestCase):
    def test_plan_team(self):
        runtime=ProjectPerfectionRuntime(Mock(),Mock(),max_workers=8)
        plan=runtime.plan_team([
            {"role":"frontend","estimate_minutes":80},
            {"role":"backend","estimate_minutes":80},
            {"role":"integration","estimate_minutes":10,"parallelizable":False},
        ],60)
        self.assertGreaterEqual(plan["recommended_workers"],4)

    def test_browser_audit_uses_geometry(self):
        browser=Mock()
        browser.perfection_scan.return_value={"ok":True,"viewports":[{
            "width":390,"height":844,"geometry":[
                {"selector":"#bad","x":380,"y":10,"width":40,"height":30,"visible":True,"text":"","z_index":0}
            ]
        }]}
        runtime=ProjectPerfectionRuntime(browser,Mock())
        result=runtime.browser_audit("http://127.0.0.1:8000")
        self.assertFalse(result["geometry_ok"])
        self.assertFalse(result["ok"])

    def test_certificate_requires_all_gates(self):
        runtime=ProjectPerfectionRuntime(Mock(),Mock())
        result=runtime.completion_certificate("demo","abc",[{"gate":"requirements","passed":True}])
        self.assertEqual(result["verdict"],"NOT_COMPLETE")


if __name__=="__main__":
    unittest.main()
