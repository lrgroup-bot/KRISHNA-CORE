import tempfile
import unittest
from pathlib import Path

from krishna_core.mobile_acceptance import MobileAcceptanceLedger, REQUIRED_GATES


class MobileAcceptanceLedgerTests(unittest.TestCase):
    def test_all_real_device_gates_are_required_before_retirement(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=MobileAcceptanceLedger(Path(td)/"acceptance.json")
            self.assertEqual(ledger.status()["companion_retirement"],"retain")
            for gate in REQUIRED_GATES:
                ledger.record(gate,True,evidence=f"device-proof:{gate}")
            status=ledger.status()
            self.assertTrue(status["real_device_accepted"])
            self.assertEqual(status["companion_retirement"],"eligible_for_review")
            self.assertFalse(status["automatic_delete"])

    def test_passing_gate_requires_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=MobileAcceptanceLedger(Path(td)/"acceptance.json")
            with self.assertRaises(ValueError):
                ledger.record("clean_install_relaunch",True,evidence="")

    def test_failed_gate_may_record_without_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=MobileAcceptanceLedger(Path(td)/"acceptance.json")
            row=ledger.record("secure_pair_reconnect",False)
            self.assertFalse(row["passed"])


if __name__=="__main__":
    unittest.main()
