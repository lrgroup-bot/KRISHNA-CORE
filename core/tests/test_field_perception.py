import tempfile
import unittest
from pathlib import Path

from krishna_core.bhumiputra import BhumiputraAgent
from krishna_core.field_perception import FieldPerceptionPolicy


class FakeVision:
    def analyze_bytes(self,data,content_type,prompt):
        return {
            "provider":"fake-local",
            "model":"fake-vision",
            "local":True,
            "analysis":"scene_type: document; username: alice; password: hunter2; OTP: 123456; visible sign: EXIT",
        }


class FieldPerceptionTests(unittest.TestCase):
    def test_capability_catalog_includes_expanded_live_modes(self):
        ids={x["id"] for x in FieldPerceptionPolicy.catalog()}
        self.assertTrue({
            "structure-detail","people-scene","ocr-assets","vehicle-inspection",
            "electronics-inspection","terrain-site","hazard-watch","temporal-change",
            "sensitive-input-guard",
        }.issubset(ids))

    def test_sensitive_authentication_values_are_redacted(self):
        text=FieldPerceptionPolicy.redact_sensitive_text(
            "password: secret123 PIN=7788 OTP: 123456 api_key: abcdefghijklmnop authorization: bearer xyzxyzxyz"
        )
        for secret in ("secret123","7788","123456","abcdefghijklmnop","xyzxyzxyz"):
            self.assertNotIn(secret,text)
        self.assertGreaterEqual(text.count("[SECRET REDACTED]"),5)

    def test_live_prompt_covers_field_people_vehicle_electronics_and_secret_guard(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"bhumiputra",vision_adapter=FakeVision())
            prompt=agent.live_prompt(scene_hint="auto",user_goal="inspect scene")
            self.assertIn("structures/buildings",prompt)
            self.assertIn("vehicles",prompt)
            self.assertIn("electronics",prompt)
            self.assertIn("people",prompt)
            self.assertIn("NEVER transcribe",prompt)
            self.assertIn("OBD/CAN/J1939",prompt)

    def test_live_frame_ingestion_uses_local_vision_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"bhumiputra",vision_adapter=FakeVision())
            session=agent.start_live_session(purpose="inspect screen",scene_hint="document")
            out=agent.ingest_live_frame(
                session["session_id"],b"jpeg-bytes","image/jpeg",{"source":"test"}
            )
            self.assertEqual(out["frame_count"],1)
            self.assertEqual(out["provider"],"fake-local")
            self.assertIn("visible sign: EXIT",out["analysis"])
            self.assertNotIn("hunter2",out["analysis"])
            self.assertNotIn("123456",out["analysis"])
            stored=agent.get_live_session(session["session_id"])
            self.assertNotIn("hunter2",stored["latest_analysis"]["analysis"])
            self.assertTrue(out["privacy"]["secret_redaction"])

    def test_server_live_response_uses_redacted_persisted_analysis(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('result["analysis"]=field["latest_analysis"]["analysis"]',source)
        self.assertIn('"analysis":field["latest_analysis"]["analysis"]',source)
        self.assertIn('"secret_redaction":True',source)

    def test_face_identity_policy_is_enrollment_scoped(self):
        face=FieldPerceptionPolicy.status()["face_recognition"]
        self.assertEqual(face["unknown_person_identity"],"UNKNOWN")
        self.assertFalse(face["cloud_biometrics"])
        self.assertEqual(face["identity_adapter_state"],"adapter_required")

    def test_existing_mobile_evidence_contract_remains_available(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"bhumiputra",vision_adapter=FakeVision())
            self.assertTrue(hasattr(agent,"store_mobile_evidence"))
            status=agent.status()
            self.assertIn("mobile_evidence",status)
            self.assertIn("perception",status)


if __name__=="__main__":
    unittest.main()
