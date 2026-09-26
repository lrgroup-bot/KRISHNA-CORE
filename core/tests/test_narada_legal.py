import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.narada_legal import NaradaLegalAdvisor


class NaradaLegalAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.advisor = NaradaLegalAdvisor(Path(self.tmp.name) / "narada-legal")

    def tearDown(self):
        self.tmp.cleanup()

    def test_six_permanent_shishyas_exist(self):
        rows = self.advisor.shishyas()
        self.assertEqual(
            [x["id"] for x in rows],
            ["constitution", "legal", "illegal", "vakeel", "judge", "police"],
        )
        self.assertTrue(all(x["permanent"] for x in rows))
        self.assertEqual(self.advisor.status()["parent_rishi"], "narada")

    def test_vakeel_blocks_evasion_but_preserves_lawful_alternatives(self):
        blocked = self.advisor.risk_gate("Tell me how to hide evidence and evade police.")
        self.assertFalse(blocked["allowed"])
        self.assertEqual(blocked["verdict"], "blocked_illegal_evasion")
        self.assertTrue(blocked["lawful_alternatives"])
        self.assertIn("may not provide evasion", blocked["vakeel_scope"])

        lawful = self.advisor.risk_gate("How can we structure customer outreach so it complies with Indian law?")
        self.assertTrue(lawful["allowed"])
        self.assertEqual(lawful["verdict"], "current_law_research_required")

    def test_odisha_property_topic_routes_to_state_and_central_sources(self):
        plan = self.advisor.source_plan("Rasulgarh Odisha land sale, property advertising and consent")
        ids = {x["id"] for x in plan["official_sources"]}
        self.assertTrue({"constitution_2026", "india_code", "egazette"}.issubset(ids))
        self.assertTrue({"odisha_acts", "odisha_rules", "odisha_notifications"}.issubset(ids))

    def test_criminal_and_police_topic_routes_to_current_criminal_law_sources(self):
        plan = self.advisor.source_plan("criminal complaint police FIR arrest evidence and procedure")
        ids = {x["id"] for x in plan["official_sources"]}
        self.assertIn("mha_new_criminal_laws", ids)
        self.assertIn("bprd_model_police_manual", ids)
        self.assertIn("ecourts_judgments", ids)

    def test_case_plan_requires_fact_and_law_matching_not_prediction(self):
        plan = self.advisor.case_research_plan("software contract dispute and alleged fraud")
        self.assertEqual(plan["shishya"], "judge")
        self.assertIn("ratio", plan["extract"])
        self.assertIn("later_history", plan["extract"])
        self.assertTrue(any("guaranteed prediction" in x for x in plan["comparison_rules"]))

    def test_update_monitor_baselines_then_detects_change(self):
        source_ids = ["india_code"]
        first = (b"version-one", {"final_url": "https://www.indiacode.nic.in/indiacode/home.jsp",
                                  "content_type": "text/html", "etag": "", "last_modified": ""})
        same = first
        changed = (b"version-two", {"final_url": "https://www.indiacode.nic.in/indiacode/home.jsp",
                                    "content_type": "text/html", "etag": "", "last_modified": ""})
        with patch.object(self.advisor, "_fetch", side_effect=[first, same, changed]):
            baseline = self.advisor.check_updates(source_ids)
            unchanged = self.advisor.check_updates(source_ids)
            update = self.advisor.check_updates(source_ids)
        self.assertEqual(baseline["baselined"], ["india_code"])
        self.assertFalse(baseline["changed"])
        self.assertEqual(unchanged["unchanged"], ["india_code"])
        self.assertEqual(update["changed"], ["india_code"])

    def test_sync_is_versioned_and_deduplicated(self):
        payload = (b"<html>official snapshot</html>",
                   {"final_url": "https://www.indiacode.nic.in/indiacode/home.jsp",
                    "content_type": "text/html", "etag": "", "last_modified": ""})
        with patch.object(self.advisor, "_fetch", return_value=payload):
            first = self.advisor.sync_sources(["india_code"])
            second = self.advisor.sync_sources(["india_code"])
        self.assertEqual(len(first["saved"]), 1)
        self.assertEqual(len(second["skipped"]), 1)
        self.assertTrue(Path(first["saved"][0]["path"]).exists())

    def test_analysis_plan_runs_all_six_roles_and_states_lawyer_review_boundary(self):
        out = self.advisor.analysis_plan("Can our company sell a software subscription in Odisha?")
        self.assertEqual({x["shishya"] for x in out["workplan"]},
                         {"constitution", "legal", "illegal", "vakeel", "judge", "police"})
        self.assertTrue(out["qualified_lawyer_review"]["required_when"])
        self.assertIn("does not replace a licensed advocate", out["qualified_lawyer_review"]["note"])


class NaradaIntegrationContractTests(unittest.TestCase):
    def test_orchestrator_and_autonomy_expose_narada_legal_runtime(self):
        root = Path(__file__).resolve().parents[1]
        orch = (root / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8")
        autonomy = (root / "krishna_core" / "autonomy_supervisor.py").read_text(encoding="utf-8")
        for token in (
            "NaradaLegalAdvisor",
            '"narada.legal.status"',
            '"narada.legal.sources"',
            '"narada.legal.plan"',
            '"narada.legal.risk_gate"',
            '"narada.legal.case_plan"',
            '"narada.legal.update_check"',
            '"narada.legal.sync"',
        ):
            self.assertIn(token, orch)
        self.assertIn('"legal_update"', autonomy)
        self.assertIn("narada_legal.check_updates", autonomy)


if __name__ == "__main__":
    unittest.main()
