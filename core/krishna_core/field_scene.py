from __future__ import annotations

"""Offline-first 3D/AR field-scene assembly for HAWKEYE/BHOOMIPUTRA.

This module fuses already-normalized measured GNSS/depth evidence and optional
photogrammetry artifacts into a deterministic scene manifest. It does not invent
terrain, depth, quarry volume or survey accuracy when measurements are absent.
"""

from pathlib import Path
import hashlib
import json
import math
import time
import uuid


def _finite(value, name):
    try:
        out=float(value)
    except (TypeError,ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _fingerprint(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class FieldSceneBuilder:
    VERSION="field-scene-v1"

    def __init__(self,state_root):
        self.root=Path(state_root).resolve()
        self.scenes=self.root/"field-scenes"
        self.scenes.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _point(sample):
        if not isinstance(sample,dict):
            raise ValueError("GNSS scene point must be an object")
        lat=_finite(sample.get("lat"),"lat")
        lon=_finite(sample.get("lon"),"lon")
        if not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError("GNSS coordinate outside valid range")
        alt=sample.get("altitude_m")
        alt=None if alt in (None,"") else _finite(alt,"altitude_m")
        state=str(sample.get("evidence_state") or "UNKNOWN").upper()
        return {
            "lat":lat,"lon":lon,"altitude_m":alt,
            "accuracy_m":sample.get("accuracy_m"),
            "fix_type":sample.get("fix_type"),
            "evidence_state":state,
            "fingerprint":sample.get("fingerprint"),
        }

    def build(self,site_id,gnss_points,*,depth=None,photogrammetry=None,anchors=None,metadata=None):
        points=[self._point(x) for x in (gnss_points or [])]
        measured=[x for x in points if x["evidence_state"]=="MEASURED"]
        if not measured:
            raise ValueError("field scene requires at least one MEASURED GNSS point")
        center={
            "lat":sum(x["lat"] for x in measured)/len(measured),
            "lon":sum(x["lon"] for x in measured)/len(measured),
            "altitude_m":(
                sum(x["altitude_m"] for x in measured if x["altitude_m"] is not None)/
                max(1,len([x for x in measured if x["altitude_m"] is not None]))
                if any(x["altitude_m"] is not None for x in measured) else None
            ),
        }
        depth=dict(depth or {})
        depth_measured=str(depth.get("evidence_state") or "").upper()=="MEASURED"
        photo=dict(photogrammetry or {})
        photo_path=photo.get("output_dir")
        photo_available=bool(photo.get("completed")) and bool(photo_path) and Path(photo_path).exists()
        anchor_rows=[]
        for i,row in enumerate(anchors or []):
            if not isinstance(row,dict):continue
            anchor_rows.append({
                "id":str(row.get("id") or f"anchor-{i+1}"),
                "label":str(row.get("label") or "")[:160],
                "lat":_finite(row.get("lat"),f"anchors[{i}].lat"),
                "lon":_finite(row.get("lon"),f"anchors[{i}].lon"),
                "altitude_m":None if row.get("altitude_m") in (None,"") else _finite(row.get("altitude_m"),f"anchors[{i}].altitude_m"),
                "source_ref":str(row.get("source_ref") or "")[:240] or None,
            })
        scene_id="SCENE-"+uuid.uuid4().hex[:20]
        payload={
            "schema":"krishna.field-scene.v1",
            "version":self.VERSION,
            "scene_id":scene_id,
            "site_id":str(site_id),
            "created_at":time.time(),
            "center":center,
            "gnss":{"points":points,"measured_count":len(measured)},
            "depth":{
                "available":depth_measured,
                "summary":depth.get("summary") if depth_measured else None,
                "survey_grade":bool(depth.get("survey_grade",False)) if depth_measured else False,
                "measurement_id":depth.get("measurement_id") if depth_measured else None,
            },
            "photogrammetry":{
                "available":photo_available,
                "output_dir":str(Path(photo_path).resolve()) if photo_available else None,
                "job_id":photo.get("job_id") if photo_available else None,
                "verification_required":bool(photo.get("verification_required",True)) if photo else True,
            },
            "anchors":anchor_rows,
            "render":{
                "maplibre":True,
                "cesium":True,
                "ar_anchor_packet":True,
                "survey_mesh":photo_available,
            },
            "metadata":dict(metadata or {}),
            "limitations":[],
        }
        if not depth_measured:
            payload["limitations"].append("no measured depth evidence; 3D vertical geometry is not survey-measured")
        if not photo_available:
            payload["limitations"].append("no verified photogrammetry output; scene uses GNSS/declared anchors only")
        if not all(x.get("accuracy_m") not in (None,"") for x in measured):
            payload["limitations"].append("one or more GNSS points lack reported horizontal accuracy")
        payload["fingerprint"]=_fingerprint({k:v for k,v in payload.items() if k!="fingerprint"})
        scene_dir=self.scenes/scene_id
        scene_dir.mkdir(parents=True,exist_ok=True)
        (scene_dir/"scene.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
        features=[]
        for x in points:
            coords=[x["lon"],x["lat"]]
            if x["altitude_m"] is not None:coords.append(x["altitude_m"])
            features.append({"type":"Feature","geometry":{"type":"Point","coordinates":coords},"properties":{
                "evidence_state":x["evidence_state"],"fix_type":x["fix_type"],"accuracy_m":x["accuracy_m"]}})
        for x in anchor_rows:
            coords=[x["lon"],x["lat"]]
            if x["altitude_m"] is not None:coords.append(x["altitude_m"])
            features.append({"type":"Feature","geometry":{"type":"Point","coordinates":coords},"properties":{
                "kind":"ar_anchor","id":x["id"],"label":x["label"],"source_ref":x["source_ref"]}})
        geo={"type":"FeatureCollection","features":features}
        (scene_dir/"scene.geojson").write_text(json.dumps(geo,indent=2),encoding="utf-8")
        return {"path":str(scene_dir),"scene":payload,"geojson":str(scene_dir/"scene.geojson")}

    def ar_packet(self,scene):
        data=scene.get("scene") if isinstance(scene,dict) and "scene" in scene else scene
        if not isinstance(data,dict) or not data.get("center"):
            raise ValueError("valid scene is required")
        return {
            "schema":"krishna.ar-anchor-packet.v1",
            "scene_id":data.get("scene_id"),
            "origin":data["center"],
            "anchors":list(data.get("anchors") or []),
            "tracking":"device-adapter-required",
            "hardware_verified":False,
            "policy":"AR placement is visualization until device tracking/depth calibration is accepted on real hardware",
        }

    def status(self):
        return {
            "component":"HAWKEYE/BHOOMIPUTRA Field Scene",
            "version":self.VERSION,
            "software_ready":True,
            "inputs":["MEASURED GNSS","optional MEASURED depth","optional verified photogrammetry","explicit anchors"],
            "outputs":["scene.json","scene.geojson","AR anchor packet"],
            "hardware_verified":False,
        }
