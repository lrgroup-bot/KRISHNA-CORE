import unittest
from pathlib import Path
from krishna_core.requirements_ledger import RequirementsLedger

class RequirementsLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger=RequirementsLedger()

    def test_chat_requirements_are_machine_readable(self):
        d=self.ledger.snapshot()
        self.assertGreaterEqual(d["group_count"],10)
        self.assertGreaterEqual(d["requirement_count"],35)
        text="\n".join(d["non_negotiables"]+[g["title"] for g in d["groups"]]+[r for g in d["groups"] for r in g["requirements"]])
        for term in ("KRISHNA","Sudarshan","Garudanetra","Gyan-Bhandar","NARAD","KABACH","conversation-only","Krishna_AGI.exe"):
            self.assertIn(term.lower(),text.lower())

    def test_schema2_product_truth_fields_are_exposed(self):
        d=self.ledger.snapshot()
        self.assertEqual(d["schema"],2)
        self.assertEqual(d["version"],"2026-09-23-master-product-truth-v6")
        self.assertIn("VERIFIED",d["status_definitions"])
        self.assertIn("IMPLEMENTED_NOT_VERIFIED",d["status_definitions"])
        self.assertIn("REAL_RUNTIME_OR_DEVICE_TEST",d["delivery_pipeline"])
        self.assertGreaterEqual(len(d["implementation_index"]),10)
        ids={x["id"] for x in d["implementation_index"]}
        self.assertIn("hawkeye_live_coordinator",ids)
        self.assertIn("canonical_mobile_runtime",ids)

    def test_prompt_contract_contains_non_negotiables(self):
        text=self.ledger.prompt_contract()
        self.assertIn("KRISHNA is the only public identity",text)
        self.assertIn("Unfinished commitments are never silently discarded",text)
        self.assertIn("Final Krishna_AGI.exe",text)

    def test_search_finds_mobile_and_voice_rules(self):
        d=self.ledger.search("device")
        self.assertGreater(d["count"],0)
        self.assertTrue(any("device" in x["requirement"].lower() for x in d["matches"]))

if __name__=="__main__": unittest.main()
