import unittest

from krishna_core.capability_fabric import CapabilityFabric
from krishna_core.rishi_deep_sources import RishiDeepSourceExpansion


class RishiDeepSourceTests(unittest.TestCase):
    def setUp(self):
        self.deep=RishiDeepSourceExpansion()

    def test_deep_catalog_covers_missing_books_datasets_space_and_standards(self):
        ids={x["id"] for x in self.deep.list_sources()}
        for needed in (
            "datacite","openaire","zenodo","ncbi-bookshelf","standard-ebooks","openstax",
            "nasa-ntrs","nasa-ads","etsi","3gpp","khronos","whatwg",
        ):
            self.assertIn(needed,ids)

    def test_openstax_is_read_only_in_commercial_context_by_default(self):
        source=self.deep.source("openstax")
        self.assertEqual(source["default_max_mode"],"read")
        self.assertIn("CC BY-NC-SA",source["notes"])

    def test_bookshelf_forbids_unverified_systematic_crawling(self):
        source=self.deep.source("ncbi-bookshelf")
        self.assertIn("official-oai",source["bulk_policy"])
        self.assertIn("No systematic crawling",source["notes"])

    def test_telecom_and_graphics_standards_are_conservative_read_sources(self):
        for sid in ("etsi","3gpp","khronos"):
            self.assertEqual(self.deep.source(sid)["default_max_mode"],"read")

    def test_dataset_research_plan_prefers_datacite_openaire_and_zenodo(self):
        rows=self.deep.research_plan(
            "research datasets software DOI open science",
            rishi_id="bharadvaja",max_sources=8,
        )
        ids={x["id"] for x in rows}
        self.assertIn("datacite",ids)
        self.assertIn("openaire",ids)
        self.assertIn("zenodo",ids)

    def test_space_research_plan_includes_nasa_sources(self):
        rows=self.deep.research_plan(
            "astronomy spacecraft planetary science technical report",
            rishi_id="atri",max_sources=8,
        )
        ids={x["id"] for x in rows}
        self.assertIn("nasa-ntrs",ids)
        self.assertIn("nasa-ads",ids)

    def test_technology_plan_includes_free_public_standards_sources(self):
        rows=self.deep.research_plan(
            "6g telecom vulkan web browser technology standards",
            rishi_id="vishwamitra",max_sources=10,
        )
        ids={x["id"] for x in rows}
        for needed in ("etsi","3gpp","khronos","whatwg"):
            self.assertIn(needed,ids)

    def test_datacite_request_is_public_and_bounded(self):
        plan=self.deep.request_plan("datacite","battery recycling dataset")
        self.assertIn("query=battery+recycling+dataset",plan["url"])
        self.assertFalse(plan["secret_required"])
        self.assertIn("do not purchase",plan["zero_spend_rule"])

    def test_ads_requires_free_token_and_tracks_2026_migration(self):
        source=self.deep.source("nasa-ads")
        self.assertEqual(source["auth"],"free-api-token")
        self.assertIn("2026-11-16",source["notes"])
        plan=self.deep.request_plan("nasa-ads","exoplanet atmosphere",api_key_ref="vault:nasa-ads")
        self.assertTrue(plan["secret_required"])
        self.assertEqual(plan["api_key_ref"],"vault:nasa-ads")

    def test_capability_fabric_merges_base_and_deep_catalogs(self):
        fabric=CapabilityFabric()
        status=fabric.knowledge_status()
        self.assertGreater(status["total_source_count"],status["sagar"]["source_count"])
        out=fabric.knowledge_plan("6g telecom technology standards",rishi_id="vishwamitra",max_sources=20)
        ids={x["id"] for x in out["plan"]["sources"]}
        self.assertIn("3gpp",ids)
        self.assertIn("etsi",ids)
        self.assertIn("rishi-deep-sources",out["plan"]["source_fabrics"])

    def test_capability_request_uses_deep_source_adapter(self):
        out=CapabilityFabric().knowledge_request("zenodo","robotics dataset")
        self.assertEqual(out["request"]["source_id"],"zenodo")
        self.assertIn("q=robotics+dataset",out["request"]["url"])


if __name__ == "__main__":
    unittest.main()
