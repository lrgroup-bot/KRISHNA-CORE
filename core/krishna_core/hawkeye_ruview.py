from __future__ import annotations

"""PC-only RuView / Wi-Fi sensing bridge for HAWKEYE.

The bridge deliberately separates *network credentials* from *sensing evidence*:

- Wi-Fi passwords are accepted only by PC/system actions and may be persisted only
  in KRISHNA's Windows-DPAPI SecureSecretVault.
- Mobile callers can observe HAWKEYE results through the existing conversation
  surface, but they cannot submit, retrieve or resolve Wi-Fi credentials.
- Ordinary consumer Wi-Fi adapters expose RSSI only. RSSI can show radio-signal
  changes but cannot honestly reconstruct body pose or provide reliable
  "see-through-wall" perception. Full RuView sensing requires CSI-capable
  hardware (for example an ESP32-S3/C6 node or a supported research NIC) feeding
  a RuView sensing server.
- RuView model outputs such as presence, motion, person count and pose are stored
  as INFERRED HAWKEYE evidence. Raw radio metrics are MEASURED evidence.
- Vital-sign estimates are disabled by default and are never collected merely
  because a RuView endpoint exposes them.
"""

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import time
from xml.sax.saxutils import escape


class HawkeyeRuViewBridge:
    VERSION = "hawkeye-ruview-v1"
    DEFAULT_BASE_URL = "http://127.0.0.1:8080"
    FALLBACK_BASE_URLS = ("http://127.0.0.1:3000",)
    CSI_HINTS = {
        "csi", "wifi_csi", "channel_state_information", "pose_data",
        "edge_vitals", "densepose", "rf_pose",
    }

    def __init__(
        self,
        state_root,
        *,
        secure_vault,
        hawkeye=None,
        field=None,
        base_url=None,
        collect_vitals=False,
    ):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.samples_file = self.root / "rf-samples.jsonl"
        self.secure_vault = secure_vault
        self.hawkeye = hawkeye
        self.field = field
        self.base_url = str(
            base_url or os.getenv("KRISHNA_RUVIEW_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.collect_vitals = bool(collect_vitals)

    def bind_hawkeye(self, hawkeye):
        self.hawkeye = hawkeye
        return {"bound": bool(hawkeye), "bridge": self.VERSION}

    def bind_field(self, field):
        self.field = field
        return {"bound": bool(field), "bridge": self.VERSION}

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_url(raw):
        try:
            parsed = urlparse(str(raw or ""))
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme or 'http'}://{host}{port}"
        except Exception:
            return ""

    @staticmethod
    def _package_available():
        return bool(
            importlib.util.find_spec("ruview")
            or importlib.util.find_spec("wifi_densepose")
        )

    @staticmethod
    def _fixed_run(args, timeout=8):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=creationflags,
        )

    def wifi_status(self):
        """Read the Windows Wi-Fi state without exposing saved credentials."""
        if os.name != "nt":
            return {
                "available": False,
                "platform": os.name,
                "connected": False,
                "mode": "unsupported_platform",
            }

        try:
            proc = self._fixed_run(["netsh", "wlan", "show", "interfaces"], timeout=5)
        except Exception as exc:
            return {
                "available": True,
                "connected": False,
                "error": type(exc).__name__,
            }

        values = {}
        for raw in (proc.stdout or "").splitlines():
            if ":" not in raw:
                continue
            key, value = raw.split(":", 1)
            key = key.strip().lower()
            if key in {
                "state", "ssid", "bssid", "signal", "radio type",
                "channel", "receive rate (mbps)", "transmit rate (mbps)",
            } and key not in values:
                values[key] = value.strip()

        signal = None
        raw_signal = values.get("signal", "").rstrip("%").strip()
        try:
            signal = int(raw_signal)
        except (TypeError, ValueError):
            pass

        state = values.get("state", "").lower()
        connected = state == "connected" and bool(values.get("ssid"))
        return {
            "available": True,
            "connected": connected,
            "state": values.get("state") or "unknown",
            "ssid": values.get("ssid") if connected else None,
            "signal_percent": signal,
            "radio_type": values.get("radio type"),
            "channel": values.get("channel"),
            "receive_rate_mbps": values.get("receive rate (mbps)"),
            "transmit_rate_mbps": values.get("transmit rate (mbps)"),
            "credential_visible": False,
        }

    @staticmethod
    def _profile_xml(ssid, password, auth="WPA2PSK", cipher="AES"):
        auth = str(auth or "WPA2PSK").strip().upper()
        cipher = str(cipher or "AES").strip().upper()
        aliases = {
            "WPA2-PERSONAL": "WPA2PSK",
            "WPA3-PERSONAL": "WPA3SAE",
            "WPA-PERSONAL": "WPAPSK",
        }
        auth = aliases.get(auth, auth)
        if auth not in {"WPA2PSK", "WPA3SAE", "WPAPSK"}:
            raise ValueError("auth must be WPA2PSK, WPA3SAE or WPAPSK")
        if cipher not in {"AES", "TKIP"}:
            raise ValueError("cipher must be AES or TKIP")
        if not password:
            raise ValueError("password is required for protected Wi-Fi")
        return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{escape(ssid)}</name>
  <SSIDConfig><SSID><name>{escape(ssid)}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM><security>
    <authEncryption>
      <authentication>{auth}</authentication>
      <encryption>{cipher}</encryption>
      <useOneX>false</useOneX>
    </authEncryption>
    <sharedKey>
      <keyType>passPhrase</keyType>
      <protected>false</protected>
      <keyMaterial>{escape(password)}</keyMaterial>
    </sharedKey>
  </security></MSM>
