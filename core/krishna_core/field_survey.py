from __future__ import annotations

import json
import math
from pathlib import Path
import time
import uuid
from xml.sax.saxutils import escape

EARTH_R=6371008.8


class FieldSurveyEngine:
    """Deterministic field geometry and evidence-gated survey calculations."""

    def __init__(self,state_root):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.history_file=self.root/"survey-history.jsonl"

    @staticmethod
    def _point(value):
        if isinstance(value,dict):
            lat=value.get("lat");lon=value.get("lon",value.get("lng"))
        elif isinstance(value,(list,tuple)) and len(value)>=2:
            lat,lon=value[0],value[1]
        else:raise ValueError("point must contain lat/lon")
        lat=float(lat);lon=float(lon)
        if not -90<=lat<=90 or not -180<=lon<=180:raise ValueError("invalid latitude/longitude")
        return {"lat":lat,"lon":lon}

    @classmethod
    def boundary(cls,points):
        rows=[cls._point(x) for x in points or []]
        if len(rows)<3:raise ValueError("boundary requires at least 3 points")
        return rows

    @staticmethod
    def haversine(a,b):
        p1=math.radians(a["lat"]);p2=math.radians(b["lat"])
        dp=p2-p1;dl=math.radians(b["lon"]-a["lon"])
        h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2*EARTH_R*math.asin(min(1,math.sqrt(h)))

    @classmethod
    def metrics(cls,points):
        pts=cls.boundary(points)
        lat0=sum(x["lat"] for x in pts)/len(pts)
        lon0=sum(x["lon"] for x in pts)/len(pts)
        c=math.cos(math.radians(lat0))
        xy=[(math.radians(p["lon"]-lon0)*EARTH_R*c,math.radians(p["lat"]-lat0)*EARTH_R) for p in pts]
        twice=0.0
        for i,(x1,y1) in enumerate(xy):
            x2,y2=xy[(i+1)%len(xy)]
            twice+=x1*y2-x2*y1
        area=abs(twice)/2.0
        perimeter=sum(cls.haversine(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts)))
        return {
            "boundary":pts,
            "centroid":{"lat":lat0,"lon":lon0},
            "area_m2":area,
            "area_hectares":area/10000.0,
            "perimeter_m":perimeter,
            "evidence_state":"MEASURED",
            "method":"local equirectangular polygon projection; suitable for bounded field sites",
        }

    @classmethod
    def contains(cls,points,point):
        pts=cls.boundary(points);p=cls._point(point)
        x=p["lon"];y=p["lat"];inside=False
        j=len(pts)-1
        for i in range(len(pts)):
            xi,yi=pts[i]["lon"],pts[i]["lat"];xj,yj=pts[j]["lon"],pts[j]["lat"]
            if ((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/((yj-yi) or 1e-15)+xi):inside=not inside
            j=i
        return {"inside":inside,"point":p,"evidence_state":"MEASURED"}

    @classmethod
    def volume_estimate(cls,points,depth_samples):
        m=cls.metrics(points)
        values=[]
        states=[]
        for row in depth_samples or []:
            if isinstance(row,dict):
                value=row.get("depth_m",row.get("height_m"))
                state=str(row.get("evidence_state") or "UNKNOWN").upper()
            else:
                value=row;state="UNKNOWN"
            try:value=float(value)
            except (TypeError,ValueError):continue
            if value<0:continue
            values.append(value);states.append(state)
        if not values:
            return {**m,"volume_m3":None,"average_depth_m":None,"evidence_state":"UNKNOWN",
                    "reason":"depth/height evidence is required; camera-only volume is not reported as measured"}
        avg=sum(values)/len(values)
        state="MEASURED" if states and all(x=="MEASURED" for x in states) else "INFERRED"
        return {**m,"average_depth_m":avg,"sample_count":len(values),"volume_m3":m["area_m2"]*avg,
                "evidence_state":state,
                "note":"Volume is polygon area × supplied average visible depth/height; subsurface reserve quantity is not inferred."}

    @staticmethod
    def assess_route(segments,vehicle=None):
        rows=[];unknown=0
        for i,seg in enumerate(segments or []):
            if not isinstance(seg,dict):continue
            width=seg.get("width_m");slope=seg.get("slope_pct");clearance=seg.get("clearance_m")
            try:width=float(width) if width is not None else None
            except (TypeError,ValueError):width=None
            try:slope=abs(float(slope)) if slope is not None else None
            except (TypeError,ValueError):slope=None
            try:clearance=float(clearance) if clearance is not None else None
            except (TypeError,ValueError):clearance=None
            issues=[]
            if width is None:issues.append("road width unknown")
            if slope is None:issues.append("slope unknown")
            if clearance is None:issues.append("vertical clearance unknown")
            if seg.get("bridge_load_verified") is False:issues.append("bridge/load capacity unverified")
            score=1.0
            if width is not None and width<3.0:score-=0.35
            if slope is not None and slope>12.0:score-=0.30
            if clearance is not None and clearance<4.2:score-=0.30
            if issues:score-=min(0.35,0.08*len(issues))
            if issues:unknown+=1
            rows.append({"segment":seg.get("id") or i,"score":max(0.0,min(1.0,score)),
                         "issues":issues,"evidence_state":"MEASURED" if not issues else "UNKNOWN"})
        return {
            "vehicle":vehicle or {},
            "segments":rows,
            "route_score":min((x["score"] for x in rows),default=0.0),
            "evidence_state":"MEASURED" if rows and unknown==0 else "UNKNOWN",
            "note":"This is evidence-based route screening, not a legal/engineering certification of heavy-vehicle access.",
        }

    @classmethod
    def geojson(cls,site_id,points,properties=None):
        pts=cls.boundary(points)
        ring=[[p["lon"],p["lat"]] for p in pts]+[[pts[0]["lon"],pts[0]["lat"]]]
        return {"type":"FeatureCollection","features":[{"type":"Feature","properties":{"site_id":str(site_id),**dict(properties or {})},
                "geometry":{"type":"Polygon","coordinates":[ring]}}]}

    @classmethod
    def kml(cls,site_id,points):
        pts=cls.boundary(points)
        coords=" ".join(f'{p["lon"]},{p["lat"]},0' for p in pts+[pts[0]])
        name=escape(str(site_id))
        return f'''<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>{name}</name><Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>'''

    def record(self,site_id,kind,payload):
        row={"id":str(uuid.uuid4()),"site_id":str(site_id),"kind":str(kind),"at":time.time(),"payload":payload}
        with self.history_file.open("a",encoding="utf-8") as f:f.write(json.dumps(row,separators=(",",":"))+"\n")
        return row

    def history(self,site_id=None,limit=100):
        if not self.history_file.exists():return []
        rows=[json.loads(x) for x in self.history_file.read_text(encoding="utf-8").splitlines() if x.strip()]
        if site_id is not None:rows=[x for x in rows if x.get("site_id")==str(site_id)]
        return rows[-max(1,min(int(limit),1000)):]
