"""Hawkeye field platform contracts: devices, sensors, maps, sync and evidence.

The registry is deliberately provider-neutral. Google content is visualization-only and
must never be cached or used as machine-analysis input unless its applicable terms allow it.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, time, uuid

SENSOR_STREAMS=("VIDEO","AUDIO","IMU","GNSS","DEPTH","GAZE","GESTURE","THERMAL","MMWAVE","WIFI_RSSI","WIFI_CSI","RF_FIELD","EEG","EMG")
EVIDENCE_STATES=("MEASURED","OBSERVED","INFERRED","PREDICTED","UNKNOWN")

MAP_PROVIDERS={
 "osm":{"free_data":True,"offline_data":True,"machine_analysis":True,"notes":"Use OSM data or self-hosted/licensed tiles; do not bulk-download osm.org public tiles."},
 "maplibre":{"free":True,"role":"2D/3D renderer","offline":True},
 "pmtiles":{"free":True,"role":"single-file vector/raster/DEM field packs","offline":True},
 "cesiumjs":{"free":True,"role":"3D globe and OGC 3D Tiles renderer"},
 "kartaview":{"free":True,"role":"street-level imagery; coverage dependent"},
 "opendronemap":{"free":True,"role":"photogrammetry, orthophoto, DEM, point cloud, 3D model","offline":True},
 "bhuvan":{"role":"India EO/thematic layers; obey dataset/service terms"},
 "google_maps":{"role":"optional licensed visualization","cache":False,"machine_analysis":False},
 "google_streetview":{"role":"optional licensed visualization","cache":False,"machine_analysis":False},
 "google_3d_tiles":{"role":"optional licensed visualization","cache":False,"machine_analysis":False},
}

@dataclass
class DeviceCapability:
    device_id:str
    kind:str
    sensors:list[str]
    capabilities:list[str]
    updated_at:float

class HawkeyeFieldPlatform:
    def __init__(self,state_root):
        self.root=Path(state_root); self.root.mkdir(parents=True,exist_ok=True)
        self.devices_file=self.root/"devices.json"
        self.queue_file=self.root/"sync-queue.jsonl"

    def register_device(self,device_id,kind,sensors=(),capabilities=()):
        bad=sorted(set(sensors)-set(SENSOR_STREAMS))
        if bad: raise ValueError("unsupported sensors: "+",".join(bad))
        row=DeviceCapability(str(device_id),str(kind),sorted(set(sensors)),sorted(set(capabilities)),time.time())
        rows=self.devices()
        rows=[x for x in rows if x["device_id"]!=row.device_id]+[asdict(row)]
        self.devices_file.write_text(json.dumps(rows,indent=2),encoding="utf-8")
        return asdict(row)

    def devices(self):
        if not self.devices_file.exists(): return []
        return json.loads(self.devices_file.read_text(encoding="utf-8"))

    def map_stack(self): return MAP_PROVIDERS

    def queue_observation(self,session_id,path,evidence_state="OBSERVED",metadata=None):
        if evidence_state not in EVIDENCE_STATES: raise ValueError("invalid evidence state")
        p=Path(path)
        digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        row={"id":str(uuid.uuid4()),"session_id":str(session_id),"path":str(p),"sha256":digest,
             "evidence_state":evidence_state,"metadata":dict(metadata or {}),"status":"pending",
             "created_at":time.time(),"retry_count":0}
        with self.queue_file.open("a",encoding="utf-8") as f:f.write(json.dumps(row,separators=(",",":"))+"\n")
        return row

    def pending(self):
        if not self.queue_file.exists():return []
        return [json.loads(x) for x in self.queue_file.read_text(encoding="utf-8").splitlines() if x.strip()]

    def field_pack_manifest(self,site_id,boundary):
        return {"version":1,"site_id":str(site_id),"boundary":boundary,
                "layers":["boundary","osm-vector","dem","roads","villages","nh-sh","geology-references","previous-surveys","route-candidates"],
                "formats":["pmtiles","geojson","kml","geotiff"],"google_content_cached":False,
                "created_at":time.time()}
