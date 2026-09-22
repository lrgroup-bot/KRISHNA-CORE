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
    def test_capability_catalog_includes_expected_live_modes(self):
        ids={x["id"] for x in FieldPerceptionPolicy.catalog()}
        self.assertIn("structure-detail",ids)
        self.assertIn("people-scene",ids)
        self.assertIn("ocr-assets",ids)
        self.assertIn("vehicle-inspection",ids)
        self.assertIn("electronics-inspection",ids)
        self.assertIn("hazard-watch",ids)
        self.assertIn("sensitive-input-guard",ids)

    def test_sensitive_authentication_values_are_redacted(self):
        text=FieldPerceptionPolicy.redact_sensitive_text(
            "password: secret123 PIN=7788 OTP: 123456 api_key: abcdefghijklmnop authorization: bearer xyzxyzxyz"
        )
        self.assertNotIn("secret123",text)
        self.assertNotIn("7788",text)
        self.assertNotIn("123456",text)
        self.assertNotIn("abcdefghijklmnop",text)
        self.assertNotIn("xyzxyzxyz",text)
        self.assertGreaterEqual(text.count("[SECRET REDACTED]"),5)

    def test_live_prompt_covers_buildings_people_vehicles_electronics_and_secret_guard(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"bhumiputra",vision_adapter=FakeVision())
            prompt=agent.live_prompt(scene_hint="auto",user_goal="inspect scene")
            self.assertIn("structures/buildings",prompt)
            self.assertIn("vehicles",prompt)
            self.assertIn("electronics",prompt)
            self.assertIn("people",prompt)
            self.assertIn("NEVER transcribe",prompt)

    def test_live_frame_ingestion_uses_local_vision_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"bhumiputra",vision_adapter=FakeVision())
            session=agent.start_live_session(purpose="inspect screen",scene_hint="document")
            out=agent.ingest_live_frame(session["session_id"],b"jpeg-bytes","image/jpeg",{"source":"test"})
            self.assertEqual(out["frame_count"],1)
            self.assertEqual(out["provider"],"fake-local")
            self.assertIn("visible sign: EXIT",out["analysis"])
            self.assertNotIn("hunter2",out["analysis"])
            self.assertNotIn("123456",out["analysis"])
            stored=agent.get_live_session(session["session_id"])
            self.assertNotIn("hunter2",stored["latest_analysis"]["analysis"])
            self.assertTrue(out["privacy"]["secret_redaction"])

    def test_face_identity_policy_is_enrollment_scoped(self):
        face=FieldPerceptionPolicy.status()["face_recognition"]
        self.assertEqual(face["unknown_person_identity"],"UNKNOWN")
        self.assertFalse(face["cloud_biometrics"])
        self.assertEqual(face["identity_adapter_state"],"adapter_required")


if __name__=="__main__":
    unittest.main()
