from pathlib import Path
import tempfile
import unittest

from krishna_core.lr_group_os import LRGroupOS, ACTIVE_DEPARTMENTS, FROZEN_COMPANIES


class LRGroupOSTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.os = LRGroupOS(Path(self.tmp.name) / "lr_group.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_active_and_frozen_boundaries(self):
        status = self.os.status()
        self.assertEqual({x["id"] for x in status["departments"]}, set(ACTIVE_DEPARTMENTS))
        self.assertEqual({x["id"] for x in status["companies"]}, set(FROZEN_COMPANIES))
        self.assertTrue(all(x["status"] == "frozen" for x in status["companies"]))

    def test_frozen_company_cannot_run(self):
        result = self.os.submit_work("lrs_motors", "Change vehicle workflow")
        self.assertEqual(result["work"]["status"], "blocked")
        self.assertEqual(result["decision"]["reason"], "company_frozen_awaiting_owner_idea")

    def test_zero_spend_requires_exact_approval(self):
        result = self.os.submit_work("lr_commerce", "Buy service", action="spend", amount_inr=499)
        self.assertEqual(result["work"]["status"], "awaiting_approval")
        self.assertEqual(result["approval"]["exact_amount_inr"], 499.0)
        self.assertEqual(result["approval"]["exact_action"], "spend")

    def test_external_write_requires_owner_approval(self):
        result = self.os.submit_work("lr_sales", "Send proposal", action="external_message", external_write=True)
        self.assertTrue(result["decision"]["approval_required"])
        self.assertEqual(result["work"]["status"], "awaiting_approval")

    def test_local_read_only_work_is_ready(self):
        result = self.os.submit_work("lr_ca", "Prepare GST checklist", action="research")
        self.assertEqual(result["work"]["status"], "ready")
        self.assertIsNone(result["approval"])

    def test_approval_is_single_resolution(self):
        result = self.os.submit_work("lr_legal", "File legal document", action="legal_file")
        approval_id = result["approval"]["id"]
        resolved = self.os.resolve_approval(approval_id, approved=True)
        self.assertEqual(resolved["status"], "approved")
        with self.assertRaises(ValueError):
            self.os.resolve_approval(approval_id, approved=True)

    def test_audit_chain_is_linked(self):
        self.os.submit_work("lr_hr", "Draft role", action="research")
        self.os.submit_work("lr_technology", "Review architecture", action="research")
        data = self.os._read()
        self.assertEqual(data["audit"][0]["previous_hash"], "GENESIS")
        self.assertEqual(data["audit"][1]["previous_hash"], data["audit"][0]["hash"])


if __name__ == "__main__":
    unittest.main()
