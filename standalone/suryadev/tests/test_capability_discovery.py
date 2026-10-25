"""No node may claim an unavailable PDF/YouTube/browser backend."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from suryadev_capabilities import installed_capabilities
from suryadev_fleet_client import hardware_report


class CapabilityDiscoveryTests(unittest.TestCase):
    def test_source_backends_are_discovered_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_packages=installed_capabilities(tmp,installed=lambda _: False)
            self.assertEqual(no_packages["capabilities"],[])
            only_pdf=installed_capabilities(tmp,installed=lambda name: name=="pypdf")
            self.assertEqual(only_pdf["capabilities"],["pdf"])
            only_video=installed_capabilities(tmp,installed=lambda name: name=="yt_dlp")
            self.assertEqual(only_video["capabilities"],["youtube"])
            self.assertFalse(only_video["sources"]["youtube"]["provider_access_verified"])
            self.assertFalse(no_packages["sources"]["website"]["browser_runtime_verified"])

    def test_book_capability_requires_valid_plan_and_source(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            plan=root/"book-collect-plan.json"
            plan.write_text("{}",encoding="utf-8")
            self.assertNotIn("book",installed_capabilities(
                root,installed=lambda _:False)["capabilities"])
            book=root/"approved.txt"
            book.write_text("Public learning example book",encoding="utf-8")
            digest=hashlib.sha256(book.read_bytes()).hexdigest()
            plan.write_text(json.dumps({
                "schema":"suryadev.book-plan.v1",
                "books":[{"path":str(book),"sha256":digest}],
                "lines_per_step":1
            }),encoding="utf-8")
            found=installed_capabilities(root,installed=lambda _:False)
            self.assertEqual(found["capabilities"],["book"])
            book.unlink()
            self.assertNotIn("book",installed_capabilities(
                root,installed=lambda _:False)["capabilities"])

    def test_no_surprise_capabilities_in_authenticated_hardware_report(self):
        reading={"available":True,"sample_time":100,
                 "cpu_percent":10,"ram_percent":20,"disk_percent":10,
                 "ram_total_gb":16,"ram_used_gb":3.2,"disk_free_gb":50,
                 "gpu":{"available":False}}
        with tempfile.TemporaryDirectory() as tmp, \
             patch("suryadev_fleet_client.installed_capabilities",
                   return_value={"capabilities":["pdf"],"status":"installed_prerequisites_only",
                                 "sources":{}}):
            report=hardware_report(tmp,sample=reading,now=100)
        self.assertEqual(report["capabilities"],["pdf"])
        self.assertNotIn("youtube",report["capabilities"])
        self.assertGreater(report["max_total"],0)


if __name__=="__main__":
    unittest.main()
