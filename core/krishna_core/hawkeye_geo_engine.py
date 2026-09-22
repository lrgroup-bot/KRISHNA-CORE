"""Provider-neutral Hawkeye geospatial fusion and field-pack planner."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,time

from .field_survey import FieldSurveyEngine

@dataclass(frozen=True)
class GeoLayer:
 name:str; provider:str; kind:str; offline:bool; analysis:bool; license_mode:str

LAYERS=(
 GeoLayer("base-vector","openstreetmap","vector",True,True,"open-data"),
 GeoLayer("offline-tiles","pmtiles","vector-raster-dem",True,True,"open-format"),
 GeoLayer("mobile-renderer","maplibre","renderer",True,True,"open-source"),
 GeoLayer("earth-3d","cesiumjs","3d-renderer",True,True,"open-source"),
 GeoLayer("street-imagery","kartaview","street",False,True,"provider-terms"),
 GeoLayer("photogrammetry","opendronemap","ortho-dem-pointcloud-mesh",True,True,"open-source"),
 GeoLayer("india-eo","bhuvan","imagery-thematic",False,True,"dataset-terms"),
 GeoLayer("google-map","google-maps","visualization",False,False,"licensed"),
 GeoLayer("google-street","google-streetview","visualization",False,False,"licensed"),
 GeoLayer("google-3d","google-3d-tiles","visualization",False,False,"licensed"),
)

class HawkeyeGeoEngine:
 def __init__(self,state_root):
  self.root=Path(state_root);self.root.mkdir(parents=True,exist_ok=True)
  self.survey=FieldSurveyEngine(self.root/"survey")
 def catalog(self):return [asdict(x) for x in LAYERS]
 def analysis_layers(self):return [asdict(x) for x in LAYERS if x.analysis]
 def unified_view(self,lat,lon):
  return {"center":{"lat":float(lat),"lon":float(lon)},"modes":["MAP","SATELLITE","STREET","TERRAIN","3D_EARTH","3D_SURVEY","AR","HISTORY"],
          "analysis_policy":"Google layers are visualization-only; analysis uses licensed/open analytical sources.",
          "layers":self.catalog()}
 def make_field_pack(self,site_id,boundary):
  d=self.root/"packs"/str(site_id);d.mkdir(parents=True,exist_ok=True)
  manifest={"version":1,"site_id":str(site_id),"boundary":boundary,"created_at":time.time(),
   "required":["boundary.geojson","base.pmtiles","dem.pmtiles","roads.geojson","villages.geojson","nh-sh.geojson"],
   "optional":["geology.geojson","previous-surveys.json","route-candidates.geojson","survey-model.glb"],
   "renderers":["maplibre","cesiumjs"],"analysis":["osm","dem","hawkeye-survey","opendronemap"],
   "google_cached":False}
  (d/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
  return {"path":str(d),"manifest":manifest}

 def survey_metrics(self,site_id,boundary,record=True):
  out=self.survey.metrics(boundary)
  if record:self.survey.record(site_id,"boundary_metrics",out)
  return out

 def geofence(self,boundary,point):
  return self.survey.contains(boundary,point)

 def volume_estimate(self,site_id,boundary,depth_samples,record=True):
  out=self.survey.volume_estimate(boundary,depth_samples)
  if record:self.survey.record(site_id,"visible_volume",out)
  return out

 def route_assessment(self,site_id,segments,vehicle=None,record=True):
  out=self.survey.assess_route(segments,vehicle)
  if record:self.survey.record(site_id,"route_assessment",out)
  return out

 def export_boundary(self,site_id,boundary,fmt="geojson"):
  fmt=str(fmt or "geojson").lower()
  if fmt=="geojson":return {"format":"geojson","data":self.survey.geojson(site_id,boundary)}
  if fmt=="kml":return {"format":"kml","data":self.survey.kml(site_id,boundary)}
  raise ValueError("format must be geojson or kml")

 def history(self,site_id=None,limit=100):
  return self.survey.history(site_id,limit)
