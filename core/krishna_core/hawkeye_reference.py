from __future__ import annotations

from pathlib import Path
import csv
import io
import json
import math
import re
import time


class HawkeyeReferenceRegistry:
    """Verified schematic/boardview/netlist references with camera affine registration."""

    KINDS={"schematic","boardview","netlist","service-manual"}

    def __init__(self,state_dir):
        self.state_dir=Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _safe(value):
        out="".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
        if not out:raise ValueError("invalid reference_id")
        return out

    def _path(self,reference_id):
        return self.state_dir/(self._safe(reference_id)+".json")

    @staticmethod
    def _point(value):
        if isinstance(value,dict):value=[value.get("x"),value.get("y")]
        if not isinstance(value,(list,tuple)) or len(value)!=2:raise ValueError("point must be [x,y]")
        return [float(value[0]),float(value[1])]

    def parse_source(self,kind,source_text):
        raw=str(source_text or "").strip()
        if not raw:raise ValueError("reference source is empty")
        if raw.startswith("{"):
            obj=json.loads(raw)
            if not isinstance(obj,dict):raise ValueError("reference JSON must be an object")
            return obj
        components=[];nets=[]
        for row in csv.reader(io.StringIO(raw)):
            if not row or str(row[0]).strip().startswith("#"):continue
            tag=str(row[0]).strip().upper()
            if tag in {"COMPONENT","PART"} and len(row)>=5:
                components.append({"id":str(row[1]).strip(),"label":str(row[2]).strip(),
                                   "x":float(row[3]),"y":float(row[4]),
                                   "kind":str(row[5]).strip() if len(row)>5 else "component"})
            elif tag in {"NET","EDGE","CONNECTION"} and len(row)>=3:
                nets.append({"from":str(row[1]).strip(),"to":str(row[2]).strip(),
                             "label":str(row[3]).strip() if len(row)>3 else "net"})
        if not components:raise ValueError("reference text did not contain parseable components")
        return {"components":components,"nets":nets}

    def register(self,reference_id,kind,data,*,verified=False,source_name=""):
        rid=self._safe(reference_id);kind=str(kind or "").strip().lower()
        if kind not in self.KINDS:raise ValueError("unsupported reference kind")
        if not isinstance(data,dict):raise ValueError("reference data must be an object")
        components=[];ids=set()
        for row in data.get("components") or []:
            if not isinstance(row,dict):continue
            cid=re.sub(r"[^A-Za-z0-9_.:-]","_",str(row.get("id") or "").strip())
            if not cid or cid in ids:continue
            x=float(row.get("x"));y=float(row.get("y"));ids.add(cid)
            components.append({"id":cid,"label":str(row.get("label") or cid)[:120],
                               "kind":str(row.get("kind") or "component")[:80],"x":x,"y":y,
                               "size":max(0.005,min(0.15,float(row.get("size") or 0.025)))})
            if len(components)>=1000:break
        if len(components)<3:raise ValueError("verified reference requires at least 3 components")
        nets=[]
        for row in data.get("nets") or data.get("flows") or []:
            if not isinstance(row,dict):continue
            a=str(row.get("from") or "").strip();b=str(row.get("to") or "").strip()
            if a in ids and b in ids and a!=b:
                nets.append({"from":a,"to":b,"label":str(row.get("label") or "net")[:100]})
            if len(nets)>=4000:break
        record={"reference_id":rid,"kind":kind,"verified":bool(verified),"source_name":str(source_name or "")[:240],
                "components":components,"nets":nets,"created_at":time.time()}
        self._path(rid).write_text(json.dumps(record,indent=2,sort_keys=True),encoding="utf-8")
        return {"reference_id":rid,"kind":kind,"verified":bool(verified),"component_count":len(components),"net_count":len(nets)}

    def register_source(self,reference_id,kind,source_text,*,verified=False,source_name=""):
        return self.register(reference_id,kind,self.parse_source(kind,source_text),verified=verified,source_name=source_name)

    def get(self,reference_id):
        p=self._path(reference_id)
        if not p.exists():raise KeyError(reference_id)
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _solve3(a,b):
        m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
        for col in range(3):
            pivot=max(range(col,3),key=lambda r:abs(m[r][col]))
            if abs(m[pivot][col])<1e-12:raise ValueError("registration anchors are degenerate")
            m[col],m[pivot]=m[pivot],m[col]
            div=m[col][col];m[col]=[v/div for v in m[col]]
            for r in range(3):
                if r==col:continue
                f=m[r][col];m[r]=[m[r][c]-f*m[col][c] for c in range(4)]
        return [m[i][3] for i in range(3)]

    @classmethod
    def _affine(cls,anchors):
        if not isinstance(anchors,list) or len(anchors)<3:raise ValueError("at least 3 registration anchors are required")
        rows=[];bx=[];by=[]
        for item in anchors[:32]:
            if not isinstance(item,dict):continue
            r=cls._point(item.get("reference"));q=cls._point(item.get("image"))
            rows.append([r[0],r[1],1.0]);bx.append(q[0]);by.append(q[1])
        if len(rows)<3:raise ValueError("at least 3 valid anchors are required")
        ata=[[sum(row[i]*row[j] for row in rows) for j in range(3)] for i in range(3)]
        atx=[sum(rows[k][i]*bx[k] for k in range(len(rows))) for i in range(3)]
        aty=[sum(rows[k][i]*by[k] for k in range(len(rows))) for i in range(3)]
        ax=cls._solve3(ata,atx);ay=cls._solve3(ata,aty)
        residual=0.0
        for row,x,y in zip(rows,bx,by):
            px=sum(ax[i]*row[i] for i in range(3));py=sum(ay[i]*row[i] for i in range(3))
            residual+=math.hypot(px-x,py-y)**2
        rms=math.sqrt(residual/len(rows))
        return ax,ay,rms

    def overlay(self,reference_id,anchors):
        ref=self.get(reference_id)
        if not ref.get("verified"):raise PermissionError("reference is not verified")
        ax,ay,rms=self._affine(anchors)
        def tx(x,y):return [sum(ax[i]*v for i,v in enumerate((x,y,1.0))),sum(ay[i]*v for i,v in enumerate((x,y,1.0)))]
        comps=[];lookup={}
        for row in ref["components"]:
            p=tx(float(row["x"]),float(row["y"]));x=max(0.0,min(1.0,p[0]));y=max(0.0,min(1.0,p[1]))
            size=float(row.get("size") or 0.025);box=[max(0,x-size/2),max(0,y-size/2),min(size,1-x+size/2),min(size,1-y+size/2)]
            item={"id":row["id"],"label":row["label"],"kind":row["kind"],"bbox":[round(v,5) for v in box],"confidence":1.0}
            comps.append(item);lookup[row["id"]]=item
        flows=[{"from":n["from"],"to":n["to"],"label":n["label"],"evidence_state":"MEASURED","confidence":1.0}
               for n in ref.get("nets") or [] if n["from"] in lookup and n["to"] in lookup]
        return {"schema":"hawkeye.diagnostic-overlay.v1","coordinate_space":"normalized-original-frame",
                "reference_id":ref["reference_id"],"reference_kind":ref["kind"],"reference_verified":True,
                "registration_rms":rms,"diagram_mode":"reference-aligned",
                "accuracy_note":"Verified reference geometry registered to the camera by supplied anchors; registration error is reported separately.",
                "components":comps,"flows":flows,"test_points":[]}

    def status(self):
        rows=list(self.state_dir.glob("*.json"))
        return {"reference_count":len(rows),"supported_kinds":sorted(self.KINDS),"registration":"least-squares affine, >=3 anchors","ready":True}
