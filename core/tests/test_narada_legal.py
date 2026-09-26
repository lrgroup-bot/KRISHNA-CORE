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

    def test_legal_query_detection_and_official_query_pack(self):
        self.assertTrue(self.advisor.looks_legal("Is this property agreement legal in Odisha?"))
        self.assertTrue(self.advisor.looks_legal("Police FIR and bail procedure"))
        self.assertFalse(self.advisor.looks_legal("Build me a photo gallery website"))
        queries = self.advisor.official_research_queries("property agreement Odisha", "Odisha")
        self.assertEqual(set(queries), {"constitution", "legal", "illegal", "vakeel", "judge", "police"})
        self.assertIn("site:indiacode.nic.in", queries["legal"])
        self.assertIn("site:law.odisha.gov.in", queries["legal"])
        self.assertIn("site:judgments.ecourts.gov.in", queries["judge"])

    def test_official_research_filter_rejects_non_authority_web_results(self):
        report = {
            "web": [
                {"url": "https://www.indiacode.nic.in/indiacode/home.jsp", "title": "India Code"},
                {"url": "https://example.com/blog", "title": "Blog"},
                {"url": "https://www.sci.gov.in/constitution/", "title": "Supreme Court"},
            ],
            "errors": {},
            "coverage": ["public_web"],
        }
        out = self.advisor.filter_official_research(report)
        self.assertEqual(len(out["web"]), 2)
        self.assertTrue(all("example.com" not in x["url"] for x in out["web"]))
        self.assertTrue(out["official_only"])

    def test_deep_corpus_plan_uses_official_inventory_and_measured_completion(self):
        plan = self.advisor.deep_corpus_plan("Odisha")
        ids = {x["id"] for x in plan["official_inventory_sources"]}
        self.assertIn("india_code_data_report", ids)
        self.assertTrue({"odisha_acts", "odisha_rules", "odisha_notifications"}.issubset(ids))
        self.assertEqual(plan["crawl_contract"]["concurrency"], 1)
        self.assertTrue(plan["crawl_contract"]["resume_from_checkpoint"])
        self.assertIn("Do not mark corpus complete", plan["completion_rule"])

    def test_bounded_crawler_saves_and_resumes_same_origin_official_pages(self):
        first = (
            b'<html><a href="/indiacode/about.jsp">About</a><a href="https://example.com/no">No</a></html>',
            {"final_url": "https://www.indiacode.nic.in/indiacode/home.jsp",
             "content_type": "text/html", "etag": "", "last_modified": ""},
        )
        second = (
            b"<html>About India Code</html>",
            {"final_url": "https://www.indiacode.nic.in/indiacode/about.jsp",
             "content_type": "text/html", "etag": "", "last_modified": ""},
        )
        with patch.object(self.advisor, "_robots_allowed", return_value=True), \
             patch.object(self.advisor, "_fetch_crawl_url", side_effect=[first, second]), \
             patch("krishna_core.narada_legal.time.sleep", return_value=None):
            out = self.advisor.crawl_official_source("india_code", max_documents=2, max_depth=1)
        self.assertEqual(out["processed"], 2)
        self.assertEqual(len(out["saved"]), 2)
        self.assertTrue(out["complete_for_discovered_frontier"])
        self.assertTrue(all(Path(x["path"]).exists() for x in out["saved"]))

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
            '"narada.legal.corpus_plan"',
            '"narada.legal.research_queries"',
            '"narada.legal.crawl"',
            '"narada.legal.update_check"',
            '"narada.legal.sync"',
        ):
            self.assertIn(token, orch)
        self.assertIn('"legal_update"', autonomy)
        self.assertIn("narada_legal.check_updates", autonomy)
        self.assertIn("self.narada_legal.looks_legal(message)", orch)
        self.assertIn("live_official_research", orch)


if __name__ == "__main__":
    unittest.main()
