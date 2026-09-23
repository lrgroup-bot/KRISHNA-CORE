import tempfile
import unittest

from krishna_core.sudarshan_design_engine import AcceptanceGovernor, SudarshanDesignEngine
from krishna_core.sudarshan_ui_pipeline import UIEvidence, UIPipeline


class SudarshanUIPipelineTests(unittest.TestCase):
    def test_repair_then_escalate_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            engine=SudarshanDesignEngine(td)
            pipeline=UIPipeline(engine,max_repairs=1)
            evidence=UIEvidence()
            checks={name:True for name in AcceptanceGovernor.REQUIRED}
            checks["visual"]=False
            first=pipeline.next_action(checks,evidence)
            second=pipeline.next_action(checks,evidence)
            self.assertEqual(first["action"],"repair-and-retest")
            self.assertEqual(second["action"],"escalate")

    def test_clean_acceptance_finishes(self):
        with tempfile.TemporaryDirectory() as td:
            pipeline=UIPipeline(SudarshanDesignEngine(td))
            checks={name:True for name in AcceptanceGovernor.REQUIRED}
            out=pipeline.next_action(checks,UIEvidence())
            self.assertEqual(out["action"],"accept")
            self.assertTrue(out["verdict"]["verified"])


if __name__=="__main__":
    unittest.main()
