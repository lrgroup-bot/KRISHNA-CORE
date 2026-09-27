from __future__ import annotations

from pathlib import Path
import json
import math
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
    "field_hardware": {
        "waterproof_without_case_m": 11,
        "waterproof_with_case_m": 60,
        "tested_drop_m": 1.5,
        "minimum_tested_temperature_c": -10,
        "front_screen_inches": 1.4,
        "rear_touchscreen_inches": 2.25,
    },
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


ZEB_PURE_PLUS_PROFILE = {
    "model": "ZEBRONICS ZEB-Pure Plus",
    "role": "planned dedicated CHANDRADEV monitor-reading webcam",
    "deployment_state": "planned_not_connected",
    "live_transport": "direct USB UVC webcam",
    "target_mode": {
        "resolution": "3840x2160",
        "fps": 30,
        "priority": "screen text detail over high frame rate",
    },
    "camera": {
        "autofocus": True,
        "built_in_microphone": True,
        "usb": True,
        "tripod_support": True,
    },
    "mounting": {
        "budget_mount_target_inr": 500,
        "expensive_arm_required": False,
        "manual_alignment_expected": True,
        "camera_should_face_back_toward_monitor": True,
        "preferred_reach_cm": [30, 60],
        "stability_strategy": "software verifies alignment; owner manually repositions only when required",
    },
    "activation_rule": (
        "Keep DJI Osmo RTMP as the active validation source until the physical USB webcam is installed, "
        "detected and deliberately selected on the KRISHNA PC."
    ),
}

CHANDRADEV_CAMERA_SELECTION = {
    "active_validation_source": "dji_osmo_action_rtmp",
    "active_validation_model": "DJI Osmo Action (original)",
    "future_primary_screen_source": "zeb_pure_plus_usb_uvc",
    "future_primary_screen_model": "ZEBRONICS ZEB-Pure Plus",
    "automatic_source_switching": False,
    "reason": "Do not pretend the future USB webcam exists before physical installation and validation.",
}


