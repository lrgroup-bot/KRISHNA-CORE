import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.chandradev import ChandradevQC
from krishna_core.chandradev_camera import (
    CHANDRADEV_CAMERA_SELECTION,
    ChandradevOsmoCameraAdapter,
    OSMO_ACTION_ORIGINAL_PROFILE,
    ZEB_PURE_PLUS_PROFILE,
)


class FakeVision:
    def analyze_bytes(self,data,content_type,prompt,mode="detailed"):
        return {
            "provider":"ollama",
            "model":"fake-local-vision",
            "vision_mode":mode,
            "local":True,
            "analysis":"A workshop scene with a vehicle and tools.",
        }


class ChandradevOsmoCameraTests(unittest.TestCase):
    def runtime(self,root,**kwargs):
        return ChandradevOsmoCameraAdapter(
            Path(root)/"chandradev-camera",
            stream_name="osmo-test",
            mediamtx_exe=Path(root)/"tools"/"mediamtx.exe",
            **kwargs,
        )

    def test_original_osmo_hardware_contract(self):
        p=OSMO_ACTION_ORIGINAL_PROFILE
        self.assertEqual(p["model"],"DJI Osmo Action (original)")
        self.assertFalse(p["uvc_webcam"])
        self.assertFalse(p["hdmi_output"])
        self.assertEqual(p["live_transport"],"DJI Mimo -> RTMP")
        self.assertEqual(p["livestream"]["resolutions"],["480p","720p"])
        self.assertEqual(p["livestream"]["fps"],30)
        self.assertEqual(p["camera"]["recording"],["4K60","1080p240"])
        self.assertEqual(p["audio"]["built_in_microphones"],2)
        self.assertEqual(p["field_hardware"]["waterproof_without_case_m"],11)

    def test_future_zeb_webcam_is_prepared_but_not_active(self):
        profile=ZEB_PURE_PLUS_PROFILE
        self.assertEqual(profile["model"],"ZEBRONICS ZEB-Pure Plus")
        self.assertEqual(profile["target_mode"]["resolution"],"3840x2160")
        self.assertEqual(profile["target_mode"]["fps"],30)
        self.assertTrue(profile["camera"]["autofocus"])
        self.assertTrue(profile["camera"]["built_in_microphone"])
        self.assertEqual(profile["mounting"]["budget_mount_target_inr"],500)
        self.assertFalse(profile["mounting"]["expensive_arm_required"])
        self.assertEqual(CHANDRADEV_CAMERA_SELECTION["active_validation_source"],"dji_osmo_action_rtmp")
        self.assertFalse(CHANDRADEV_CAMERA_SELECTION["automatic_source_switching"])

    def test_future_webcam_status_does_not_claim_hardware_is_connected(self):
        with tempfile.TemporaryDirectory() as td:
            out=self.runtime(td).future_webcam_profile()
        self.assertFalse(out["active_now"])
        self.assertIn("DJI Osmo Action",out["validation_now"])
        self.assertEqual(out["profile"]["deployment_state"],"planned_not_connected")

    def test_alignment_handoff_routes_through_krishna_and_clears_stale_lock(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            v._state["screen_lock"]={"normalized_quad":[[0,0],[1,0],[1,1],[0,1]]}
            v._save(v._state)
            handoff=v._alignment_handoff("camera_or_mount_unstable",details={"test":True})
            state=v.alignment_status()
        self.assertTrue(handoff["owner_handoff_required"])
        self.assertEqual(handoff["route_through"],"KRISHNA")
        self.assertIsNone(state["screen_lock"])
        self.assertTrue(state["owner_handoff_required"])
        self.assertEqual(state["alignment_handoff"]["reason"],"camera_or_mount_unstable")

    def test_normalized_quad_motion_distinguishes_stable_and_unstable_mount(self):
        base=[[0.10,0.10],[0.90,0.10],[0.90,0.90],[0.10,0.90]]
        stable=[
            base,
            [[0.101,0.101],[0.901,0.101],[0.901,0.901],[0.101,0.901]],
            [[0.102,0.101],[0.902,0.101],[0.902,0.901],[0.102,0.901]],
        ]
        unstable=[
            base,
            [[0.14,0.12],[0.94,0.12],[0.94,0.92],[0.14,0.92]],
            [[0.20,0.15],[1.00,0.15],[1.00,0.95],[0.20,0.95]],
        ]
        self.assertTrue(ChandradevOsmoCameraAdapter._normalized_quad_motion(stable)["stable"])
        self.assertFalse(ChandradevOsmoCameraAdapter._normalized_quad_motion(unstable)["stable"])

    def test_exact_mimo_and_local_urls(self):
        with tempfile.TemporaryDirectory() as td:
            urls=self.runtime(td).urls("192.168.0.50")
            self.assertEqual(urls["mimo_push_url"],"rtmp://192.168.0.50:1935/osmo-test")
            self.assertEqual(urls["local_rtmp_url"],"rtmp://127.0.0.1:1935/osmo-test")
            self.assertEqual(urls["local_hls_url"],"http://127.0.0.1:8888/osmo-test/index.m3u8")

    def test_mediamtx_config_exposes_only_rtmp_to_lan(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            cfg=v.mediamtx_config()
            self.assertIn("rtmpAddress: :1935",cfg)
            self.assertIn("hlsAddress: 127.0.0.1:8888",cfg)
            self.assertIn("webrtcAddress: 127.0.0.1:8889",cfg)
            self.assertIn("overridePublisher: false",cfg)
            self.assertTrue(Path(v.ensure_config()["config_path"]).is_file())

    def test_connection_guide_is_chandradev_only(self):
        with tempfile.TemporaryDirectory() as td:
            guide=self.runtime(td).connection_guide("10.0.0.5")
            self.assertEqual(guide["mimo_push_url"],"rtmp://10.0.0.5:1935/osmo-test")
            self.assertEqual(guide["recommended_original_osmo_settings"]["resolution"],"720p")
            self.assertIn("Chandradev reads, analyzes and records",guide["steps"][-1])

    def test_status_is_pc_chandradev_camera_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            status=self.runtime(td).status()
            self.assertEqual(status["component"],"CHANDRADEV OSMO CAMERA ADAPTER")
            self.assertIn("standalone PC",status["role"])
            self.assertIn("-> CHANDRADEV",status["live_path"])
            self.assertFalse(status["mediamtx"]["installed"])
            self.assertFalse(status["cloud_required"])
            self.assertFalse(status["paid_service_required"])
            self.assertEqual(status["camera_selection"]["active_validation_source"],"dji_osmo_action_rtmp")
            self.assertEqual(status["future_webcam_profile"]["deployment_state"],"planned_not_connected")

    def test_runtime_and_powershell_share_one_stream_name(self):
        with tempfile.TemporaryDirectory() as td:
            shared=Path(td)/"shared"
            shared.mkdir()
            (shared/"stream-name.txt").write_text("osmo-shared\n",encoding="utf-8")
            with patch.dict("os.environ",{"CHANDRADEV_SHARED_STATE":str(shared)}):
                v=ChandradevOsmoCameraAdapter(
                    Path(td)/"runtime",
                    mediamtx_exe=Path(td)/"mediamtx.exe",
                )
            self.assertEqual(v.stream_name,"osmo-shared")
            self.assertEqual(v.urls("10.0.0.2")["mimo_push_url"],"rtmp://10.0.0.2:1935/osmo-shared")

    def test_screen_lock_can_be_cleared(self):
        with tempfile.TemporaryDirectory() as td:
            shared=Path(td)/"shared"
            with patch.dict("os.environ",{"CHANDRADEV_SHARED_STATE":str(shared)}):
                v=self.runtime(td)
                v._state["screen_lock"]={"normalized_quad":[[0,0],[1,0],[1,1],[0,1]]}
                v._save(v._state)
                out=v.clear_screen_lock()
            self.assertFalse(out["locked"])
            self.assertIsNone(out["screen_lock"])
            self.assertNotIn("screen_lock",v._state)

    @unittest.skipUnless(importlib.util.find_spec("cv2"),"OpenCV is optional in CI")
    def test_screen_detector_warp_and_enhancement_on_synthetic_monitor(self):
        import cv2
        import numpy as np
        frame=np.zeros((720,1280,3),dtype=np.uint8)
        quad=np.array([[150,100],[1130,130],[1080,620],[190,590]],dtype=np.int32)
        cv2.fillConvexPoly(frame,quad,(25,25,25))
        cv2.polylines(frame,[quad],True,(240,240,240),8)
        for y in range(190,500,55):
            cv2.line(frame,(280,y),(930,y),(180,180,180),5)
        detected=ChandradevOsmoCameraAdapter._detect_screen_quad(frame)
        self.assertIsNotNone(detected)
        self.assertGreater(detected["area_ratio"],0.25)
        warped=ChandradevOsmoCameraAdapter._warp_screen(frame,detected["quad"])
        self.assertGreater(warped.shape[1],warped.shape[0])
        enhanced=ChandradevOsmoCameraAdapter._enhance_screen(warped,target_width=1920)
        self.assertGreaterEqual(enhanced.shape[1],1920)
        self.assertGreaterEqual(ChandradevOsmoCameraAdapter._screen_sharpness(enhanced),0.0)

    def test_server_start_fails_closed_without_mediamtx(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                self.runtime(td).start_server()

    def test_analyze_frame_records_directly_to_chandradev(self):
        with tempfile.TemporaryDirectory() as td:
            qc=ChandradevQC(Path(td)/"qc")
            v=self.runtime(td,chandradev=qc,vision=FakeVision())
            frame_path=Path(td)/"frame.jpg"
            frame_path.write_bytes(b"fake-jpeg")
            with patch.object(v,"capture_frame",return_value={
                "path":str(frame_path),"bytes":9,"content_type":"image/jpeg",
                "captured_at":1.0,"source":"rtmp://127.0.0.1:1935/osmo-test",
                "width":1280,"height":720,
            }):
                out=v.analyze_frame()
            self.assertTrue(out["vision"]["local"])
            self.assertEqual(out["vision"]["vision_mode"],"fast")
            self.assertEqual(out["chandradev_observation"]["agent"],"CHANDRADEV")
            self.assertTrue(out["chandradev_observation"]["local_only"])
            self.assertEqual(len(qc.camera_observations()),1)
            self.assertFalse(out["cloud_upload"])

    def test_camera_module_has_no_hawkeye_dependency(self):
        source=Path(__file__).resolve().parents[1]/"krishna_core"/"chandradev_camera.py"
        self.assertNotIn("hawkeye",source.read_text(encoding="utf-8").lower())


if __name__=="__main__":
    unittest.main()
