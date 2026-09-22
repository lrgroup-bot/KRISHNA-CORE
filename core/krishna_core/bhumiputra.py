from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
import time
import uuid

from .field_perception import FieldPerceptionPolicy


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
    VERSION = "0.2.0"

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
        "people": ("person", "people", "face", "ppe", "worker", "crowd"),
        "vehicle": ("car", "bike", "motorcycle", "bus", "truck", "dashboard", "number plate", "license plate"),
        "electronics": ("pcb", "motherboard", "circuit", "connector", "wire", "device", "electronics"),
        "document": ("document", "label", "sign", "screen", "ocr", "serial number", "asset tag"),
        "hazard": ("fire", "smoke", "leak", "exposed wire", "obstacle", "open edge"),
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
            "perception_policy": FieldPerceptionPolicy.status(),
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
            "You are Bhumiputra, KRISHNA's live field perception, geo-engineering and inspection specialist. "
            "Analyze ONLY what can be supported by this camera frame and supplied sensor context. "
            "Automatically identify whether the scene is terrain/quarry, building/tower/bridge, road, machinery, "
            "utility infrastructure, people, vehicle, electronics/device, document/screen, hazard, or general. "
            "For structures/buildings, identify visible structural system/components (columns, beams, bracing, slabs, "
            "walls, openings, facade, stairs, roof, tower members, joints), apparent materials, access/clearance, "
            "visible cracks/spalling/corrosion/deformation/dampness and measurements only when scale/depth evidence exists. "
            "For terrain/quarry, identify slopes, exposed rock/soil, access routes, drainage, excavation activity and survey gaps. "
            "For vehicles, report category, visible make/model cues, registration/asset markings when requested, body/tyre/light/glass "
            "condition, dashboard indicators and visible leaks/smoke/damaged parts; hidden mechanical diagnosis requires OBD/CAN or measurements. "
            "For electronics, identify visible PCB/components/connectors/cables, labels, damaged/burnt/corroded areas and explain likely functional "
            "blocks or signal/power flow without inventing electrical measurements. For people, report count, visible PPE/activity and face presence; "
            "identify a person only if an explicitly enrolled, consented local face profile is supplied, otherwise identity is UNKNOWN. "
            "Read ordinary signs, serial/model numbers, asset tags and requested plate text. Detect hazards such as fire/smoke, exposed wiring, leaks, "
            "obstacles/open edges and missing visible PPE. Compare with prior observations when temporal context is supplied and state what changed. "
            "Never claim hidden reinforcement, foundation condition, certified load capacity, exact material grade, subsurface reserves or original "
            "design intent from imagery alone. Mark important findings as observed, measured, estimated, inferred or unknown. "
            + FieldPerceptionPolicy.prompt_rules() + " "
            "Return a concise field result with: scene_type, visible_components, text_or_asset_markings, people_and_ppe, "
            "vehicle_or_equipment_details, measurements_or_estimates, visible_condition, hazards_or_access_constraints, "
            "temporal_changes, recommended_next_scan, unknowns, evidence_state and confidence. "
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
            "scene_modes": sorted(self.SCENE_MODES),
            "structural_truth_policy": dict(self.STRUCTURAL_TRUTH_POLICY),
            "perception": FieldPerceptionPolicy.status(),
            "heavy_pipeline": list(self.HEAVY_PIPELINE),
            "main_loop_blocking": False,
            "menu_visible": False,
            "ready": True,
        }
