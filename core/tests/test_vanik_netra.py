import tempfile
import unittest
from pathlib import Path

from krishna_core.manibhadra_crm import ManibhadraCRM
from krishna_core.vanik_netra import VanikNetra
from krishna_core.vanik_netra_sources import BoundingBox, FoursquareOSAdapter, OSMExtractAdapter
from krishna_core.vanik_netra_store import VanikNetraStore


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


class FakeOverture:
    def status(self): return {"id":"overture","free":True,"live_scan":True}
    def scan(self,bbox,**kwargs):
        return [
            {"source":"overture","id":"a","name":"Alpha Hardware","category":"hardware","phone":"111","longitude":85.86,"latitude":20.296},
            {"source":"overture","id":"b","name":"Beta Clinic","category":"clinic","website":"https://beta.test","longitude":85.861,"latitude":20.297},
        ]


class FakeRegistry:
    def __init__(self):
        self.overture=FakeOverture()
        self.foursquare=FoursquareOSAdapter()
        self.osm=OSMExtractAdapter()
    def status(self): return {"zero_spend":True,"paid_fallback":False,"sources":{"overture":self.overture.status()}}


class VanikNetraPipelineTests(unittest.TestCase):
    def test_bbox_validation(self):
        box=BoundingBox.from_value({"west":85.84,"south":20.28,"east":85.88,"north":20.31})
        self.assertEqual(box.west,85.84)
        with self.assertRaises(ValueError):
            BoundingBox(86,20,85,21)

    def test_foursquare_local_csv_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"fsq.csv"
            path.write_text("fsq_place_id,name,latitude,longitude,tel,website\n1,Shop A,20.29,85.86,999,https://a.test\n",encoding="utf-8")
            rows=FoursquareOSAdapter.load_local(path)
            self.assertEqual(rows[0]["source"],"foursquare_os")
            self.assertEqual(rows[0]["name"],"Shop A")

    def test_osm_geojson_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"osm.geojson"
            path.write_text(
                '{"type":"FeatureCollection","features":[{"type":"Feature","id":"node/1","geometry":{"type":"Point","coordinates":[85.86,20.29]},"properties":{"name":"Repair Shop","shop":"car_repair","contact:phone":"999"}}]}',
                encoding="utf-8",
            )
            rows=OSMExtractAdapter.load_geojson(path)
            self.assertEqual(rows[0]["category"],"car_repair")
            self.assertEqual(rows[0]["phone"],"999")
            self.assertEqual(rows[0]["source"],"openstreetmap_extract")

    def test_store_detects_added_changed_removed(self):
        with tempfile.TemporaryDirectory() as td:
            store=VanikNetraStore(Path(td)/"market.db")
            first=[
                VanikNetra.normalize_place({"source":"overture","id":"1","name":"One","phone":"1","lat":20.29,"lon":85.86}),
                VanikNetra.normalize_place({"source":"overture","id":"2","name":"Two","phone":"2","lat":20.30,"lon":85.87}),
            ]
            snap1=store.save_snapshot("rasulgarh",first,source="overture",bbox={"west":85.8,"south":20.2,"east":85.9,"north":20.4})
            self.assertEqual(snap1["changes"]["added"],2)
            second=[
                VanikNetra.normalize_place({"source":"overture","id":"1","name":"One","phone":"111","lat":20.29,"lon":85.86}),
                VanikNetra.normalize_place({"source":"overture","id":"3","name":"Three","phone":"3","lat":20.31,"lon":85.88}),
            ]
            snap2=store.save_snapshot("rasulgarh",second,source="overture",bbox={"west":85.8,"south":20.2,"east":85.9,"north":20.4})
            self.assertEqual(snap2["changes"],{"added":1,"changed":1,"removed":1})
            changes=store.changes("rasulgarh")
            self.assertEqual({x["change_type"] for x in changes},{"added","changed","removed"})

    def test_scan_area_persists_and_builds_map_payload(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            store=VanikNetraStore(Path(td)/"market.db")
            agent=VanikNetra(crm,store=store,sources=FakeRegistry())
            out=agent.scan_area(
                {"west":85.84,"south":20.28,"east":85.88,"north":20.31},
                area_key="rasulgarh",source="overture",limit=100,
            )
            self.assertEqual(out["record_count"],2)
            self.assertEqual(out["snapshot"]["changes"]["added"],2)
            cached=agent.stored_area({"west":85.84,"south":20.28,"east":85.88,"north":20.31})
            self.assertEqual(cached["summary"]["businesses"],2)
            points=agent.map_payload(cached["records"])
            self.assertEqual(len(points["points"]),2)
            self.assertIsNotNone(points["bounds"])


class VanikNetraWhiteSpaceTests(unittest.TestCase):
    def test_white_space_uses_density_as_proxy_not_guaranteed_demand(self):
        with tempfile.TemporaryDirectory() as td:
            store=VanikNetraStore(Path(td)/"market.db")
            rows=[]
            for i in range(6):
                rows.append(VanikNetra.normalize_place({
                    "source":"overture","id":f"r{i}","name":f"Retail {i}",
                    "category":"retail","lat":20.2901+i*0.00001,"lon":85.8601+i*0.00001,
                }))
            rows.append(VanikNetra.normalize_place({
                "source":"overture","id":"h1","name":"Hardware One",
                "category":"hardware","lat":20.3001,"lon":85.8701,
            }))
            for i in range(4):
                rows.append(VanikNetra.normalize_place({
                    "source":"overture","id":f"x{i}","name":f"Other {i}",
                    "category":"retail","lat":20.3002+i*0.00001,"lon":85.8702+i*0.00001,
                }))
            store.save_snapshot("market",rows)
            out=store.white_space(
                {"west":85.85,"south":20.28,"east":85.88,"north":20.31},
                "hardware",min_cell_businesses=3,
            )
            self.assertTrue(out["cells"])
            self.assertIn("proxy",out["warning"].lower())
            self.assertEqual(out["target_category"],"hardware")



if __name__=="__main__":
    unittest.main()
