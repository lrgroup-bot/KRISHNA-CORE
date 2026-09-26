import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.chandradev import ChandradevQC
from krishna_core.chandradev_camera import (
    ChandradevOsmoCameraAdapter,
    OSMO_ACTION_ORIGINAL_PROFILE,
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
