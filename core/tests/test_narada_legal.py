import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from krishna_core.narada_legal import NaradaLegalAdvisor, NaradaLegalCouncil
from krishna_core.rishi_council import RishiCouncil


class NaradaLegalCouncilTests(unittest.TestCase):
    def test_narada_has_six_permanent_legal_shishya(self):
        self.assertEqual(
            RishiCouncil().get("narada")["permanent_shishya"],
            ["constitution","legal","illegal","vakeel","judge","police"],
        )

    def test_status_exposes_official_sources_and_safety_policy(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td);status=n.status()
            self.assertEqual(len(status["shishya"]),6)
            self.assertIn("india_code",status["official_sources"])
            self.assertIn("supreme_court",status["official_sources"])
            self.assertIn("evasion",status["policy"])

    def test_vakeel_routes_to_lawful_alternatives_not_evasion(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            plan=n.research_plan("Can I bypass law and hide evidence to escape police?")
            self.assertTrue(plan["routing"]["evasion_language_detected"])
            self.assertIn("illegal",plan["routing"]["shishya"])
            self.assertIn("vakeel",plan["routing"]["shishya"])
            v=[x for x in n.shishya() if x["id"]=="vakeel"][0]
            self.assertTrue(any("never advise how to hide" in x for x in v["must_not_do"]))

    def test_authoritative_corpus_accepts_only_allowlisted_official_sources(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            out=n.ingest_official_document(title="Example Act",url="https://www.indiacode.nic.in/example",text="Section 1. Example.",document_type="act")
            self.assertTrue(out["stored"]);self.assertTrue(out["changed"])
            with self.assertRaises(PermissionError):
                n.ingest_official_document(title="Blog",url="https://example.com/law",text="summary",document_type="commentary")

    def test_update_version_preserves_old_hash_and_marks_supersession(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            first=n.ingest_official_document(title="Rule",url="https://www.indiacode.nic.in/rule/1",text="old text",document_type="rule")
            second=n.ingest_official_document(title="Rule",url="https://www.indiacode.nic.in/rule/1",text="new text",document_type="rule")
            self.assertTrue(second["changed"])
            self.assertEqual(second["supersedes"],first["document_id"])
            self.assertTrue((Path(td)/"corpus"/(first["document_id"]+".json")).exists())

    def test_default_jurisdiction_is_bhubaneswar_odisha(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            plan=n.research_plan("What permissions apply to a commercial website business?")
            self.assertEqual(plan["jurisdiction"]["state"],"Odisha")
            self.assertEqual(plan["jurisdiction"]["district"],"Khordha")
            self.assertEqual(plan["jurisdiction"]["city"],"Bhubaneswar")
            self.assertIn("Odisha law only",plan["scope_policy"])

    def test_other_state_law_is_disabled_for_now(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            with self.assertRaises(PermissionError):
                n.research_plan("property registration rules",state="Karnataka")

    def test_odisha_and_bhubaneswar_sources_are_registered(self):
        with tempfile.TemporaryDirectory() as td:
            sources=NaradaLegalCouncil(td).sources()
            for sid in ("odisha_law","orissa_high_court","odisha_revenue","odisha_urban","bmc","bda","orera","odisha_police","commissionerate_police","odisha_labour","odisha_finance","odisha_spcb"):
                self.assertIn(sid,sources)

    def test_odisha_official_document_can_enter_authoritative_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            out=n.ingest_official_document(
                title="Odisha Rule",
                url="https://law.odisha.gov.in/example-rule",
                text="Official Odisha legal text",
                document_type="rule",
                jurisdiction="Odisha",
            )
            self.assertEqual(out["source_id"],"odisha_law")

    def test_active_advisor_case_plan_always_pairs_judge_and_vakeel(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalAdvisor(td)
            plan=n.case_research_plan("software contract dispute in Bhubaneswar")
            self.assertEqual(plan["mandatory_shishyas"],["judge","vakeel"])
            self.assertIn("favourable precedent",plan["judge"]["required_search"])
            self.assertIn("adverse precedent",plan["judge"]["required_search"])
            self.assertIn("opponent's strongest counter-argument linked to verified authority",plan["vakeel"]["argument_packet"])
            self.assertIn("reply/rebuttal",plan["vakeel"]["argument_packet"])
            self.assertIn("relief_granted_or_refused",plan["judge"]["extract"])
            self.assertTrue(any("guaranteed prediction" in x for x in plan["comparison_rules"]))

    def test_active_advisor_defaults_to_bhubaneswar_odisha_and_blocks_other_states(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalAdvisor(td)
            plan=n.case_research_plan("property contract dispute")
            self.assertIn("Odisha",plan["jurisdiction"])
            self.assertIn("Bhubaneswar",plan["jurisdiction"])
            with self.assertRaises(PermissionError):
                n.case_research_plan("property dispute",jurisdiction="Karnataka")

    def test_council_routes_judge_and_vakeel_for_every_legal_question(self):
        with tempfile.TemporaryDirectory() as td:
            n=NaradaLegalCouncil(td)
            plan=n.research_plan("Can we send a lawful commercial contract notice?")
            self.assertIn("judge",plan["routing"]["shishya"])
            self.assertIn("vakeel",plan["routing"]["shishya"])
            self.assertTrue(plan["case_research_policy"]["judge_and_vakeel_mandatory"])

    def test_legal_query_detection_and_official_query_pack(self):
        with tempfile.TemporaryDirectory() as td:
            advisor=NaradaLegalAdvisor(td)
            self.assertTrue(advisor.looks_legal("Is this property agreement legal in Odisha?"))
            self.assertTrue(advisor.looks_legal("Police FIR and bail procedure"))
            self.assertFalse(advisor.looks_legal("Build me a photo gallery website"))
            queries=advisor.official_research_queries("property agreement Odisha","Odisha")
            self.assertEqual(set(queries),{"constitution","legal","illegal","vakeel","judge","police"})
            self.assertIn("site:indiacode.nic.in",queries["legal"])
            self.assertIn("site:law.odisha.gov.in",queries["legal"])
            self.assertIn("site:judgments.ecourts.gov.in",queries["judge"])

    def test_official_research_filter_rejects_non_authority_web_results(self):
        with tempfile.TemporaryDirectory() as td:
            advisor=NaradaLegalAdvisor(td)
            report={
                "web":[
                    {"url":"https://www.indiacode.nic.in/indiacode/home.jsp","title":"India Code"},
                    {"url":"https://example.com/blog","title":"Blog"},
                    {"url":"https://www.sci.gov.in/constitution/","title":"Supreme Court"},
                ],
                "errors":{},"coverage":["public_web"],
            }
            out=advisor.filter_official_research(report)
            self.assertEqual(len(out["web"]),2)
            self.assertTrue(all("example.com" not in x["url"] for x in out["web"]))
            self.assertTrue(out["official_only"])

    def test_deep_corpus_plan_uses_official_inventory_and_measured_completion(self):
        with tempfile.TemporaryDirectory() as td:
            advisor=NaradaLegalAdvisor(td)
            plan=advisor.deep_corpus_plan("Odisha")
            ids={x["id"] for x in plan["official_inventory_sources"]}
            self.assertIn("india_code_data_report",ids)
            self.assertTrue({"odisha_acts","odisha_rules","odisha_notifications"}.issubset(ids))
            self.assertEqual(plan["crawl_contract"]["concurrency"],1)
            self.assertTrue(plan["crawl_contract"]["resume_from_checkpoint"])
            self.assertIn("Do not mark corpus complete",plan["completion_rule"])

    def test_bounded_crawler_saves_and_resumes_same_origin_official_pages(self):
        with tempfile.TemporaryDirectory() as td:
            advisor=NaradaLegalAdvisor(td)
            first=(
                b'<html><a href="/indiacode/about.jsp">About</a><a href="https://example.com/no">No</a></html>',
                {"final_url":"https://www.indiacode.nic.in/indiacode/home.jsp",
                 "content_type":"text/html","etag":"","last_modified":""},
            )
            second=(
                b"<html>About India Code</html>",
                {"final_url":"https://www.indiacode.nic.in/indiacode/about.jsp",
                 "content_type":"text/html","etag":"","last_modified":""},
            )
            with patch.object(advisor,"_robots_allowed",return_value=True), \
                 patch.object(advisor,"_fetch_crawl_url",side_effect=[first,second]), \
                 patch("krishna_core.narada_legal.time.sleep",return_value=None):
                out=advisor.crawl_official_source("india_code",max_documents=2,max_depth=1)
            self.assertEqual(out["processed"],2)
            self.assertEqual(len(out["saved"]),2)
            self.assertTrue(out["complete_for_discovered_frontier"])
            self.assertTrue(all(Path(x["path"]).exists() for x in out["saved"]))

    def test_operational_narada_actions_and_conversation_routing_are_wired(self):
        orch=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for token in (
            '"narada.legal.corpus_plan"',
            '"narada.legal.research_queries"',
            '"narada.legal.crawl"',
            "self.narada_legal.looks_legal(message)",
            "live_official_research",
        ):
            self.assertIn(token,orch)


if __name__=="__main__":
    unittest.main()
