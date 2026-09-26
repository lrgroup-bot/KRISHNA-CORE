import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class FakeHawkeye:
    def __init__(self):
        self.rows=[]

    def start_live_session(self,**kwargs):
        return {"session_id":"session-1",**kwargs}

    def record_live_analysis(self,session_id,analysis,**kwargs):
        row={"session_id":session_id,"analysis":analysis,**kwargs}
        self.rows.append(row)
        return row


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
        self.assertEqual(p["connectivity"]["wifi"],"802.11a/b/g/n/ac")
        self.assertEqual(p["connectivity"]["bluetooth"],"BLE 4.2")
        self.assertEqual(p["audio"]["built_in_microphones"],2)
        self.assertEqual(p["field_hardware"]["waterproof_without_case_m"],11)
        self.assertEqual(p["field_hardware"]["tested_drop_m"],1.5)

    def test_exact_mimo_and_local_urls(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            urls=v.urls("192.168.0.50")
            self.assertEqual(urls["mimo_push_url"],"rtmp://192.168.0.50:1935/osmo-test")
            self.assertEqual(urls["local_rtmp_url"],"rtmp://127.0.0.1:1935/osmo-test")
            self.assertEqual(urls["local_hls_url"],"http://127.0.0.1:8888/osmo-test/index.m3u8")
            self.assertEqual(urls["local_webrtc_url"],"http://127.0.0.1:8889/osmo-test")

    def test_mediamtx_config_exposes_only_rtmp_to_lan(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            cfg=v.mediamtx_config()
            self.assertIn("rtmpAddress: :1935",cfg)
            self.assertIn("hlsAddress: 127.0.0.1:8888",cfg)
            self.assertIn("webrtcAddress: 127.0.0.1:8889",cfg)
            self.assertIn("rtsp: false",cfg)
            self.assertIn("srt: false",cfg)
            self.assertIn("overridePublisher: false",cfg)
            out=v.ensure_config()
            self.assertTrue(Path(out["config_path"]).is_file())
            self.assertIn("Private profile",out["security"]["recommended_firewall"])

    def test_connection_guide_matches_original_osmo_limit(self):
        with tempfile.TemporaryDirectory() as td:
            guide=self.runtime(td).connection_guide("10.0.0.5")
            self.assertEqual(guide["mimo_push_url"],"rtmp://10.0.0.5:1935/osmo-test")
            self.assertEqual(guide["recommended_original_osmo_settings"]["resolution"],"720p")
            self.assertEqual(guide["recommended_original_osmo_settings"]["fps"],30)
            self.assertEqual(guide["recommended_original_osmo_settings"]["bitrate_mbps"],2)
            self.assertIn("does not expose USB UVC",guide["note"])

    def test_status_is_adapter_not_second_chandradev_agent(self):
        with tempfile.TemporaryDirectory() as td:
            status=self.runtime(td).status()
            self.assertEqual(status["component"],"CHANDRADEV OSMO CAMERA ADAPTER")
            self.assertIn("existing CHANDRADEV",status["role"])
            self.assertFalse(status["mediamtx"]["installed"])
            self.assertFalse(status["usb_live_video"])
            self.assertFalse(status["cloud_required"])
            self.assertFalse(status["paid_service_required"])

    def test_server_start_fails_closed_without_mediamtx(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                self.runtime(td).start_server()

    def test_analyze_frame_uses_local_fast_vision_and_hawkeye(self):
        with tempfile.TemporaryDirectory() as td:
            hawkeye=FakeHawkeye()
            v=self.runtime(td,hawkeye=hawkeye,vision=FakeVision())
            frame_path=Path(td)/"frame.jpg"
            frame_path.write_bytes(b"fake-jpeg")
            with patch.object(v,"capture_frame",return_value={
                "path":str(frame_path),"bytes":9,"content_type":"image/jpeg",
                "captured_at":1.0,"source":"rtmp://127.0.0.1:1935/osmo-test",
                "width":1280,"height":720,
            }):
                out=v.analyze_frame(session_id="session-1")
            self.assertTrue(out["vision"]["local"])
            self.assertEqual(out["vision"]["vision_mode"],"fast")
            self.assertEqual(out["hawkeye"]["session_id"],"session-1")
            self.assertFalse(out["cloud_upload"])
            self.assertEqual(len(hawkeye.rows),1)

    def test_can_start_hawkeye_session(self):
        with tempfile.TemporaryDirectory() as td:
            row=self.runtime(td,hawkeye=FakeHawkeye()).start_hawkeye_session(
                project="KRISHNA",scene_hint="workshop"
            )
            self.assertEqual(row["session_id"],"session-1")
            self.assertEqual(row["scene_hint"],"workshop")


if __name__=="__main__":
    unittest.main()
