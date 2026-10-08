import unittest

from krishna_core.rishi_gyan_sagar import AccessMode, RishiGyanSagar


class RishiGyanSagarTests(unittest.TestCase):
    def setUp(self):
        self.sagar = RishiGyanSagar()

    def test_catalog_is_large_and_has_core_sources(self):
        status = self.sagar.source_status()
        self.assertGreaterEqual(status["source_count"], 25)
        ids = {x["id"] for x in self.sagar.list_sources()}
        for needed in (
            "openalex", "crossref", "unpaywall", "core", "doaj", "doab", "oapen",
            "europe-pmc", "pmc", "shodhganga", "sarit", "dcs", "nptel", "swayam",
            "epo-ops", "rfc-editor", "w3c", "nist", "github", "software-heritage",
            "huggingface", "gutenberg", "openlibrary",
        ):
            self.assertIn(needed, ids)

    def test_blocked_sources_never_enter_rishi_fabric(self):
        for sid in ("sci-hub", "temp-mail", "10-minute-mail"):
            with self.assertRaises(PermissionError):
                self.sagar.source(sid)

    def test_openalex_is_primary_search_and_unpaywall_is_doi_resolver(self):
        openalex = self.sagar.source("openalex")
        unpaywall = self.sagar.source("unpaywall")
        self.assertEqual(openalex["evidence_role"], "discovery")
        self.assertEqual(unpaywall["adapter"], "rest-json-doi")
        self.assertIn("retired", unpaywall["notes"].lower())

    def test_medical_plan_prioritizes_biomedical_sources(self):
        plan = self.sagar.research_plan("clinical diagnosis medicine evidence", rishi_id="sushruta", max_sources=10)
        ids = [x["id"] for x in plan["sources"]]
        self.assertIn("europe-pmc", ids)
        self.assertIn("pmc", ids)
        self.assertEqual(plan["lead_rishi"], "sushruta")
        self.assertEqual(plan["mandatory_reviewers"], ["gautama", "veda-vyasa"])

    def test_sanskrit_plan_prioritizes_machine_readable_corpora(self):
        plan = self.sagar.research_plan("Sanskrit Ayurveda classical Indian text", rishi_id="panini", max_sources=12)
        ids = [x["id"] for x in plan["sources"]]
        self.assertIn("sarit", ids)
        self.assertIn("dcs", ids)

    def test_technology_plan_contains_standards_code_and_patents(self):
        plan = self.sagar.research_plan("software networking AI technology patent", rishi_id="vishwamitra", max_sources=20)
        ids = [x["id"] for x in plan["sources"]]
        for needed in ("rfc-editor", "github", "software-heritage", "epo-ops"):
            self.assertIn(needed, ids)

    def test_query_builders_do_not_execute_and_preserve_zero_spend(self):
        plan = self.sagar.request_plan("openalex", "battery recycling")
        self.assertIn("search=battery+recycling", plan["url"])
        self.assertIn("never upgrade", plan["zero_spend_rule"])
        self.assertFalse(plan["requires_browser"])

    def test_crossref_polite_request_can_include_mailto(self):
        plan = self.sagar.request_plan("crossref", "graph neural networks", email="owner@example.com")
        self.assertIn("mailto=owner%40example.com", plan["url"])

    def test_unpaywall_doi_resolution_requires_contact_email(self):
        with self.assertRaises(ValueError):
            self.sagar.doi_resolution_plan("10.1000/test", "")
        rows = self.sagar.doi_resolution_plan("10.1000/test", "owner@example.com")
        self.assertEqual([x["source_id"] for x in rows], ["crossref", "unpaywall"])

    def test_unknown_rights_do_not_auto_archive(self):
        decision = self.sagar.rights_decision("archive", license_id="", source_default_max_mode="index")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.review_required)

    def test_cc0_can_be_archived_and_training_candidate_is_allowed(self):
        archive = self.sagar.rights_decision(AccessMode.ARCHIVE, license_id="CC0-1.0", source_default_max_mode="index")
        train = self.sagar.rights_decision(AccessMode.TRAIN, license_id="CC0-1.0", source_default_max_mode="index")
        self.assertTrue(archive.allowed)
        self.assertTrue(train.allowed)
        self.assertTrue(train.training_allowed)

    def test_cc_by_requires_attribution(self):
        decision = self.sagar.rights_decision("archive", license_id="CC-BY-4.0", source_default_max_mode="index")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.attribution_required)
        self.assertTrue(decision.commercial_allowed)

    def test_noncommercial_is_blocked_for_commercial_archive(self):
        decision = self.sagar.rights_decision("archive", license_id="CC-BY-NC-4.0", source_default_max_mode="read")
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.commercial_allowed)
        self.assertTrue(decision.review_required)

    def test_no_derivatives_is_never_auto_training_approved(self):
        decision = self.sagar.rights_decision("train", license_id="CC-BY-ND-4.0", source_default_max_mode="read")
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.training_allowed)

    def test_permissive_software_license_does_not_auto_authorize_training(self):
        archive = self.sagar.rights_decision("archive", license_id="MIT", source_default_max_mode="read")
        train = self.sagar.rights_decision("train", license_id="MIT", source_default_max_mode="read")
        self.assertTrue(archive.allowed)
        self.assertFalse(train.allowed)
        self.assertTrue(train.review_required)

    def test_knowledge_record_preserves_provenance_and_rights(self):
        row = self.sagar.make_record(
            title="Example open paper",
            source_id="doaj",
            source_url="https://example.org/paper",
            source_type="paper",
            identifier="doi:10.1/example",
            authors=["A. Researcher"],
            license_id="CC-BY-4.0",
            checksum="a" * 64,
            peer_reviewed=True,
            primary=True,
            rishi_owner="gautama",
            knowledge_track="modern_science",
        )
        self.assertEqual(row["source_id"], "doaj")
        self.assertEqual(row["rishi_owner"], "gautama")
        self.assertTrue(row["rights"]["archive"]["allowed"])
        self.assertTrue(row["rights"]["archive"]["attribution_required"])

    def test_archive_gate_requires_item_license_when_source_requires_it(self):
        row = self.sagar.make_record(
            title="Unknown licence paper",
            source_id="pmc",
            source_url="https://pmc.ncbi.nlm.nih.gov/articles/example",
            checksum="b" * 64,
            rishi_owner="sushruta",
        )
        gate = self.sagar.ingestion_gate(row, "archive")
        self.assertFalse(gate["allowed"])
        self.assertTrue(any("licence" in x.lower() for x in gate["problems"]))

    def test_training_gate_requires_checksum(self):
        row = self.sagar.make_record(
            title="Open training candidate",
            source_id="doab",
            source_url="https://example.org/book",
            license_id="CC0-1.0",
            rishi_owner="veda-vyasa",
        )
        gate = self.sagar.ingestion_gate(row, "train")
        self.assertFalse(gate["allowed"])
        self.assertTrue(any("checksum" in x.lower() for x in gate["problems"]))

    def test_rfc_editor_is_official_archive_capable_source(self):
        rfc = self.sagar.source("rfc-editor")
        self.assertEqual(rfc["default_max_mode"], "archive")
        self.assertEqual(rfc["bulk_policy"], "official-rsync-mirror")

    def test_openlibrary_bulk_policy_avoids_high_volume_api_abuse(self):
        ol = self.sagar.source("openlibrary")
        self.assertIn("monthly-dumps", ol["bulk_policy"])


if __name__ == "__main__":
    unittest.main()
