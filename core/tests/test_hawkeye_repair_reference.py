import io
import json
import unittest
from krishna_core.hawkeye_repair_reference import HawkeyeRepairReference

class Response:
    status=200
    def __init__(self,data): self.buf=io.BytesIO(json.dumps(data).encode())
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.buf.read(n)

class HawkeyeRepairReferenceTests(unittest.TestCase):
    def test_opt_in_required(self):
        with self.assertRaises(PermissionError):
            HawkeyeRepairReference().search_module("Laptop A","battery")
    def test_attributed_links_only(self):
        def fake(req,timeout):
            self.assertIn("/suggest/",req.full_url)
            return Response({"results":[{"title":"Battery replacement","url":"https://www.ifixit.com/Guide/Example/123","dataType":"guide"},
                                        {"title":"Malicious","url":"https://attacker.example/guide"}]})
        client=HawkeyeRepairReference(enabled=True,opener=fake)
        card=client.hawkeye_module_card("Laptop A","battery",measured_evidence=["photo:1"])
        self.assertEqual(len(card["repair_references"]),1)
        self.assertFalse(card["repair_authorized"])
        self.assertEqual(card["diagnosis"],"not_established")
    def test_reject_invalid_query(self):
        with self.assertRaises(ValueError):
            HawkeyeRepairReference(enabled=True).search_module("x","battery")
if __name__=="__main__":
    unittest.main()
