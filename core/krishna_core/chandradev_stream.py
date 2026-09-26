from __future__ import annotations

from pathlib import Path
import json
import os
import secrets
import socket
import subprocess
import time


OSMO_ACTION_ORIGINAL_PROFILE = {
    "model": "DJI Osmo Action (original)",
    "usb_mode": "mass_storage_only_on_this_model",
    "uvc_webcam": False,
    "hdmi_output": False,
    "live_transport": "DJI Mimo -> RTMP",
    "livestream": {
        "resolutions": ["480p", "720p"],
        "fps": 30,
        "bitrates_mbps": {"480p": [1, 2], "720p": [2, 4]},
    },
    "camera": {
        "sensor": '1/2.3-inch CMOS',
        "effective_megapixels": 12,
        "fov_degrees": 145,
        "aperture": "f/2.8",
        "recording": ["4K60", "1080p240"],
        "max_video_bitrate_mbps": 100,
        "video_codec": "H.264",
    },
    "connectivity": {
        "wifi": "802.11a/b/g/n/ac",
        "wifi_bands_ghz": ["2.4", "5.8"],
        "bluetooth": "BLE 4.2",
        "usb_c": True,
    },
    "audio": {
        "built_in_microphones": 2,
        "recording": "48 kHz AAC",
        "external_microphone": "USB-C via compatible 3.5 mm adapter",
    },
    "storage": {"microSD_max_gb": 256},
    "battery": {
        "capacity_mah": 1300,
        "energy_wh": 5.005,
        "reference_runtime": {
            "1080p30_rocksteady_off_minutes": 135,
            "4k60_rocksteady_on_minutes": 63,
        },
    },
    "chandradev_value": [
        "wireless RTMP live vision source",
        "parallel high-quality microSD evidence recorder",
        "wide 145-degree field of view",
        "built-in stereo-environment audio source",
        "optional external microphone input",
        "rugged mobile mounting platform",
    ],
    "limitations": [
        "original Osmo Action is not on DJI's current UVC webcam support list",
        "USB connection presents storage/file-transfer rather than live video",
        "Osmo series does not provide HDMI output or USB-C-to-HDMI output",
        "RTMP live feed is limited to 480p/720p at 30 fps on the original Osmo Action",
        "DJI Mimo is required to originate the supported RTMP livestream",
    ],
}