</WLANProfile>"""

    @staticmethod
    def _windows_set_profile_and_connect(ssid, password, auth, cipher):
        """Use Native Wi-Fi API so the password never needs a plaintext temp file."""
        if os.name != "nt":
            raise RuntimeError("Wi-Fi profile creation is available only on Windows")

        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class WLAN_INTERFACE_INFO(ctypes.Structure):
            _fields_ = [
                ("InterfaceGuid", GUID),
                ("strInterfaceDescription", wintypes.WCHAR * 256),
                ("isState", wintypes.DWORD),
            ]

        class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
            _fields_ = [
                ("dwNumberOfItems", wintypes.DWORD),
                ("dwIndex", wintypes.DWORD),
                ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
            ]

        class WLAN_CONNECTION_PARAMETERS(ctypes.Structure):
            _fields_ = [
                ("wlanConnectionMode", wintypes.DWORD),
                ("strProfile", wintypes.LPCWSTR),
                ("pDot11Ssid", ctypes.c_void_p),
                ("pDesiredBssidList", ctypes.c_void_p),
                ("dot11BssType", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
            ]

        wlan = ctypes.WinDLL("wlanapi")
        handle = wintypes.HANDLE()
        negotiated = wintypes.DWORD()
        rc = wlan.WlanOpenHandle(
            2, None, ctypes.byref(negotiated), ctypes.byref(handle)
        )
        if rc:
            raise OSError(rc, "WlanOpenHandle failed")

        interfaces = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
        try:
            rc = wlan.WlanEnumInterfaces(handle, None, ctypes.byref(interfaces))
            if rc:
                raise OSError(rc, "WlanEnumInterfaces failed")
            count = int(interfaces.contents.dwNumberOfItems)
            if count < 1:
                raise RuntimeError("no Windows Wi-Fi interface is available")

            base = (
                ctypes.addressof(interfaces.contents)
                + WLAN_INTERFACE_INFO_LIST.InterfaceInfo.offset
            )
            info = ctypes.cast(
                base, ctypes.POINTER(WLAN_INTERFACE_INFO)
            ).contents
            guid = info.InterfaceGuid

            profile = HawkeyeRuViewBridge._profile_xml(
                str(ssid), str(password), auth, cipher
            )
            reason = wintypes.DWORD()
            wlan.WlanSetProfile.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(GUID),
                wintypes.DWORD,
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.BOOL,
                ctypes.c_void_p,
                ctypes.POINTER(wintypes.DWORD),
            ]
            wlan.WlanSetProfile.restype = wintypes.DWORD
            rc = wlan.WlanSetProfile(
                handle,
                ctypes.byref(guid),
                0,
                profile,
                None,
                True,
                None,
                ctypes.byref(reason),
            )
            if rc:
                raise OSError(rc, f"WlanSetProfile failed (reason={reason.value})")

            params = WLAN_CONNECTION_PARAMETERS(
                0,  # wlan_connection_mode_profile
                str(ssid),
                None,
                None,
                3,  # dot11_BSS_type_any
                0,
            )
            wlan.WlanConnect.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(GUID),
                ctypes.POINTER(WLAN_CONNECTION_PARAMETERS),
                ctypes.c_void_p,
            ]
            wlan.WlanConnect.restype = wintypes.DWORD
            rc = wlan.WlanConnect(
                handle, ctypes.byref(guid), ctypes.byref(params), None
            )
            if rc:
                raise OSError(rc, "WlanConnect failed")
            return {
                "profile_written": True,
                "connect_requested": True,
                "interface": str(info.strInterfaceDescription),
            }
        finally:
            if interfaces:
                wlan.WlanFreeMemory(interfaces)
            wlan.WlanCloseHandle(handle, None)

    def _save_secret(self, ssid, password):
        if not self.secure_vault:
            return None
        return self.secure_vault.put(
            f"wifi:{ssid}", "hawkeye-ruview-wifi", str(password)
        )

    def connect_wifi(
        self,
        *,
        ssid,
        password=None,
        secret_id=None,
        remember=True,
        auth="WPA2PSK",
        cipher="AES",
        wait_seconds=15,
    ):
        ssid = str(ssid or "").strip()
        if not ssid:
            raise ValueError("ssid is required")
        if len(ssid) > 32:
            raise ValueError("ssid is too long")

        resolved = str(password or "")
        if not resolved and secret_id:
            resolved = self.secure_vault.resolve(str(secret_id))
        if not resolved:
            raise ValueError("password or secret_id is required")

        result = self._windows_set_profile_and_connect(
            ssid, resolved, auth, cipher
        )

        deadline = time.time() + max(0, min(int(wait_seconds), 30))
        status = self.wifi_status()
        while time.time() < deadline and not (
            status.get("connected") and status.get("ssid") == ssid
        ):
            time.sleep(0.4)
            status = self.wifi_status()

        secret_ref = None
        if bool(remember) and status.get("connected") and status.get("ssid") == ssid:
            secret_ref = self._save_secret(ssid, resolved)

        # Do not return or retain the plaintext value.
        resolved = ""
        return {
            **result,
            "connected": bool(status.get("connected") and status.get("ssid") == ssid),
            "ssid": ssid,
            "wifi": status,
            "secret_ref": secret_ref,
            "password_returned": False,
            "mobile_credential_entry": False,
        }

    def _candidate_base_urls(self):
        out = []
        for value in (self.base_url, *self.FALLBACK_BASE_URLS):
            value = str(value or "").rstrip("/")
            if value and value not in out:
                out.append(value)
        return out

    def probe_ruview(self):
        headers = {"Accept": "application/json"}
        token = str(os.getenv("RUVIEW_API_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = "Bearer " + token
        errors = {}
        for base_url in self._candidate_base_urls():
            endpoint = base_url + "/api/v1/sensing/latest"
            try:
                with urlopen(Request(endpoint, headers=headers), timeout=0.6) as response:
                    raw = response.read(1024 * 1024)
                    payload = json.loads(raw.decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("RuView latest endpoint did not return an object")
                    return {
                        "reachable": True,
                        "http_status": int(getattr(response, "status", 200)),
                        "base_url": base_url,
                        "latest": payload,
                    }
            except Exception as exc:
                errors[self._safe_url(base_url)] = type(exc).__name__
        return {
            "reachable": False,
            "errors": errors,
        }

    @classmethod
    def _payload_has_csi(cls, payload):
        payload = dict(payload or {}) if isinstance(payload, dict) else {}
        window = payload.get("window")
        if isinstance(window, dict) and (
            isinstance(window.get("amplitudes"), list)
            or isinstance(window.get("phases"), list)
        ):
            return True
        nodes = payload.get("nodes")
        if isinstance(nodes, list) and any(
            isinstance(node, dict)
            and (
                node.get("subcarrier_count") is not None
                or isinstance(node.get("amplitude"), list)
            )
            for node in nodes
        ):
            return True
        if payload.get("schema_version") and (
            "captured_at" in payload or "features" in payload
        ):
            return True
        text = json.dumps(payload, sort_keys=True, default=str).lower()
        return any(hint in text for hint in cls.CSI_HINTS)

    @staticmethod
    def _event_fingerprint(event):
        raw = json.dumps(
            event or {}, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def normalize_ruview_event(self, event):
        event = dict(event or {})
        kind = str(
            event.get("type")
            or event.get("kind")
            or ("sensing_update" if "classification" in event else "sensing")
        ).strip().lower()
        classification = event.get("classification")
        classification = classification if isinstance(classification, dict) else {}
        features = event.get("features")
        features = features if isinstance(features, dict) else {}

        nodes = event.get("nodes")
        nodes = nodes if isinstance(nodes, list) else []
        first_node = next((x for x in nodes if isinstance(x, dict)), {})
        node_id = str(
            event.get("node_id")
            or event.get("node")
            or first_node.get("node_id")
            or "ruview"
        ).strip()

        confidence = self._clamp(
            event.get(
                "confidence",
                classification.get(
                    "confidence",
                    event.get("presence_score", event.get("signal_quality_score", 0.7)),
                ),
            )
        )

        persons = event.get("persons")
        if not isinstance(persons, list):
            persons = []

        count_source = (
            event.get("estimated_persons")
            if event.get("estimated_persons") is not None
            else event.get("n_persons")
        )
        try:
            person_count = int(count_source) if count_source is not None else len(persons)
        except (TypeError, ValueError):
            person_count = len(persons)

        presence_value = event.get("presence")
        if presence_value is None:
            presence_value = classification.get("presence")

        motion_value = event.get("motion")
        if motion_value is None:
            motion_value = features.get("motion_band_power")
        motion_level = classification.get("motion_level")

        rssi_value = event.get("rssi")
        if rssi_value is None:
            rssi_value = first_node.get("rssi_dbm", features.get("mean_rssi"))

        pose_keypoints = event.get("pose_keypoints")
        if not isinstance(pose_keypoints, list):
            pose_keypoints = []

        csi = self._payload_has_csi(event)
        payload = {
            "modality": "wifi_csi" if csi else "rf",
            "provider": "RuView",
            "event_type": kind,
            "node_id": node_id,
            "presence": bool(presence_value) if presence_value is not None else None,
            "motion": motion_value,
            "motion_level": motion_level,
            "motion_energy": event.get("motion_energy"),
            "person_count": max(0, person_count),
            "presence_score": event.get("presence_score"),
            "rssi": rssi_value,
            "persons": persons[:20],
            "pose_keypoints": pose_keypoints[:68],
            "signal_quality": event.get("signal_quality_score", event.get("signal_quality")),
            "quality_verdict": event.get("quality_verdict"),
            "source": event.get("source"),
            "limitation": (
                "RuView scene outputs are RF-model inferences, not camera observations. "
                "Accuracy depends on CSI hardware, calibration, room geometry and the deployed model."
            ),
        }
        return {
            "kind": kind,
            "node_id": node_id,
            "confidence": confidence,
            "payload": payload,
            "fingerprint": self._event_fingerprint(event),
            "csi": csi,
        }

    def ingest_event(self, session_id, event):
        if not self.hawkeye:
            raise RuntimeError("HAWKEYE coordinator is not bound")
        normalized = self.normalize_ruview_event(event)
        source = "ruview:" + normalized["node_id"] + ":" + normalized["fingerprint"][:16]
        perception = self.hawkeye.record_lane(
            str(session_id),
            "perception",
            normalized["payload"],
            evidence_state="INFERRED",
            confidence=normalized["confidence"],
            source_refs=[source],
            limitations=[
                "presence/motion/person-count/pose are model inferences from RF measurements",
                "full pose/through-wall capability requires compatible CSI hardware and calibration",
            ],
            provenance={
                "provider": "RuView",
                "bridge": self.VERSION,
                "fingerprint": normalized["fingerprint"],
                "csi": normalized["csi"],
            },
        )

        physio = None
        if self.collect_vitals:
            vitals = {}
            for key in ("breathing_rate_bpm", "heartrate_bpm"):
                if event.get(key) is not None:
                    vitals[key] = event.get(key)
            if vitals:
                vitals["source"] = "RuView RF estimate"
                physio = self.hawkeye.record_lane(
                    str(session_id),
                    "physio",
                    vitals,
                    evidence_state="INFERRED",
                    confidence=normalized["confidence"],
                    source_refs=[source],
                    limitations=[
                        "RF vital-sign estimates are not a medical diagnosis",
                        "vital estimates require explicit owner opt-in",
                    ],
                    provenance={
                        "provider": "RuView",
                        "bridge": self.VERSION,
                        "fingerprint": normalized["fingerprint"],
                    },
                )

        self._append_sample(
            {
                "at": time.time(),
                "source": "ruview",
                "session_id": str(session_id),
                "fingerprint": normalized["fingerprint"],
                "event_type": normalized["kind"],
                "csi": normalized["csi"],
            }
        )
        return {
            "bridge": self.VERSION,
            "perception": perception,
            "physio": physio,
            "vitals_collected": bool(physio),
        }

    def _append_sample(self, row):
        safe = dict(row or {})
        safe.pop("password", None)
        safe.pop("secret", None)
        with self.samples_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, separators=(",", ":"), default=str) + "\n")

    def sample(self, session_id=None):
        """Read RuView when available, otherwise return an honest RSSI-only snapshot."""
        probe = self.probe_ruview()
        if probe.get("reachable") and isinstance(probe.get("latest"), dict):
            latest = probe["latest"]
            normalized = self.normalize_ruview_event(latest)
            if session_id:
                return {
                    "mode": "ruview",
                    "latest": latest,
                    "normalized": normalized,
                    "recorded": self.ingest_event(session_id, latest),
                }
            return {
                "mode": "ruview",
                "latest": latest,
                "normalized": normalized,
                "recorded": None,
            }

        wifi = self.wifi_status()
        snapshot = {
            "mode": "rssi_only",
            "wifi": wifi,
            "evidence_state": "MEASURED" if wifi.get("signal_percent") is not None else "UNKNOWN",
            "capability": "coarse RF signal observation only",
            "limitation": (
                "Consumer Wi-Fi RSSI alone cannot reconstruct body pose or reliably see through walls. "
                "Install a CSI-capable RuView sensor node for full RF sensing."
            ),
        }
        self._append_sample(
            {
                "at": time.time(),
                "source": "windows-rssi",
                "ssid": wifi.get("ssid"),
                "signal_percent": wifi.get("signal_percent"),
                "connected": wifi.get("connected"),
            }
        )
        if session_id and self.hawkeye and wifi.get("signal_percent") is not None:
            snapshot["recorded"] = self.hawkeye.record_lane(
                str(session_id),
                "perception",
                {
                    "modality": "wifi_rssi",
                    "ssid": wifi.get("ssid"),
                    "signal_percent": wifi.get("signal_percent"),
                    "channel": wifi.get("channel"),
                    "observation": "radio signal measurement; no person/pose inference",
                },
                evidence_state="MEASURED",
                confidence=1.0,
                source_refs=["windows-wifi:rssi"],
                limitations=[snapshot["limitation"]],
                provenance={"bridge": self.VERSION},
            )
        return snapshot

    def status(self, refresh=False):
        wifi = self.wifi_status()
        probe = self.probe_ruview() if refresh else {"reachable": False, "not_probed": True}
        latest = probe.get("latest") if isinstance(probe.get("latest"), dict) else None
        csi = bool(latest and self._payload_has_csi(latest))
        if csi:
            mode = "csi"
        elif wifi.get("connected"):
            mode = "rssi_only"
        else:
            mode = "unconfigured"

        return {
            "agent": "HAWKEYE RUVIEW",
            "version": self.VERSION,
            "authority": "KRISHNA",
            "mode": mode,
            "wifi": wifi,
            "ruview": {
                "python_client_installed": self._package_available(),
                "server_url": self._safe_url(probe.get("base_url") or self.base_url),
                "candidate_urls": [self._safe_url(x) for x in self._candidate_base_urls()],
                "reachable": bool(probe.get("reachable")),
                "csi_detected": csi,
                "latest": self.normalize_ruview_event(latest) if latest else None,
            },
            "credentials": {
                "entry_surface": "KRISHNA PC only",
                "mobile_entry_allowed": False,
                "storage": "Windows DPAPI SecureSecretVault",
                "plaintext_returned": False,
            },
            "privacy": {
                "vitals_enabled": self.collect_vitals,
                "default_vitals_policy": "off",
                "raw_wifi_password_in_evidence": False,
            },
            "capability_limit": (
                "Connected consumer Wi-Fi provides RSSI-only sensing. Full RuView presence/pose/through-wall "
                "sensing requires compatible CSI hardware and room calibration."
            ),
        }
