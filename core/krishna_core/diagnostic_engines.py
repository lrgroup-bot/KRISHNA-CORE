from __future__ import annotations

import math
import os
import shlex
import subprocess
from dataclasses import dataclass


def _f(value):
    try:return float(value)
    except (TypeError,ValueError):return None


def _bounded_text(value,limit=240):
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class AdapterStatus:
    id: str
    configured: bool
    read_only: bool
    evidence: str
    note: str

    def as_dict(self):
        return {
            "id":self.id,"configured":self.configured,"read_only":self.read_only,
            "evidence":self.evidence,"note":self.note,
        }


class ReadOnlyCommandAdapter:
    """Owner-configured diagnostic reader. No command is accepted from the model/user."""

    def __init__(self,adapter_id,env_var):
        self.adapter_id=adapter_id
        self.env_var=env_var

    def status(self):
        configured=bool(os.getenv(self.env_var,"").strip())
        return AdapterStatus(
            self.adapter_id,configured,True,"MEASURED" if configured else "UNKNOWN",
            f"configured by {self.env_var}" if configured else f"{self.env_var} is not configured",
        ).as_dict()

    def read(self,timeout=20):
        raw=os.getenv(self.env_var,"").strip()
        if not raw:raise RuntimeError(f"{self.env_var} is not configured")
        args=shlex.split(raw,posix=(os.name!="nt"))
        if not args:raise RuntimeError("diagnostic reader command is empty")
        completed=subprocess.run(args,capture_output=True,text=True,timeout=max(1,min(int(timeout),60)),shell=False)
        if completed.returncode!=0:
            raise RuntimeError(f"{self.adapter_id} reader failed: "+_bounded_text(completed.stderr,400))
        return _bounded_text(completed.stdout,12000)


class ElectronicsDiagnosticEngine:
    ID="electronics"
    def status(self):
        return {"id":self.ID,"mode":"reference + instrument evidence","read_only":True,"ready":True}

    def evaluate(self,context):
        measurements=context.get("measurements") or []
        expected=context.get("expected_ranges") or {}
        findings=[]
        used=0
        for row in measurements[:64] if isinstance(measurements,list) else []:
            if not isinstance(row,dict):continue
            name=_bounded_text(row.get("name") or row.get("test_point"),80)
            value=_f(row.get("value"))
            unit=_bounded_text(row.get("unit"),24)
            if not name or value is None:continue
            used+=1
            finding={"test_point":name,"value":value,"unit":unit,"evidence_state":"MEASURED","status":"measured"}
            exp=expected.get(name) if isinstance(expected,dict) else None
            if isinstance(exp,dict):
                low=_f(exp.get("min"));high=_f(exp.get("max"))
                finding["expected"]={"min":low,"max":high,"unit":_bounded_text(exp.get("unit") or unit,24)}
                if low is not None and value<low:finding["status"]="below_expected_range"
                elif high is not None and value>high:finding["status"]="above_expected_range"
                elif low is not None or high is not None:finding["status"]="within_expected_range"
            findings.append(finding)
        return {
            "engine":"ElectronicsDiagnosticEngine","evidence_state":"MEASURED" if used else "UNKNOWN",
            "measurements_used":used,"findings":findings,
            "limits":["no hidden voltage/current/value is inferred","expected ranges must come from supplied verified reference/service data"],
        }


class VehicleDiagnosticEngine:
    ID="vehicle"
    def __init__(self):
        self.obd=ReadOnlyCommandAdapter("obd2-read","KRISHNA_OBD_READ_CMD")
        self.j1939=ReadOnlyCommandAdapter("j1939-read","KRISHNA_J1939_READ_CMD")

    def status(self):
        return {"id":self.ID,"read_only":True,"obd":self.obd.status(),"j1939":self.j1939.status(),
                "auto_transmit":False,"ecu_programming":False}

    def evaluate(self,context):
        dtcs=context.get("dtcs") or context.get("diagnostic_trouble_codes") or []
        telemetry=context.get("vehicle_telemetry") or {}
        observed=[]
        if isinstance(dtcs,(list,tuple)):
            for code in dtcs[:64]:
                value=_bounded_text(code,32).upper()
                if value:observed.append({"kind":"dtc","code":value,"evidence_state":"MEASURED"})
        if isinstance(telemetry,dict):
            for key,value in list(telemetry.items())[:64]:
                num=_f(value)
                observed.append({"kind":"telemetry","name":_bounded_text(key,80),"value":num if num is not None else _bounded_text(value,120),"evidence_state":"MEASURED"})
        return {
            "engine":"VehicleDiagnosticEngine","evidence_state":"MEASURED" if observed else "UNKNOWN",
            "observations":observed,"provider_status":self.status(),
            "limits":["DTC/telemetry evidence does not by itself prove the failed part","no CAN transmission or ECU programming"],
        }


class AcousticDiagnosticEngine:
    ID="acoustic"
    def status(self):
        return {"id":self.ID,"mode":"baseline feature comparison","read_only":True,"ready":True}

    def evaluate(self,context):
        baseline=context.get("acoustic_baseline") or {}
        current=context.get("acoustic_features") or {}
        changes=[]
        if isinstance(baseline,dict) and isinstance(current,dict):
            for key in sorted(set(baseline)&set(current))[:64]:
                b=_f(baseline.get(key));c=_f(current.get(key))
                if b is None or c is None:continue
                delta=c-b
                ratio=(delta/abs(b)) if abs(b)>1e-12 else None
                changes.append({
                    "feature":_bounded_text(key,80),"baseline":b,"current":c,"delta":delta,
                    "relative_change":ratio,"evidence_state":"MEASURED",
                })
        largest=sorted(changes,key=lambda x:abs(x["relative_change"]) if x["relative_change"] is not None else abs(x["delta"]),reverse=True)[:8]
        return {
            "engine":"AcousticDiagnosticEngine","evidence_state":"MEASURED" if changes else "UNKNOWN",
            "feature_changes":largest,
            "limits":["feature change is anomaly evidence, not proof of a specific hidden mechanical fault","baseline must represent comparable operating conditions"],
        }


class DiagnosticEngineRegistry:
    def __init__(self):
        self.electronics=ElectronicsDiagnosticEngine()
        self.vehicle=VehicleDiagnosticEngine()
        self.acoustic=AcousticDiagnosticEngine()

    @staticmethod
    def select(goal="",modality="image"):
        text=str(goal or "").lower()
        if str(modality).lower()=="audio" or any(x in text for x in ("sound","noise","vibration","bearing")):return "acoustic"
        if any(x in text for x in ("vehicle","truck","car","bus","bike","motorcycle","obd","can bus","j1939","ecu","engine")):return "vehicle"
        if any(x in text for x in ("circuit","pcb","board","motherboard","electronic","wiring","relay","fuse","connector","voltage")):return "electronics"
        return None

    def evaluate(self,context,*,goal="",modality="image"):
        selected=self.select(goal,modality)
        if not selected:return {"status":"not_applicable","selected":None}
        engine=getattr(self,selected)
        return {"status":"evaluated","selected":selected,"result":engine.evaluate(dict(context or {}))}

    def status(self):
        return {
            "electronics":self.electronics.status(),
            "vehicle":self.vehicle.status(),
            "acoustic":self.acoustic.status(),
            "hardware_absence_policy":"unconfigured providers report unavailable; measurements are never fabricated",
        }
