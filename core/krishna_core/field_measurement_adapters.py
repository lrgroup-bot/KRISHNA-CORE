from __future__ import annotations

"""Evidence-gated field measurement adapters for HAWKEYE/BHOOMIPUTRA.

These adapters normalize measurements supplied by real devices or trusted import
boundaries. They never fabricate RTK/depth/photogrammetry measurements and never
upgrade an inferred value to MEASURED without the required device evidence.
"""

from dataclasses import dataclass
from pathlib import Path
from statistics import median
from urllib.parse import urlparse
import hashlib
import json
import math
import os
import shlex
import subprocess
import time
import uuid


def _finite(value, name):
    try:
        out=float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _fingerprint(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class GnssRtkAdapter:
    FIXES={"unknown","gps","dgps","sbas","rtk_float","rtk_fixed"}

    def normalize(self, sample):
        if not isinstance(sample,dict):
            raise ValueError("GNSS sample must be an object")
        lat=_finite(sample.get("lat"),"lat")
        lon=_finite(sample.get("lon"),"lon")
        if not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError("GNSS coordinate outside valid range")
        accuracy=sample.get("accuracy_m")
        accuracy=None if accuracy in (None,"") else max(0.0,_finite(accuracy,"accuracy_m"))
        altitude=sample.get("altitude_m")
        altitude=None if altitude in (None,"") else _finite(altitude,"altitude_m")
        fix=str(sample.get("fix_type") or "unknown").strip().lower()
        if fix not in self.FIXES:
            raise ValueError("unsupported GNSS fix_type")
        device_id=str(sample.get("device_id") or "").strip()
        captured_raw=sample.get("captured_at")
        captured_at=_finite(time.time() if captured_raw in (None,"") else captured_raw,"captured_at")
        rtk=fix in {"rtk_float","rtk_fixed"}
        row={
            "measurement_id":"GNSS-"+uuid.uuid4().hex[:20],
            "stream":"GNSS",
            "lat":lat,"lon":lon,"altitude_m":altitude,"accuracy_m":accuracy,
            "fix_type":fix,
            "rtk":rtk,
            "rtk_fixed":fix=="rtk_fixed",
            "device_id":device_id or None,
            "captured_at":captured_at,
            "evidence_state":"MEASURED",
            "limitations":[],
        }
        if rtk and not device_id:
            row["limitations"].append("RTK fix was supplied without a device identifier; provenance remains incomplete")
        if accuracy is None:
            row["limitations"].append("horizontal accuracy was not supplied")
        row["fingerprint"]=_fingerprint({k:v for k,v in row.items() if k not in {"measurement_id","fingerprint"}})
        return row


class DepthMeasurementAdapter:
    def normalize(self, samples, *, device_id="", calibration_ref="", captured_at=None):
        if not isinstance(samples,list) or not samples:
            return {
                "stream":"DEPTH","evidence_state":"UNKNOWN","sample_count":0,
                "measurements":[],"summary":None,
                "limitations":["no measured depth samples supplied"],
            }
        rows=[]
        for idx,item in enumerate(samples):
            if isinstance(item,(int,float)):
                value=_finite(item,f"depth[{idx}]")
                item={"depth_m":value}
            if not isinstance(item,dict):
                raise ValueError("depth samples must be numeric values or objects")
            key="depth_m" if item.get("depth_m") not in (None,"") else "distance_m"
            if item.get(key) in (None,""):
                raise ValueError("each depth sample requires depth_m or distance_m")
            value=max(0.0,_finite(item.get(key),f"{key}[{idx}]"))
            row={
                "index":idx,
                key:value,
                "x":item.get("x"),
                "y":item.get("y"),
                "lat":item.get("lat"),
                "lon":item.get("lon"),
                "confidence":max(0.0,min(_finite(item.get("confidence",1.0),f"confidence[{idx}]"),1.0)),
            }
            rows.append(row)
        values=[float(x.get("depth_m",x.get("distance_m"))) for x in rows]
        result={
            "measurement_id":"DEPTH-"+uuid.uuid4().hex[:20],
            "stream":"DEPTH",
            "evidence_state":"MEASURED",
            "sample_count":len(rows),
            "measurements":rows,
            "summary":{
                "min_m":min(values),"max_m":max(values),
                "median_m":median(values),"mean_m":sum(values)/len(values),
            },
            "device_id":str(device_id or "").strip() or None,
            "calibration_ref":str(calibration_ref or "").strip() or None,
            "captured_at":_finite(time.time() if captured_at in (None,"") else captured_at,"captured_at"),
            "limitations":[],
        }
        if not result["device_id"]:
            result["limitations"].append("depth device identifier missing")
        if not result["calibration_ref"]:
            result["limitations"].append("calibration/reference evidence missing; measurements are retained but not treated as survey-grade")
        result["survey_grade"]=bool(result["device_id"] and result["calibration_ref"])
        result["fingerprint"]=_fingerprint({k:v for k,v in result.items() if k not in {"measurement_id","fingerprint"}})
        return result


@dataclass(frozen=True)
class PhotogrammetryPlan:
    provider:str
    configured:bool
    executable:str|None
    input_dir:str
    output_dir:str
    options:dict


class PhotogrammetryWorkerAdapter:
    """Optional local worker boundary for OpenDroneMap/NodeODM-style jobs.

    The configured command is owner/runtime configuration, not user text. KRISHNA
    passes one generated JSON job file as the only argument. The worker is not
    reported active until the executable exists.
    """

    ENV="KRISHNA_PHOTOGRAMMETRY_CMD"

    def __init__(self, runtime_root):
        self.root=Path(runtime_root)
        self.jobs=self.root/"photogrammetry-jobs"
        self.jobs.mkdir(parents=True,exist_ok=True)

    def _command(self):
        raw=str(os.getenv(self.ENV) or "").strip()
        if not raw:
            return []
        argv=shlex.split(raw,posix=(os.name!="nt"))
        if not argv:
            return []
        exe=Path(argv[0]).expanduser()
        if not exe.is_absolute() or not exe.is_file():
            return []
        return [str(exe),*argv[1:]]

    def status(self):
        argv=self._command()
        return {
            "provider":"opendronemap-compatible-worker",
            "configured":bool(argv),
            "executable":argv[0] if argv else None,
            "environment":self.ENV,
            "authority":"optional local worker only; no photogrammetry result exists until a configured worker completes and outputs are verified",
        }

    def plan(self,input_dir,output_dir,options=None):
        inp=Path(input_dir).resolve(); out=Path(output_dir).resolve()
        if not inp.is_dir():
            raise FileNotFoundError(str(inp))
        opts=dict(options or {})
        return PhotogrammetryPlan(
            "opendronemap-compatible-worker",bool(self._command()),
            self._command()[0] if self._command() else None,
            str(inp),str(out),opts,
        )

    def run(self,input_dir,output_dir,options=None,*,timeout=7200):
        argv=self._command()
        if not argv:
            raise RuntimeError(
                "photogrammetry worker is not configured; set KRISHNA_PHOTOGRAMMETRY_CMD to an absolute local worker executable"
            )
        plan=self.plan(input_dir,output_dir,options)
        job_id="PHOTO-"+uuid.uuid4().hex[:20]
        job_file=self.jobs/(job_id+".json")
        payload={
            "schema":"krishna.photogrammetry-job.v1",
            "job_id":job_id,
            "input_dir":plan.input_dir,
            "output_dir":plan.output_dir,
            "options":plan.options,
            "requested_at":time.time(),
        }
        job_file.write_text(json.dumps(payload,indent=2),encoding="utf-8")
        started=time.time()
        proc=subprocess.run(
            [*argv,str(job_file)],capture_output=True,text=True,
            timeout=max(30,int(timeout)),shell=False,
        )
        result={
            "job_id":job_id,"provider":plan.provider,
            "returncode":proc.returncode,"completed":proc.returncode==0,
            "duration_s":round(time.time()-started,3),
            "output_dir":plan.output_dir,
            "stdout_tail":(proc.stdout or "")[-4000:],
            "stderr_tail":(proc.stderr or "")[-4000:],
            "evidence_state":"MEASURED" if proc.returncode==0 else "UNKNOWN",
            "verification_required":True,
        }
        (self.jobs/(job_id+"-result.json")).write_text(json.dumps(result,indent=2),encoding="utf-8")
        if proc.returncode!=0:
            raise RuntimeError("photogrammetry worker failed: "+result["stderr_tail"][-1000:])
        return result


class FieldMeasurementAdapters:
    def __init__(self,runtime_root):
        self.gnss=GnssRtkAdapter()
        self.depth=DepthMeasurementAdapter()
        self.photogrammetry=PhotogrammetryWorkerAdapter(runtime_root)

    def status(self):
        return {
            "component":"HAWKEYE Field Measurement Adapters",
            "gnss_rtk":{"implemented":True,"physical_device_verified":False},
            "depth":{"implemented":True,"physical_device_verified":False},
            "photogrammetry":self.photogrammetry.status(),
            "policy":"software adapters normalize supplied measurements; physical device/provider claims remain HARDWARE_UNVERIFIED until accepted on real equipment",
        }
