from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import math
import time
import uuid


EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    alt_m: float | None = None

    def as_dict(self):
        return asdict(self)


class BhumiputraAgent:
    """KRISHNA's isolated field geo-engineering specialist.

    Bhumiputra owns survey planning/state and describes heavy work as isolated
    worker jobs. Camera/AR, photogrammetry, DEM/GIS, geology and routing
    backends plug into this contract without running inside KRISHNA's main
    conversational loop.
    """

    AGENT_ID = "bhumiputra"
    VERSION = "0.1.0"

    HEAVY_PIPELINE = (
        "mobile-camera-ingest",
        "gnss-rtk-fusion",
        "photogrammetry-3d",
        "terrain-dem-analysis",
        "geology-evidence-correlation",
        "haul-road-routing",
        "ar-overlay-generation",
        "survey-report-generation",
    )

    OUTPUTS = (
        "boundary.geojson",
        "boundary.kml",
        "gnss.csv",
        "imu.csv",
        "observations.jsonl",
        "point-cloud.las",
        "terrain.tif",
        "mesh.glb",
        "route-candidates.geojson",
        "survey-report.pdf",
    )

    SCENE_MODES = {
        "terrain": ("hill", "quarry", "rock face", "land", "slope", "cutting"),
        "structure": ("building", "tower", "bridge", "wall", "column", "beam", "roof", "foundation"),
        "road": ("road", "track", "haul road", "culvert", "turning radius", "clearance"),
        "machinery": ("excavator", "loader", "truck", "crane", "drill", "crusher"),
        "utility": ("transmission tower", "telecom tower", "pole", "substation", "pipeline"),
        "general": (),
    }

    STRUCTURAL_TRUTH_POLICY = {
        "visible_geometry": "may be described/measured when scale or depth is available",
        "visible_condition": "report only observable surface evidence and confidence",
        "hidden_reinforcement": "unknown without drawings, scanning/NDT or destructive verification",
        "foundation": "unknown unless exposed or supported by drawings/geotechnical evidence",
        "load_capacity": "never infer a certified safe load from camera imagery alone",
        "material_grade": "visual classification is preliminary; grade requires records/testing",
        "as_built_design": "infer visible arrangement only; do not claim original design intent without drawings",
    }

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.surveys_dir = self.state_dir / "surveys"
        self.surveys_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir = self.state_dir / "mobile-evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_cipher = None
        self.require_evidence_encryption = False

    def bind_evidence_cipher(self, cipher, *, require_encryption=False):
        self.evidence_cipher = cipher
        self.require_evidence_encryption = bool(require_encryption)
        return {"bound": cipher is not None, "available": bool(getattr(cipher, "available", False)), "required": self.require_evidence_encryption}

    @staticmethod
    def _point(value) -> GeoPoint:
        if isinstance(value, GeoPoint):
            p = value
        elif isinstance(value, dict):
            p = GeoPoint(
                float(value["lat"]),
                float(value.get("lon", value.get("lng"))),
                None if value.get("alt_m") is None else float(value["alt_m"]),
            )
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            p = GeoPoint(
                float(value[0]), float(value[1]),
                None if len(value) < 3 or value[2] is None else float(value[2]),
            )
        else:
            raise ValueError("point must be GeoPoint, {lat,lon}, or [lat,lon]")

        if not -90 <= p.lat <= 90:
            raise ValueError(f"latitude out of range: {p.lat}")
        if not -180 <= p.lon <= 180:
            raise ValueError(f"longitude out of range: {p.lon}")
        return p

    @classmethod
    def _points(cls, points):
        rows = [cls._point(x) for x in (points or [])]
        if len(rows) < 3:
            raise ValueError("survey boundary requires at least 3 coordinate points")
        unique = {(round(x.lat, 10), round(x.lon, 10)) for x in rows}
        if len(unique) < 3:
            raise ValueError("survey boundary requires at least 3 unique coordinate points")
        return rows

    @staticmethod
    def _haversine(a: GeoPoint, b: GeoPoint) -> float:
        p1, p2 = math.radians(a.lat), math.radians(b.lat)
        dp = math.radians(b.lat - a.lat)
        dl = math.radians(b.lon - a.lon)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))

    @classmethod
    def boundary_metrics(cls, points):
        pts = cls._points(points)
        lat0 = math.radians(sum(x.lat for x in pts) / len(pts))
        lon0 = math.radians(sum(x.lon for x in pts) / len(pts))

        xy = []
        for p in pts:
            lat = math.radians(p.lat)
            lon = math.radians(p.lon)
            x = EARTH_RADIUS_M * (lon - lon0) * math.cos(lat0)
            y = EARTH_RADIUS_M * (lat - lat0)
            xy.append((x, y))

        twice_area = 0.0
        perimeter = 0.0
        for i, (x1, y1) in enumerate(xy):
            x2, y2 = xy[(i + 1) % len(xy)]
            twice_area += x1 * y2 - x2 * y1
            perimeter += cls._haversine(pts[i], pts[(i + 1) % len(pts)])
        area_m2 = abs(twice_area) / 2.0

        if area_m2 < 1.0:
            raise ValueError("survey boundary area is too small or degenerate")

        return {
            "points": [x.as_dict() for x in pts],
            "point_count": len(pts),
            "area_m2": area_m2,
            "area_hectares": area_m2 / 10_000.0,
            "perimeter_m": perimeter,
            "bbox": {
                "min_lat": min(x.lat for x in pts),
                "max_lat": max(x.lat for x in pts),
                "min_lon": min(x.lon for x in pts),
                "max_lon": max(x.lon for x in pts),
            },
            "method": "local-tangent-plane polygon estimate",
            "engineering_note": (
                "Use survey-grade GNSS/RTK or authoritative cadastral coordinates "
                "when legal/engineering boundary accuracy is required."
            ),
        }

    def _live_path(self, session_id: str) -> Path:
        safe = "".join(ch for ch in str(session_id) if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("invalid session_id")
        return self.state_dir / f"live-{safe}.json"

    def start_live_session(self, *, project="KRISHNA", purpose="live field scan",
                           coordinates=None, scene_hint="auto"):
        session_id = str(uuid.uuid4())
        row = {
            "session_id": session_id,
            "agent": self.AGENT_ID,
            "version": self.VERSION,
            "project": str(project or "KRISHNA"),
            "purpose": str(purpose or "live field scan"),
            "scene_hint": str(scene_hint or "auto").lower(),
            "coordinates": dict(coordinates or {}),
            "started_at": time.time(),
            "updated_at": time.time(),
            "status": "live",
            "frame_count": 0,
            "latest_analysis": None,
            "truth_policy": dict(self.STRUCTURAL_TRUTH_POLICY),
            "privacy": {
                "camera_transport": "paired KRISHNA private-network endpoint",
                "vision_provider": "local-only",
                "cloud_upload": False,
            },
            "execution": {
                "main_loop_blocking": False,
                "analysis_cadence": "sampled frames; heavy reconstruction is asynchronous/isolated",
            },
        }
        self._live_path(session_id).write_text(
            json.dumps(row, indent=2, sort_keys=True), encoding="utf-8"
        )
        return row

    def live_prompt(self, *, scene_hint="auto", user_goal="", sensor_context=None):
        hint = str(scene_hint or "auto").strip().lower()
        sensors = dict(sensor_context or {})
        return (
            "You are Bhumiputra, KRISHNA's field geo-engineering and visible-structure inspection specialist. "
            "Analyze ONLY what can be supported by this camera frame and supplied sensor context. "
            "Automatically identify whether the scene is terrain/quarry, building/tower/bridge, road, machinery, "
            "utility infrastructure, or general. For structures, identify visible structural system/components "
            "(columns, beams, bracing, slabs, walls, roof, tower members, joints), apparent materials, geometry, "
            "access/clearance, visible deterioration or damage indicators, and measurements only when scale/depth "
            "evidence is supplied. For terrain, identify slopes, exposed rock/soil, access routes, drainage and "
            "survey gaps. Never claim hidden reinforcement, foundation condition, certified load capacity, exact "
            "material grade, subsurface reserves, or original design intent from imagery alone. Mark each important "
            "finding as observed, estimated, inferred, or unknown. Return a concise field result with: scene_type, "
            "visible_components, measurements_or_estimates, visible_condition, hazards_or_access_constraints, "
            "recommended_next_scan, unknowns, and confidence. "
            f"Scene hint: {hint}. User goal: {str(user_goal or 'automatic field scan')}. "
            f"Sensor context: {json.dumps(sensors, ensure_ascii=False)[:4000]}."
        )

    def record_live_analysis(self, session_id: str, analysis: str, *,
                             model=None, sensor_context=None, frame_meta=None):
        path = self._live_path(session_id)
        if not path.exists():
            raise KeyError(f"live session not found: {session_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        now = time.time()
        item = {
            "at": now,
            "analysis": str(analysis or "").strip(),
            "model": str(model or ""),
            "sensor_context": dict(sensor_context or {}),
            "frame_meta": dict(frame_meta or {}),
        }
        if not item["analysis"]:
            raise ValueError("live analysis is empty")
        data["frame_count"] = int(data.get("frame_count") or 0) + 1
        data["latest_analysis"] = item
        data["updated_at"] = now
        data["status"] = "live"
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "session_id": session_id,
            "frame_count": data["frame_count"],
            "latest_analysis": item,
            "truth_policy": data["truth_policy"],
        }

    def get_live_session(self, session_id: str):
        path = self._live_path(session_id)
        if not path.exists():
            raise KeyError(f"live session not found: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def store_mobile_evidence(self, session_id: str, raw: bytes, content_type="image/jpeg", sensor_context=None):
        """Persist only curator-selected mobile evidence before the phone deletes its copy.

        Storage is content-addressed per session, bounded, and deduplicated. This method
        does not perform model inference and therefore does not add compute load.
        """
        if not raw:
            raise ValueError("mobile evidence is empty")
        kind = str(content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
        limits = {"image": 2 * 1024 * 1024, "audio": 1024 * 1024, "video": 4 * 1024 * 1024}
        modality = kind.split("/", 1)[0] if "/" in kind else "unknown"
        if modality not in limits:
            raise ValueError("unsupported mobile evidence content type")
        if len(raw) > limits[modality]:
            raise ValueError(f"curated {modality} evidence exceeds bounded size")
        suffix = {
            "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
            "audio/webm": ".audio.webm", "audio/mp4": ".audio.mp4", "audio/ogg": ".audio.ogg",
            "video/webm": ".video.webm", "video/mp4": ".video.mp4",
        }.get(kind)
        if not suffix:
            raise ValueError("unsupported mobile evidence media type")
        safe_session = "".join(ch for ch in str(session_id or "") if ch.isalnum() or ch in "-_")
        if not safe_session:
            raise ValueError("invalid session_id")
        digest = hashlib.sha256(raw).hexdigest()
        evidence_id = f"{safe_session}-{digest[:20]}"
        encrypted = bool(self.evidence_cipher is not None and getattr(self.evidence_cipher, "available", False))
        if self.require_evidence_encryption and not encrypted:
            raise RuntimeError("Hawkeye PC evidence encryption is required but unavailable")
        payload_path = self.evidence_dir / (f"{evidence_id}.payload.enc" if encrypted else f"{evidence_id}{suffix}")
        meta = self.evidence_dir / f"{evidence_id}.json"
        deduplicated = payload_path.exists() and meta.exists()
        if not payload_path.exists():
            if encrypted:
                aad=f"hawkeye:{evidence_id}".encode("utf-8")
                envelope=self.evidence_cipher.encrypt(raw,aad)
                payload_path.write_text(json.dumps(envelope,separators=(",",":")),encoding="utf-8")
            else:
                payload_path.write_bytes(raw)
        record = {
            "evidence_id": evidence_id,
            "session_id": safe_session,
            "sha256": digest,
            "bytes": len(raw),
            "content_type": kind,
            "modality": modality,
            "source": "hawkeye-mobile-curator",
            "sensor_context": dict(sensor_context or {}),
            "received_at": time.time(),
            "retained_pc": True,
            "raw_cloud_upload": False,
            "encrypted_at_rest": encrypted,
            "encryption": "AES-256-GCM + Windows-DPAPI" if encrypted else "test-platform-plaintext-fallback",
            "payload_file": payload_path.name,
        }
        meta.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        pruned = self._prune_mobile_evidence(max_items=64, max_bytes=192 * 1024 * 1024)
        return {
            "evidence_id": evidence_id,
            "sha256": digest,
            "bytes": len(raw),
            "content_type": kind,
            "modality": modality,
            "retained_pc": True,
            "deduplicated": deduplicated,
            "encrypted_at_rest": encrypted,
            "storage_policy": {"max_items": 64, "max_bytes": 192 * 1024 * 1024},
            "pruned": pruned,
        }

    def _prune_mobile_evidence(self, *, max_items: int, max_bytes: int):
        rows = sorted(self.evidence_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        def pair_bytes(meta_path):
            total = meta_path.stat().st_size if meta_path.exists() else 0
            stem = meta_path.stem
            for ext in (".jpg", ".png", ".webp", ".audio.webm", ".audio.mp4", ".audio.ogg", ".video.webm", ".video.mp4", ".payload.enc"):
                image = self.evidence_dir / f"{stem}{ext}"
                if image.exists():
                    total += image.stat().st_size
            return total
        total = sum(pair_bytes(x) for x in rows)
        deleted = 0
        while rows and (len(rows) > max(1, int(max_items)) or total > max(8 * 1024 * 1024, int(max_bytes))):
            old = rows.pop(0)
            removed = pair_bytes(old)
            stem = old.stem
            for ext in (".jpg", ".png", ".webp", ".audio.webm", ".audio.mp4", ".audio.ogg", ".video.webm", ".video.mp4", ".payload.enc"):
                image = self.evidence_dir / f"{stem}{ext}"
                if image.exists():
                    image.unlink()
            if old.exists():
                old.unlink()
            total = max(0, total - removed)
            deleted += 1
        return deleted

    def mobile_evidence_status(self):
        rows = list(self.evidence_dir.glob("*.json"))
        total = 0
        for meta in rows:
            total += meta.stat().st_size
            for ext in (".jpg", ".png", ".webp", ".audio.webm", ".audio.mp4", ".audio.ogg", ".video.webm", ".video.mp4", ".payload.enc"):
                image = self.evidence_dir / f"{meta.stem}{ext}"
                if image.exists():
                    total += image.stat().st_size
        return {"items": len(rows), "bytes": total, "max_items": 64, "max_bytes": 192 * 1024 * 1024,
                "encryption_bound": self.evidence_cipher is not None,
                "encryption_available": bool(getattr(self.evidence_cipher, "available", False)) if self.evidence_cipher is not None else False,
                "encryption_required": self.require_evidence_encryption}

    def _survey_path(self, survey_id: str) -> Path:
        safe = "".join(ch for ch in str(survey_id) if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("invalid survey_id")
        return self.surveys_dir / f"{safe}.json"

    def plan_survey(self, points, *, project="KRISHNA", purpose="field geo-engineering",
                    vehicle_profile=None, requested_outputs=None):
        metrics = self.boundary_metrics(points)
        survey_id = str(uuid.uuid4())
        now = time.time()
        outputs = list(requested_outputs or self.OUTPUTS)
        record = {
            "survey_id": survey_id,
            "agent": self.AGENT_ID,
            "version": self.VERSION,
            "project": str(project or "KRISHNA"),
            "purpose": str(purpose or "field geo-engineering"),
            "created_at": now,
            "boundary": metrics,
            "vehicle_profile": vehicle_profile or {},
            "capture_plan": [
                "confirm GNSS accuracy and boundary position",
                "capture boundary corners and access points",
                "walk/drive overlapping camera passes around visible faces",
                "capture road width, turning radius, gradient and overhead constraints",
                "record occluded/unseen zones instead of guessing",
                "send heavy reconstruction and routing jobs to Bhumiputra worker",
            ],
            "heavy_pipeline": list(self.HEAVY_PIPELINE),
            "execution": {
                "authority": "KRISHNA -> Bhumiputra",
                "main_loop_blocking": False,
                "heavy_compute": "isolated worker/process only",
                "state_root": str(self.state_dir),
                "ui": "no main-menu item; invoked through KRISHNA/mobile field mode",
            },
            "confidence_policy": {
                "camera_visible_geometry": "may be measured when capture quality is sufficient",
                "terrain_derived_volume": "label with DEM/photogrammetry accuracy and reference surface",
                "geology_inference": "must be labelled inferred and source-backed",
                "subsurface_resource": "never claim verified from camera imagery alone",
                "mineable_reserve": "requires geological/exploration evidence and applicable engineering/regulatory inputs",
            },
            "route_policy": {
                "candidate_generation": "roads + DEM + slope + constraints + vehicle profile",
                "field_verification": "camera/GNSS verification required before operational recommendation",
                "unknowns": "mark missing bridge/load/clearance/surface data as unknown",
            },
            "requested_outputs": outputs,
            "status": "planned",
            "observations": [],
        }
        self._survey_path(survey_id).write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )
        return record

    def record_observation(self, survey_id: str, observation: dict):
        path = self._survey_path(survey_id)
        if not path.exists():
            raise KeyError(f"survey not found: {survey_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        row = {
            "at": time.time(),
            "source": str((observation or {}).get("source") or "mobile-field"),
            "type": str((observation or {}).get("type") or "field-observation"),
            "payload": dict((observation or {}).get("payload") or {}),
            "confidence": str((observation or {}).get("confidence") or "unverified"),
        }
        data.setdefault("observations", []).append(row)
        data["updated_at"] = row["at"]
        data["status"] = "field-data-collected"
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return {"survey_id": survey_id, "observation": row, "count": len(data["observations"])}

    def get_survey(self, survey_id: str):
        path = self._survey_path(survey_id)
        if not path.exists():
            raise KeyError(f"survey not found: {survey_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def status(self):
        surveys = sorted(self.surveys_dir.glob("*.json"))
        return {
            "agent_id": self.AGENT_ID,
            "version": self.VERSION,
            "role": "isolated field geospatial/geological engineering specialist",
            "state_dir": str(self.state_dir),
            "survey_count": len(surveys),
            "live_sessions": len(list(self.state_dir.glob("live-*.json"))),
            "mobile_evidence": self.mobile_evidence_status(),
            "scene_modes": sorted(self.SCENE_MODES),
            "structural_truth_policy": dict(self.STRUCTURAL_TRUTH_POLICY),
            "heavy_pipeline": list(self.HEAVY_PIPELINE),
            "main_loop_blocking": False,
            "menu_visible": False,
            "ready": True,
        }
