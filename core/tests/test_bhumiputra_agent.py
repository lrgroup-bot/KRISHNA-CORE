import tempfile
import unittest
from pathlib import Path

from krishna_core.bhumiputra import BhumiputraAgent


class BhumiputraAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = BhumiputraAgent(Path(self.tmp.name) / "bhumiputra")
        self.square = [
            {"lat": 20.3000, "lon": 85.8000},
            {"lat": 20.3000, "lon": 85.8010},
            {"lat": 20.3010, "lon": 85.8010},
            {"lat": 20.3010, "lon": 85.8000},
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_boundary_metrics_are_positive(self):
        out = self.agent.boundary_metrics(self.square)
        self.assertGreater(out["area_m2"], 1)
        self.assertGreater(out["perimeter_m"], 1)
        self.assertEqual(out["point_count"], 4)

    def test_survey_plan_is_isolated_and_truthful_about_subsurface(self):
        out = self.agent.plan_survey(self.square, project="KRISHNA")
        self.assertFalse(out["execution"]["main_loop_blocking"])
        self.assertEqual(out["execution"]["heavy_compute"], "isolated worker/process only")
        self.assertIn("never claim verified", out["confidence_policy"]["subsurface_resource"])
        self.assertTrue(self.agent.get_survey(out["survey_id"]))

    def test_field_observation_is_persisted(self):
        survey = self.agent.plan_survey(self.square)
        receipt = self.agent.record_observation(
            survey["survey_id"],
            {"type": "road-width", "payload": {"width_m": 6.8}, "confidence": "measured"},
        )
        self.assertEqual(receipt["count"], 1)
        stored = self.agent.get_survey(survey["survey_id"])
        self.assertEqual(stored["observations"][0]["payload"]["width_m"], 6.8)

    def test_live_structure_session_and_truth_policy(self):
        session = self.agent.start_live_session(
            project="KRISHNA", purpose="inspect transmission tower", scene_hint="auto"
        )
        prompt = self.agent.live_prompt(
            scene_hint="tower",
            user_goal="check visible design and condition",
            sensor_context={"gps_accuracy_m": 3.2},
        )
        self.assertIn("hidden reinforcement", prompt)
        self.assertIn("load capacity", prompt)
        receipt = self.agent.record_live_analysis(
            session["session_id"],
            "scene_type: structure; observed: lattice tower members; unknown: foundation condition",
            model="local-vision",
            sensor_context={"gps_accuracy_m": 3.2},
        )
        self.assertEqual(receipt["frame_count"], 1)
        self.assertIn("foundation", receipt["truth_policy"])

    def test_curated_mobile_evidence_is_bounded_and_deduplicated(self):
        session = self.agent.start_live_session(project="KRISHNA", purpose="diagnose PCB")
        raw = b"curated-jpeg-evidence"
        sensors = {"curator_selected": True, "mobile_observation_id": "HAW-1"}
        first = self.agent.store_mobile_evidence(session["session_id"], raw, "image/jpeg", sensors)
        second = self.agent.store_mobile_evidence(session["session_id"], raw, "image/jpeg", sensors)
        self.assertTrue(first["retained_pc"])
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(first["sha256"], second["sha256"])
        status = self.agent.mobile_evidence_status()
        self.assertEqual(status["items"], 1)
        self.assertLessEqual(status["max_items"], 64)
        self.assertLessEqual(status["max_bytes"], 192 * 1024 * 1024)

    def test_curated_audio_and_video_are_bounded(self):
        session=self.agent.start_live_session(project="KRISHNA",purpose="diagnose bearing noise")
        audio=self.agent.store_mobile_evidence(session["session_id"],b"a"*1024,"audio/webm",{"curator_selected":True})
        video=self.agent.store_mobile_evidence(session["session_id"],b"v"*2048,"video/webm",{"curator_selected":True})
        self.assertEqual(audio["modality"],"audio")
        self.assertEqual(video["modality"],"video")
        self.assertTrue(audio["retained_pc"])
        self.assertTrue(video["retained_pc"])
        with self.assertRaises(ValueError):
            self.agent.store_mobile_evidence(session["session_id"],b"x"*(1024*1024+1),"audio/webm",{})

    def test_pc_evidence_can_be_encrypted_fail_closed(self):
        class FakeCipher:
            available=True
            def encrypt(self,data,aad=b""):
                return {"schema":1,"alg":"AES-256-GCM","ciphertext_b64":"TEST","aad":aad.decode("utf-8")}
        self.agent.bind_evidence_cipher(FakeCipher(),require_encryption=True)
        session=self.agent.start_live_session(project="KRISHNA",purpose="diagnose PCB")
        out=self.agent.store_mobile_evidence(session["session_id"],b"secret-image","image/jpeg",{"curator_selected":True})
        self.assertTrue(out["encrypted_at_rest"])
        self.assertTrue(any(self.agent.evidence_dir.glob("*.payload.enc")))
        self.assertFalse(any(self.agent.evidence_dir.glob("*.jpg")))

    def test_degenerate_boundary_rejected(self):
        with self.assertRaises(ValueError):
            self.agent.boundary_metrics([
                {"lat": 20.3, "lon": 85.8},
                {"lat": 20.3, "lon": 85.8},
                {"lat": 20.3, "lon": 85.8},
            ])


if __name__ == "__main__":
    unittest.main()
