import tempfile
import unittest
from pathlib import Path

from krishna_core.manibhadra_crm import ManibhadraCRM
from krishna_core.vanik_netra import VanikNetra


class VanikNetraTests(unittest.TestCase):
    def test_status_is_zero_spend_and_blocks_google_bulk_scraping(self):
        agent=VanikNetra()
        status=agent.status()
        self.assertTrue(status["zero_spend"])
        self.assertFalse(status["paid_sources_enabled"])
        self.assertFalse(status["external_outreach_enabled"])
        self.assertFalse(status["google_maps_bulk_scraping"])
        self.assertTrue(status["sources"]["google_maps_bulk_scrape"]["blocked"])

    def test_normalize_generates_navigation_link_without_google_ingestion(self):
        row=VanikNetra.normalize_place({
            "source":"overture","id":"abc","name":"Example Hardware",
            "category":"hardware_store","phone":"+91 99999 11111",
            "address":"Rasulgarh, Bhubaneswar, Odisha",
            "lat":20.296,"lon":85.86,"confidence":0.9,
        })
        self.assertEqual(row["name"],"Example Hardware")
        self.assertEqual(row["primary_category"],"hardware_store")
        self.assertIn("google.com/maps/search",row["google_maps_navigation_url"])
        self.assertEqual(row["sources"],["overture"])

    def test_deduplicates_same_place_across_sources(self):
        rows=[
            {
                "source":"overture","id":"o1","name":"ABC Motors",
                "address":"Rasulgarh, Bhubaneswar","phone":"9999911111",
                "lat":20.2960,"lon":85.8600,"confidence":0.8,
            },
            {
                "source":"foursquare_os","fsq_place_id":"f1","name":"ABC Motors",
                "address":"Rasulgarh, Bhubaneswar","phone":"9999911111",
                "website":"https://example.test","lat":20.29601,"lon":85.86001,
                "confidence":0.9,
            },
        ]
        out=VanikNetra.deduplicate(rows)
        self.assertEqual(len(out),1)
        self.assertEqual(set(out[0]["sources"]),{"overture","foursquare_os"})
        self.assertEqual(out[0]["website"],"https://example.test")
        self.assertEqual(out[0]["confidence"],0.9)

    def test_area_analysis_finds_reachable_no_website_opportunities(self):
        rows=[
            {"name":"A","source":"overture","category":"hardware","phone":"1"},
            {"name":"B","source":"overture","category":"hardware","website":"https://b.test"},
            {"name":"C","source":"overture","category":"clinic","email":"c@example.test"},
        ]
        report=VanikNetra.analyze_area(rows)
        self.assertEqual(report["businesses"],3)
        self.assertEqual(report["opportunities"]["no_website"],2)
        self.assertEqual(report["opportunities"]["no_website_but_reachable"],2)
        self.assertEqual(report["categories"][0],{"category":"hardware","count":2})

    def test_crm_handoff_creates_local_lead_only(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            agent=VanikNetra(crm)
            lead=agent.import_to_crm({
                "name":"Rasulgarh Shop","source":"foursquare_os",
                "category":"retail","phone":"9999999999",
                "address":"Rasulgarh, Bhubaneswar",
            })
            self.assertEqual(lead["company"],"Rasulgarh Shop")
            self.assertEqual(lead["stage"],"new")
            self.assertIn("vanik-netra",lead["tags"])
            self.assertEqual(lead["next_action"],"Review opportunity before any outreach")
            self.assertEqual(len(crm.records()["leads"]),1)


if __name__=="__main__":
    unittest.main()