class ChandradevOsmoCameraAdapter:
    VERSION = "chandradev-osmo-rtmp-v1"

    def __init__(
        self,
        state_dir: str | Path,
        *,
        chandradev=None,
        vision=None,
        mediamtx_exe: str | Path | None = None,
        stream_name: str | None = None,
    ):
        self.root=Path(state_dir).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.frames=self.root/"frames"
        self.frames.mkdir(parents=True,exist_ok=True)
        self.screens=self.root/"screens"
        self.screens.mkdir(parents=True,exist_ok=True)
        self.state_file=self.root/"stream-state.json"
        shared_override=str(os.getenv("CHANDRADEV_SHARED_STATE") or "").strip()
        shared_root=Path(shared_override).resolve() if shared_override else self.root
        shared_root.mkdir(parents=True,exist_ok=True)
        self.shared_stream_file=shared_root/"stream-name.txt"
        self.config_file=self.root/"mediamtx.yml"
        self.log_file=self.root/"mediamtx.log"
        self.chandradev=chandradev
        self.vision=vision
        self.mediamtx_exe=Path(
            mediamtx_exe
            or os.getenv("CHANDRADEV_MEDIAMTX_EXE")
            or r"E:\Krishna-The GOD\tools\mediamtx\mediamtx.exe"
        )
        self._state=self._load_or_create(stream_name)

    def _load_or_create(self,stream_name=None):
        explicit=str(stream_name or "").strip()
        shared=""
        if self.shared_stream_file.is_file():
            try:
                shared=self.shared_stream_file.read_text(encoding="utf-8").strip()
            except Exception:
                shared=""
        local=None
        if self.state_file.is_file():
            try:
                row=json.loads(self.state_file.read_text(encoding="utf-8"))
                if isinstance(row,dict) and row.get("stream_name"):
                    local=row
            except Exception:
                local=None
        name=explicit or shared or (str(local.get("stream_name") or "").strip() if local else "")
        if not name:
            name="osmo-"+secrets.token_hex(6)
        row=dict(local or {})
        row.update({
            "version":self.VERSION,
            "stream_name":name,
            "server_pid":row.get("server_pid"),
            "created_at":row.get("created_at") or time.time(),
            "updated_at":time.time(),
        })
        self._save(row)
        self._sync_shared_stream_name(name)
        return row

    def _sync_shared_stream_name(self,name=None):
        value=str(name or self._state.get("stream_name") or "").strip() if hasattr(self,"_state") else str(name or "").strip()
        if not value:
            return None
        self.shared_stream_file.parent.mkdir(parents=True,exist_ok=True)
        self.shared_stream_file.write_text(value+"\n",encoding="utf-8")
        return str(self.shared_stream_file)


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

    def probe_usb(self):
        if os.name!="nt":
            return {
                "supported":False,
                "detected":False,
                "reason":"Windows PnP probe is available only on Windows",
                "devices":[],
            }
        command=(
            "$rows=Get-PnpDevice -PresentOnly | "
            "Where-Object { $_.FriendlyName -match 'DJI|OSMO' -or $_.InstanceId -match 'VEN_DJI|PROD_OSMO' } | "
            "Select-Object Status,Class,FriendlyName,InstanceId; "
            "$rows | ConvertTo-Json -Compress"
        )
        try:
            proc=subprocess.run(
                ["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                capture_output=True,text=True,timeout=8,check=False,
            )
            raw=str(proc.stdout or "").strip()
            if proc.returncode!=0:
                return {
                    "supported":True,"detected":False,
                    "error":str(proc.stderr or "").strip()[:1000],
                    "devices":[],
                }
            if not raw:
                return {"supported":True,"detected":False,"devices":[]}
            parsed=json.loads(raw)
            rows=parsed if isinstance(parsed,list) else [parsed]
            devices=[]
            for row in rows:
                if not isinstance(row,dict):continue
                instance=str(row.get("InstanceId") or "")
                klass=str(row.get("Class") or "")
                storage=instance.upper().startswith("USBSTOR\\") or klass.lower()=="diskdrive"
                devices.append({
                    "status":row.get("Status"),
                    "class":klass,
                    "friendly_name":row.get("FriendlyName"),
                    "instance_id":instance,
                    "mass_storage":storage,
                    "uvc_live_video":klass.lower()=="camera" and not storage,
                })
            return {
                "supported":True,
                "detected":bool(devices),
                "devices":devices,
                "interpretation":(
                    "OSMO connected as file-transfer/storage; use DJI Mimo RTMP for live CHANDRADEV video"
                    if any(x["mass_storage"] for x in devices)
                    else "No DJI mass-storage interface detected"
                ),
            }
        except Exception as exc:
            return {
                "supported":True,"detected":False,"devices":[],
                "error":f"{type(exc).__name__}: {exc}",
            }

    def status(self):
        pid=self._state.get("server_pid")
        try:
            import cv2  # noqa: F401
            opencv=True
        except Exception:
            opencv=False
        return {
            "component":"CHANDRADEV OSMO CAMERA ADAPTER",
            "version":self.VERSION,
            "role":"standalone PC camera transport/input adapter for the existing CHANDRADEV QC peer",
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
            "screen_focus":{
                "mode":"software_auto_focus",
                "optical_focus_control":False,
                "detect_monitor":True,
                "perspective_correction":True,
                "sharpest_frame_selection":True,
                "screen_lock":self._state.get("screen_lock"),
                "alignment_handoff":self._state.get("alignment_handoff"),
                "enhancement":["crop","perspective_warp","upscale","local_contrast","unsharp_mask"],
            },
            "camera_selection":dict(CHANDRADEV_CAMERA_SELECTION),
            "future_webcam_profile":dict(ZEB_PURE_PLUS_PROFILE),
            "usb_probe":self.probe_usb(),
            "urls":self.urls(),
            "shared_stream_name_file":str(self.shared_stream_file),
            "cloud_required":False,
            "paid_service_required":False,
            "usb_live_video":False,
            "live_path":"DJI Mimo RTMP -> MediaMTX -> local frame -> local VisionAdapter -> CHANDRADEV",
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
                "For the original Osmo Action select 720p/30fps; use 4 Mbps for maximum supported live quality; fall back to 2 Mbps if the LAN is unstable.",
                "Start livestreaming; Chandradev reads, analyzes and records sampled frames locally on the PC.",
            ],
            "mimo_push_url":urls["mimo_push_url"],
            "local_read_url":urls["local_rtmp_url"],
            "recommended_original_osmo_settings":{
                "resolution":"720p",
                "fps":30,
                "bitrate_mbps":4,
                "fallback":"720p/2 Mbps first; 480p/1 Mbps only when Wi-Fi is unstable",
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

    @staticmethod
    def _order_quad(points):
        import numpy as np
        pts=np.asarray(points,dtype="float32").reshape(4,2)
        ordered=np.zeros((4,2),dtype="float32")
        sums=pts.sum(axis=1)
        diffs=np.diff(pts,axis=1).reshape(-1)
        ordered[0]=pts[sums.argmin()]   # top-left
        ordered[2]=pts[sums.argmax()]   # bottom-right
        ordered[1]=pts[diffs.argmin()]  # top-right
        ordered[3]=pts[diffs.argmax()]  # bottom-left
        return ordered

    @staticmethod
    def _quad_geometry(quad):
        import numpy as np
        q=ChandradevOsmoCameraAdapter._order_quad(quad)
        tl,tr,br,bl=q
        width=max(float(np.linalg.norm(br-bl)),float(np.linalg.norm(tr-tl)))
        height=max(float(np.linalg.norm(tr-br)),float(np.linalg.norm(tl-bl)))
        return q,max(1.0,width),max(1.0,height)

    @staticmethod
    def _screen_sharpness(image):
        import cv2
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if len(image.shape)==3 else image
        return float(cv2.Laplacian(gray,cv2.CV_64F).var())

    @staticmethod
    def _detect_screen_quad(frame):
        import cv2
        import numpy as np
        h,w=frame.shape[:2]
        frame_area=float(max(1,h*w))
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        gray=cv2.GaussianBlur(gray,(5,5),0)
        edges=cv2.Canny(gray,45,140)
        kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
        edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,kernel,iterations=2)
        contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        candidates=[]
        center=np.array([w/2.0,h/2.0],dtype="float32")
        for contour in sorted(contours,key=cv2.contourArea,reverse=True)[:80]:
            area=float(cv2.contourArea(contour))
            area_ratio=area/frame_area
            if area_ratio<0.08 or area_ratio>0.98:
                continue
            peri=cv2.arcLength(contour,True)
            approx=cv2.approxPolyDP(contour,0.02*peri,True)
            if len(approx)!=4 or not cv2.isContourConvex(approx):
                continue
            quad=ChandradevOsmoCameraAdapter._order_quad(approx.reshape(4,2))
            _,qw,qh=ChandradevOsmoCameraAdapter._quad_geometry(quad)
            aspect=qw/qh
            if aspect<1.05 or aspect>3.8:
                continue
            rect=cv2.minAreaRect(contour)
            box_area=max(1.0,float(rect[1][0]*rect[1][1]))
            rectangularity=min(1.0,area/box_area) if box_area>0 else 0.0
            qcenter=quad.mean(axis=0)
            center_distance=float(np.linalg.norm(qcenter-center))/max(1.0,float(np.linalg.norm(center)))
            center_score=max(0.0,1.0-center_distance)
            aspect_score=max(0.0,1.0-abs(aspect-(16.0/9.0))/2.2)
            score=(area_ratio*4.0)+(rectangularity*1.8)+(center_score*0.8)+(aspect_score*0.6)
            candidates.append({
                "quad":quad,
                "score":float(score),
                "area_ratio":area_ratio,
                "aspect_ratio":aspect,
                "rectangularity":rectangularity,
            })
        if not candidates:
            return None
        candidates.sort(key=lambda x:x["score"],reverse=True)
        return candidates[0]

    @staticmethod
    def _warp_screen(frame,quad):
        import cv2
        import numpy as np
        q,width,height=ChandradevOsmoCameraAdapter._quad_geometry(quad)
        max_w=max(320,int(round(width)))
        max_h=max(180,int(round(height)))
        destination=np.array(
            [[0,0],[max_w-1,0],[max_w-1,max_h-1],[0,max_h-1]],
            dtype="float32",
        )
        matrix=cv2.getPerspectiveTransform(q,destination)
        return cv2.warpPerspective(frame,matrix,(max_w,max_h),flags=cv2.INTER_CUBIC)

    @staticmethod
    def _enhance_screen(image,target_width=1920):
        import cv2
        h,w=image.shape[:2]
        width=max(int(target_width or 1920),w)
        scale=width/float(max(1,w))
        resized=cv2.resize(
            image,
            (width,max(1,int(round(h*scale)))),
            interpolation=cv2.INTER_CUBIC if scale>1 else cv2.INTER_AREA,
        )
        lab=cv2.cvtColor(resized,cv2.COLOR_BGR2LAB)
        l,a,b=cv2.split(lab)
        clahe=cv2.createCLAHE(clipLimit=1.7,tileGridSize=(8,8))
        l=clahe.apply(l)
        enhanced=cv2.cvtColor(cv2.merge((l,a,b)),cv2.COLOR_LAB2BGR)
        blurred=cv2.GaussianBlur(enhanced,(0,0),1.0)
        return cv2.addWeighted(enhanced,1.45,blurred,-0.45,0)

    @staticmethod
    def _normalize_quad(quad,width,height):
        q=ChandradevOsmoCameraAdapter._order_quad(quad)
        return [
            [round(float(x)/max(1.0,float(width)),6),round(float(y)/max(1.0,float(height)),6)]
            for x,y in q
        ]

    @staticmethod
    def _denormalize_quad(points,width,height):
        import numpy as np
        return np.asarray(
            [[float(x)*width,float(y)*height] for x,y in points],
            dtype="float32",
        )

    def clear_screen_lock(self):
        self._state.pop("screen_lock",None)
        self._state.pop("alignment_handoff",None)
        self._save(self._state)
        return {"locked":False,"screen_lock":None,"alignment_handoff":None}

    @staticmethod
    def _normalized_quad_motion(samples):
        rows=[x for x in (samples or []) if isinstance(x,list) and len(x)==4]
        if len(rows)<2:
            return {
                "status":"unverified",
                "stable":None,
                "sample_count":len(rows),
                "median_max_corner_shift":None,
                "max_corner_shift":None,
            }
        shifts=[]
        for previous,current in zip(rows,rows[1:]):
            corner_shifts=[]
            for p,c in zip(previous,current):
                if not (isinstance(p,list) and isinstance(c,list) and len(p)==2 and len(c)==2):
                    continue
                corner_shifts.append(math.hypot(float(c[0])-float(p[0]),float(c[1])-float(p[1])))
            if corner_shifts:
                shifts.append(max(corner_shifts))
        if not shifts:
            return {
                "status":"unverified",
                "stable":None,
                "sample_count":len(rows),
                "median_max_corner_shift":None,
                "max_corner_shift":None,
            }
        ordered=sorted(shifts)
        middle=len(ordered)//2
        median=ordered[middle] if len(ordered)%2 else (ordered[middle-1]+ordered[middle])/2.0
        maximum=max(ordered)
        stable=median<=0.018 and maximum<=0.060
        return {
            "status":"stable" if stable else "unstable",
            "stable":stable,
            "sample_count":len(rows),
            "median_max_corner_shift":round(float(median),6),
            "max_corner_shift":round(float(maximum),6),
            "thresholds":{"median":0.018,"maximum":0.060},
        }

    def _alignment_handoff(self,reason,*,details=None):
        reason=str(reason or "camera_alignment_required")
        handoff={
            "request_id":"CHANDRA-ALIGN-"+secrets.token_hex(6),
            "requested_at":time.time(),
            "agent":"CHANDRADEV",
            "route_through":"KRISHNA",
            "owner_handoff_required":True,
            "reason":reason,
            "instruction":(
                "Please stabilize or reposition the CHANDRADEV camera so the complete monitor is visible, "
                "all four screen edges are inside the frame and the camera is not shaking. "
                "After adjustment CHANDRADEV will re-detect, refocus and lock the monitor automatically."
            ),
            "details":dict(details or {}),
        }
        self._state["alignment_handoff"]=handoff
        self._state.pop("screen_lock",None)
        self._save(self._state)
        memory=getattr(self.chandradev,"memory",None) if self.chandradev is not None else None
        if memory is not None:
            try:
                memory.audit(
                    "chandradev_camera_alignment",
                    "owner_handoff_required",
                    f"{handoff['request_id']}:{reason}",
                )
            except Exception:
                pass
        return handoff

    def alignment_status(self):
        return {
            "agent":"CHANDRADEV",
            "active_source":CHANDRADEV_CAMERA_SELECTION["active_validation_source"],
            "screen_lock":self._state.get("screen_lock"),
            "alignment_handoff":self._state.get("alignment_handoff"),
            "owner_handoff_required":bool(self._state.get("alignment_handoff")),
        }

    def future_webcam_profile(self):
        return {
            "profile":dict(ZEB_PURE_PLUS_PROFILE),
            "selection":dict(CHANDRADEV_CAMERA_SELECTION),
            "active_now":False,
            "validation_now":"DJI Osmo Action via DJI Mimo RTMP only",
        }

    def focus_screen(self,*,burst_frames=12,target_width=1920,timeout_seconds=8):
        """Software auto-focus for a monitor/screen in the Osmo RTMP feed.

        The original action camera does not expose motorized focus control here.
        We instead detect the monitor, perspective-correct it, choose the
        sharpest screen image from a short burst, upscale and enhance it.
        """
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV screen focus is not installed; run scripts/INSTALL_CHANDRADEV_VISION.ps1"
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

        count=max(3,min(int(burst_frames or 12),45))
        best=None
        locked=self._state.get("screen_lock")
        fresh_quad_samples=[]
        for index in range(count):
            ok,frame=cap.read()
            if not ok or frame is None:
                continue
            h,w=frame.shape[:2]
            detected=self._detect_screen_quad(frame)
            used_lock=False
            if detected is None and isinstance(locked,dict) and len(locked.get("normalized_quad") or [])==4:
                quad=self._denormalize_quad(locked["normalized_quad"],w,h)
                detected={
                    "quad":quad,
                    "score":float(locked.get("detection_score") or 0.5)*0.82,
                    "area_ratio":float(locked.get("area_ratio") or 0),
                    "aspect_ratio":float(locked.get("aspect_ratio") or 0),
                    "rectangularity":float(locked.get("rectangularity") or 0),
                }
                used_lock=True
            if detected is None:
                continue
            if not used_lock:
                fresh_quad_samples.append(self._normalize_quad(detected["quad"],w,h))
            warped=self._warp_screen(frame,detected["quad"])
            sharpness=self._screen_sharpness(warped)
            combined=(float(detected["score"])*100.0)+min(sharpness,2500.0)/12.0
            row={
                "frame":frame,
                "warped":warped,
                "quad":detected["quad"],
                "detection_score":float(detected["score"]),
                "area_ratio":float(detected["area_ratio"]),
                "aspect_ratio":float(detected["aspect_ratio"]),
                "rectangularity":float(detected["rectangularity"]),
                "sharpness":sharpness,
                "combined_score":combined,
                "used_previous_lock":used_lock,
                "source_width":w,
                "source_height":h,
                "burst_index":index,
            }
            if best is None or row["combined_score"]>best["combined_score"]:
                best=row
        cap.release()

        if best is None:
            handoff=self._alignment_handoff(
                "screen_not_detected",
                details={
                    "source":source,
                    "active_camera":"DJI Osmo Action (original)",
                    "requested_burst_frames":count,
                },
            )
            return {
                "found":False,
                "mode":"software_auto_focus",
                "reason":"screen_not_detected",
                "owner_handoff_required":True,
                "alignment_handoff":handoff,
                "guidance":[
                    "Point the camera toward the monitor so the complete display is inside the frame.",
                    "Avoid severe glare/reflections and keep all four screen edges visible.",
                    "Stabilize the inexpensive mount by hand if required; no expensive arm is assumed.",
                ],
                "source":source,
            }

        stability=self._normalized_quad_motion(fresh_quad_samples)
        if stability.get("stable") is False:
            handoff=self._alignment_handoff(
                "camera_or_mount_unstable",
                details={
                    "source":source,
                    "active_camera":"DJI Osmo Action (original)",
                    "stability":stability,
                    "screen_area_ratio":round(best["area_ratio"],4),
                },
            )
            return {
                "found":False,
                "mode":"software_auto_focus",
                "reason":"camera_or_mount_unstable",
                "owner_handoff_required":True,
                "alignment_handoff":handoff,
                "stability":stability,
                "source":source,
            }

        enhanced=self._enhance_screen(best["warped"],target_width=target_width)
        stamp=time.strftime("%Y%m%d-%H%M%S")+"-"+f"{int(time.time()*1000)%1000:03d}"
        raw_path=self.screens/f"screen-{stamp}-raw.jpg"
        focused_path=self.screens/f"screen-{stamp}-focused.jpg"
        cv2.imwrite(str(raw_path),best["warped"],[int(cv2.IMWRITE_JPEG_QUALITY),95])
        cv2.imwrite(str(focused_path),enhanced,[int(cv2.IMWRITE_JPEG_QUALITY),96])

        normalized=self._normalize_quad(
            best["quad"],best["source_width"],best["source_height"]
        )
        lock={
            "normalized_quad":normalized,
            "detection_score":round(best["detection_score"],6),
            "area_ratio":round(best["area_ratio"],6),
            "aspect_ratio":round(best["aspect_ratio"],6),
            "rectangularity":round(best["rectangularity"],6),
            "sharpness":round(best["sharpness"],3),
            "source_width":best["source_width"],
            "source_height":best["source_height"],
            "locked_at":time.time(),
        }
        self._state["screen_lock"]=lock
        self._state.pop("alignment_handoff",None)
        self._state["last_alignment_stability"]=stability
        self._save(self._state)

        eh,ew=enhanced.shape[:2]
        return {
            "found":True,
            "mode":"software_auto_focus",
            "optical_focus_changed":False,
            "screen_locked":True,
            "used_previous_lock":bool(best["used_previous_lock"]),
            "burst_frames_requested":count,
            "selected_burst_index":best["burst_index"],
            "detection_score":round(best["detection_score"],4),
            "sharpness":round(best["sharpness"],2),
            "screen_area_ratio":round(best["area_ratio"],4),
            "screen_aspect_ratio":round(best["aspect_ratio"],4),
            "normalized_quad":normalized,
            "raw_screen_path":str(raw_path),
            "focused_screen_path":str(focused_path),
            "focused_width":int(ew),
            "focused_height":int(eh),
            "source":source,
            "owner_handoff_required":False,
            "alignment_handoff":None,
            "stability":stability,
            "enhancement":[
                "screen detection","perspective correction","sharpest-frame selection",
                "bicubic upscale","local contrast enhancement","unsharp mask",
            ],
        }

    def analyze_screen(self,*,prompt="",burst_frames=12,target_width=1920):
        if self.vision is None:
            raise RuntimeError("Chandradev VisionAdapter is not bound")
        focus=self.focus_screen(
            burst_frames=burst_frames,
            target_width=target_width,
        )
        if not focus.get("found"):
            return {
                "component":"CHANDRADEV SCREEN FOCUS",
                "focus":focus,
                "vision":None,
                "chandradev_observation":None,
                "cloud_upload":False,
            }
        path=Path(focus["focused_screen_path"])
        question=str(prompt or (
            "Read and understand this computer screen. Prioritize visible text, buttons, menus, "
            "dialogs, code, terminal output, warnings, status indicators and UI problems. "
            "Do not guess text that is not legible; explicitly identify uncertain areas."
        )).strip()
        result=self.vision.analyze_bytes(
            path.read_bytes(),"image/jpeg",question,mode="detailed"
        )
        observation=None
        if self.chandradev is not None:
            observation=self.chandradev.record_camera_observation(
                analysis=str(result.get("analysis") or ""),
                frame_meta={
                    "path":focus["focused_screen_path"],
                    "width":focus["focused_width"],
                    "height":focus["focused_height"],
                    "content_type":"image/jpeg",
                    "captured_at":time.time(),
                },
                source="DJI Osmo Action screen focus via DJI Mimo RTMP",
                prompt=question,
            )
        return {
            "component":"CHANDRADEV SCREEN FOCUS",
            "focus":focus,
            "vision":result,
            "chandradev_observation":observation,
            "cloud_upload":False,
        }

    def analyze_frame(self,*,prompt=""):
        if self.vision is None:
            raise RuntimeError("Chandradev VisionAdapter is not bound")
        frame=self.capture_frame()
        data=Path(frame["path"]).read_bytes()
        question=str(prompt or (
            "Observe this live Chandradev camera frame. Describe only visible evidence, important objects, "
            "text, people, vehicles, equipment and changes that are actually supported. State uncertainty."
        )).strip()
        result=self.vision.analyze_bytes(data,"image/jpeg",question,mode="fast")
        observation=None
        if self.chandradev is not None:
            observation=self.chandradev.record_camera_observation(
                analysis=str(result.get("analysis") or ""),
                frame_meta=frame,
                source="DJI Osmo Action (original) via DJI Mimo RTMP",
                prompt=question,
            )
        return {
            "component":"CHANDRADEV OSMO CAMERA ADAPTER",
            "frame":frame,
            "vision":result,
            "chandradev_observation":observation,
            "raw_frame_retention":"local PC only",
            "cloud_upload":False,
        }
