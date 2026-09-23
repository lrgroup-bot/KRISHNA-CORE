import tempfile
import unittest

from krishna_core.vishvakarma_rishi import DesignFinding, VishvakarmaRishi


class VishvakarmaRishiTests(unittest.TestCase):
    def test_provenance_and_retrieval(self):
        with tempfile.TemporaryDirectory() as td:
            rishi=VishvakarmaRishi(td)
            rishi.learn(DesignFinding(
                "repo@commit","accessibility","Keyboard focus must remain visible",
                "MIT",0.9,"browser test evidence",
            ))
            rows=rishi.retrieve("keyboard")
            self.assertEqual(rows[0]["source"],"repo@commit")
            self.assertEqual(rows[0]["status"],"candidate")

    def test_unprovenanced_or_unevidenced_finding_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            rishi=VishvakarmaRishi(td)
            with self.assertRaises(ValueError):
                rishi.learn(DesignFinding("","ui","x",evidence="test"))
            with self.assertRaises(ValueError):
                rishi.learn(DesignFinding("source","ui","x",evidence=""))


if __name__=="__main__":
    unittest.main()
