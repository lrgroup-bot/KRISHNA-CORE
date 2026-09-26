import tempfile
import unittest
from pathlib import Path

from krishna_core.narada_legal import NaradaLegalCouncil
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


if __name__=="__main__":
    unittest.main()