class ChandradevStreamRuntime:
    VERSION = "chandradev-osmo-rtmp-v1"

    def __init__(
        self,
        state_dir: str | Path,
        *,
        hawkeye=None,
        vision=None,
        mediamtx_exe: str | Path | None = None,
        stream_name: str | None = None,
    ):
        self.root=Path(state_dir).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.frames=self.root/"frames"
        self.frames.mkdir(parents=True,exist_ok=True)
        self.state_file=self.root/"stream-state.json"
        self.config_file=self.root/"mediamtx.yml"
        self.log_file=self.root/"mediamtx.log"
        self.hawkeye=hawkeye
        self.vision=vision
        self.mediamtx_exe=Path(
            mediamtx_exe
            or os.getenv("CHANDRADEV_MEDIAMTX_EXE")
            or r"E:\Krishna-The GOD\tools\mediamtx\mediamtx.exe"
        )
        self._state=self._load_or_create(stream_name)

    def _load_or_create(self,stream_name=None):
        if self.state_file.is_file():
            try:
                row=json.loads(self.state_file.read_text(encoding="utf-8"))
                if isinstance(row,dict) and row.get("stream_name"):
                    return row
            except Exception:
                pass
        name=str(stream_name or "").strip()
        if not name:
            name="osmo-"+secrets.token_hex(6)
        row={
            "version":self.VERSION,
            "stream_name":name,
            "server_pid":None,
            "created_at":time.time(),
            "updated_at":time.time(),
        }
        self._save(row)
        return row

    def _save(self,row):
        row=dict(row)
        row["version"]=self.VERSION
        row["updated_at"]=time.time()
        tmp=self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(row,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(self.state_file)
        self._state=row

    @staticmethod
    def lan_ipv4():
        # Determine the preferred LAN route without sending application data.
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            sock.connect(("1.1.1.1",80))
            ip=sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            pass
        finally:
            sock.close()
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                if ip and not ip.startswith("127.") and ":" not in ip:
                    return ip
        except OSError:
            pass
        return "127.0.0.1"

    @property
    def stream_name(self):
        return str(self._state["stream_name"])

    def urls(self,lan_ip=None):
        lan=str(lan_ip or self.lan_ipv4())
        path=self.stream_name
        return {
            "mimo_push_url":f"rtmp://{lan}:1935/{path}",
            "local_rtmp_url":f"rtmp://127.0.0.1:1935/{path}",
            "local_hls_url":f"http://127.0.0.1:8888/{path}/index.m3u8",
            "local_webrtc_url":f"http://127.0.0.1:8889/{path}",
            "lan_ip":lan,
            "stream_name":path,
        }

    def mediamtx_config(self):
        path=self.stream_name
        return (
            "logLevel: info\n"
            "rtsp: false\n"
            "rtmp: true\n"
            "rtmpEncryption: \"no\"\n"
            "rtmpAddress: :1935\n"
            "hls: true\n"
            "hlsAddress: 127.0.0.1:8888\n"
            "webrtc: true\n"
            "webrtcAddress: 127.0.0.1:8889\n"
            "srt: false\n"
            "api: false\n"
            "metrics: false\n"
            "pprof: false\n"
            "paths:\n"
            f"  {path}:\n"
            "    source: publisher\n"
            "    overridePublisher: false\n"
            "    maxReaders: 4\n"
        )

    def ensure_config(self):
        text=self.mediamtx_config()
        self.config_file.write_text(text,encoding="utf-8")
        return {
            "config_path":str(self.config_file),
            "stream_name":self.stream_name,
            "security":{
                "rtmp_listener":"LAN-accessible TCP 1935",
                "hls_listener":"localhost only",
                "webrtc_listener":"localhost only",
                "single_expected_publish_path":True,
                "publisher_override":False,
                "recommended_firewall":"Windows Private profile + LocalSubnet only",
            },
        }

    @staticmethod
    def _pid_alive(pid):
        try:
            pid=int(pid or 0)
        except (TypeError,ValueError):
            return False
        if pid<=0:return False
        try:
            os.kill(pid,0)
            return True
        except (OSError,PermissionError):
            return False

    def status(self):
        pid=self._state.get("server_pid")
        try:
            import cv2  # noqa: F401
            opencv=True
        except Exception:
            opencv=False
        return {
            "agent":"CHANDRADEV",
            "version":self.VERSION,
            "role":"live camera ingest and visual handoff to HAWKEYE",
            "hardware_profile":OSMO_ACTION_ORIGINAL_PROFILE,
            "mediamtx":{
                "exe":str(self.mediamtx_exe),
                "installed":self.mediamtx_exe.is_file(),
                "config":str(self.config_file),
                "config_ready":self.config_file.is_file(),
                "running":self._pid_alive(pid),
                "pid":pid if self._pid_alive(pid) else None,
            },
            "opencv_frame_reader":opencv,
            "urls":self.urls(),
            "cloud_required":False,
            "paid_service_required":False,
            "usb_live_video":False,
            "live_path":"DJI Mimo RTMP -> MediaMTX -> local frame -> local VisionAdapter -> HAWKEYE",
        }

    def connection_guide(self,lan_ip=None):
        urls=self.urls(lan_ip)
        return {
            "camera":"DJI Osmo Action (original)",
            "mode":"Wi-Fi livestream through DJI Mimo",
            "steps":[
                "Disconnect the USB file-transfer session from the PC for live use.",
                "Power on Osmo Action and connect it to DJI Mimo on the phone.",
                "Put the phone and KRISHNA PC on the same trusted Wi-Fi/LAN.",
                "Start the local Chandradev MediaMTX receiver on the PC.",
                "In DJI Mimo open Live Stream and choose RTMP.",
                "Enter the exact Mimo push URL below.",
                "For the original Osmo Action select 720p/30fps; use 2 Mbps first, then 4 Mbps if the LAN is stable.",
                "Start livestreaming; Chandradev reads the local stream and passes sampled frames to HAWKEYE.",
            ],
            "mimo_push_url":urls["mimo_push_url"],
            "local_read_url":urls["local_rtmp_url"],
            "recommended_original_osmo_settings":{
                "resolution":"720p",
                "fps":30,
                "bitrate_mbps":2,
                "fallback":"480p/1 Mbps when Wi-Fi is unstable",
            },
            "note":"The original Osmo Action does not expose USB UVC live video; USB remains useful for file transfer and charging.",
        }

    def start_server(self):
        if not self.mediamtx_exe.is_file():
            raise FileNotFoundError(
                f"MediaMTX not installed at {self.mediamtx_exe}; run scripts/INSTALL_CHANDRADEV_RTMP.ps1"
            )
        if self._pid_alive(self._state.get("server_pid")):
            return self.status()
        self.ensure_config()
        log=self.log_file.open("ab")
        proc=subprocess.Popen(
            [str(self.mediamtx_exe),str(self.config_file)],
            cwd=str(self.mediamtx_exe.parent),
            stdout=log,stderr=subprocess.STDOUT,
            creationflags=(getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0),
        )
        self._state["server_pid"]=proc.pid
        self._state["server_started_at"]=time.time()
        self._save(self._state)
        time.sleep(0.35)
        if proc.poll() is not None:
            self._state["server_pid"]=None
            self._save(self._state)
            raise RuntimeError("MediaMTX exited during startup; inspect "+str(self.log_file))
        return self.status()

    def stop_server(self):
        pid=self._state.get("server_pid")
        if not self._pid_alive(pid):
            self._state["server_pid"]=None
            self._save(self._state)
            return self.status()
        if os.name=="nt":
            subprocess.run(
                ["taskkill","/PID",str(int(pid)),"/T","/F"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,
            )
        else:
            try:os.kill(int(pid),15)
            except OSError:pass
        self._state["server_pid"]=None
        self._state["server_stopped_at"]=time.time()
        self._save(self._state)
        return self.status()

    def capture_frame(self,*,quality=88,timeout_seconds=6):
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV frame reader is not installed; run scripts/INSTALL_CHANDRADEV_VISION.ps1"
            ) from exc
        source=self.urls()["local_rtmp_url"]
        cap=cv2.VideoCapture()
        for prop,value in (
            (getattr(cv2,"CAP_PROP_OPEN_TIMEOUT_MSEC",-1),int(max(1,timeout_seconds)*1000)),
            (getattr(cv2,"CAP_PROP_READ_TIMEOUT_MSEC",-1),int(max(1,timeout_seconds)*1000)),
        ):
            if prop>=0:
                try:cap.set(prop,value)
                except Exception:pass
        if not cap.open(source):
            cap.release()
            raise RuntimeError("Chandradev RTMP stream is not available at "+source)
        ok,frame=cap.read()
        cap.release()
        if not ok or frame is None:
            raise RuntimeError("Chandradev could not read a frame from the Osmo RTMP stream")
        stamp=time.strftime("%Y%m%d-%H%M%S")
        path=self.frames/f"osmo-{stamp}-{int(time.time()*1000)%1000:03d}.jpg"
        ok,encoded=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),max(40,min(int(quality),100))])
        if not ok:
            raise RuntimeError("OpenCV failed to encode Chandradev frame")
        data=encoded.tobytes()
        path.write_bytes(data)
        return {
            "path":str(path),
            "bytes":len(data),
            "content_type":"image/jpeg",
            "captured_at":time.time(),
            "source":source,
            "width":int(frame.shape[1]),
            "height":int(frame.shape[0]),
        }

    def analyze_frame(self,*,prompt="",session_id="",scene_hint="auto"):
        if self.vision is None:
            raise RuntimeError("Chandradev VisionAdapter is not bound")
        frame=self.capture_frame()
        data=Path(frame["path"]).read_bytes()
        question=str(prompt or (
            "Observe this live Chandradev camera frame. Describe only visible evidence, important objects, "
            "text, people/vehicles/equipment and changes that are actually supported. State uncertainty."
        )).strip()
        result=self.vision.analyze_bytes(data,"image/jpeg",question,mode="fast")
        hawkeye_row=None
        if session_id and self.hawkeye is not None:
            hawkeye_row=self.hawkeye.record_live_analysis(
                str(session_id),
                str(result.get("analysis") or ""),
                model=result.get("model"),
                sensor_context={
                    "camera":"DJI Osmo Action (original)",
                    "transport":"DJI Mimo RTMP",
                    "scene_hint":str(scene_hint or "auto"),
                },
                frame_meta={
                    "source":"chandradev-osmo-rtmp",
                    "path":frame["path"],
                    "width":frame["width"],
                    "height":frame["height"],
                    "confidence":0.65,
                },
            )
        return {
            "agent":"CHANDRADEV",
            "frame":frame,
            "vision":result,
            "hawkeye":hawkeye_row,
            "raw_frame_retention":"local PC only",
            "cloud_upload":False,
        }

    def start_hawkeye_session(self,*,project="KRISHNA",purpose="Chandradev live Osmo observation",scene_hint="auto"):
        if self.hawkeye is None:
            raise RuntimeError("HAWKEYE coordinator is not bound")
        return self.hawkeye.start_live_session(
            project=str(project or "KRISHNA"),
            purpose=str(purpose or "Chandradev live Osmo observation"),
            scene_hint=str(scene_hint or "auto"),
        )
