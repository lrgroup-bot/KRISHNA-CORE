import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.diagnostic_transport import DiagnosticEvidenceTransport


class DiagnosticEvidenceTransportTests(unittest.TestCase):
    def test_electronics_json_is_ingested_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"meter.json"
            path.write_text(json.dumps({
                "source":"multimeter-1",
                "measurements":[{"point":"TP1","quantity":"voltage","value":12.4,"unit":"V"}]
            }),encoding="utf-8")
            out=DiagnosticEvidenceTransport(root).ingest("electronics",path)
            self.assertTrue(out["read_only"])
            self.assertFalse(out["hardware_verified"])
            self.assertEqual(out["result"]["evidence_state"],"MEASURED")

    def test_vehicle_transmit_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"can.json"
            path.write_text(json.dumps({
                "frames":[{"can_id":0x123,"data":[1,2,3],"action":"transmit"}]
            }),encoding="utf-8")
            with self.assertRaises(PermissionError):
                DiagnosticEvidenceTransport(root).ingest("can",path)

    def test_transport_refuses_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"inbox";root.mkdir()
            outside=Path(td)/"outside.json";outside.write_text("{}",encoding="utf-8")
            with self.assertRaises(PermissionError):
                DiagnosticEvidenceTransport(root).ingest("electronics",outside)


if __name__=="__main__":
    unittest.main()
