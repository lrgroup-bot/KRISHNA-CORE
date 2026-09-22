from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import time


@dataclass(frozen=True)
class SpecialistPacket:
    specialist: str
    question: str
    evidence_state: str
    confidence: float
    observations: tuple[str, ...]
    unknowns: tuple[str, ...] = ()

    def as_dict(self):
        row=asdict(self)
        row["observations"]=list(self.observations)
        row["unknowns"]=list(self.unknowns)
        return row


class HawkeyeCoordinator:
    """Canonical live HAWKEYE coordinator.

    Bhumiputra remains the field-perception implementation. This wrapper owns the
    live evidence fusion contract so PERCEPTION/PHYSIO/BEHAVIOR/TEMPORAL/
    DIAGNOSTIC/REASONER do not become competing control planes.
    """

    SPECIALISTS={
        "PERCEPTION":"What do I actually see/hear?",
        "PHYSIO":"What measurable physical signal changed?",
        "BEHAVIOR":"What observable action occurred?",
        "TEMPORAL":"What changed over time?",
        "DIAGNOSTIC":"What may be wrong and what should we test next?",
        "REASONER":"What conclusion is actually supported by independent evidence?",
    }
    SENSOR_KEYS={
        "PHYSIO":("heart_rate","pulse","spo2","temperature_c","thermal_c","rppg_bpm","respiration_rate"),
        "BEHAVIOR":("activity","motion","pose","gesture","speed_mps","rpm","state"),
        "TEMPORAL":("timestamp","captured_at","elapsed_ms","frame_index"),
    }

    def __init__(self,state_dir: str|Path,bhumiputra,diagnostic=None,learning=None,field=None,geo=None):
        self.state_dir=Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self.bhumiputra=bhumiputra
        self.diagnostic=diagnostic
        self.learning=learning
        self.field=field
        self.geo=geo

    def __getattr__(self,name):
        return getattr(self.bhumiputra,name)

    @staticmethod
    def _clamp(value,default=0.0):
        try:return max(0.0,min(1.0,float(value)))
        except (TypeError,ValueError):return default

    @staticmethod
    def _text(value,limit=1600):
        return str(value or "").strip()[:limit]

    def _history_path(self,session_id):
        safe="".join(c for c in str(session_id or "") if c.isalnum() or c in "-_")
        if not safe:raise ValueError("invalid Hawkeye session id")
        return self.state_dir/(safe+".jsonl")

    def _previous(self,session_id):
        path=self._history_path(session_id)
        if not path.exists():return None
        try:
            rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            return rows[-1] if rows else None
        except Exception:
            return None

    def _append(self,session_id,row):
        path=self._history_path(session_id)
        rows=[]
        if path.exists():
            try:rows=path.read_text(encoding="utf-8").splitlines()[-119:]
            except Exception:rows=[]
        rows.append(json.dumps(row,ensure_ascii=False,separators=(",",":")))
        path.write_text("\n".join(rows)+"\n",encoding="utf-8")

    def _sensor_packet(self,name,sensors):
        keys=self.SENSOR_KEYS.get(name,())
        obs=[]
        for key in keys:
            value=sensors.get(key)
            if value is not None and value!="":
                obs.append(f"{key}={self._text(value,120)}")
        return SpecialistPacket(
            name,self.SPECIALISTS[name],"MEASURED" if obs else "UNKNOWN",
            0.9 if obs else 0.0,tuple(obs),() if obs else ("no supported sensor measurement supplied",)
        )

    def _diagnostic_packet(self,result,goal):
        hypotheses=result.get("fault_hypotheses") or result.get("hypotheses") or []
        tests=result.get("recommended_tests") or result.get("next_tests") or []
        obs=[]
        if isinstance(hypotheses,list):obs += [self._text(x,300) for x in hypotheses[:5] if self._text(x,300)]
        if isinstance(tests,list):obs += ["next_test: "+self._text(x,300) for x in tests[:5] if self._text(x,300)]
        if not obs and self.diagnostic and self.diagnostic.should_activate(goal):
            obs.append("diagnostic mode active; specific fault remains unverified until corroborating test/measurement evidence")
        return SpecialistPacket(
            "DIAGNOSTIC",self.SPECIALISTS["DIAGNOSTIC"],
            "INFERRED" if obs else "UNKNOWN",
            self._clamp(result.get("confidence"),0.35 if obs else 0.0),
            tuple(obs),() if obs else ("no diagnostic evidence requested or supported",)
        )

    def enrich_result(self,session_id,result,*,sensor_context=None,goal="",modality="image"):
        result=dict(result or {})
        sensors=dict(sensor_context or {})
        previous=self._previous(session_id)
        analysis=self._text(result.get("analysis"),4000)
        confidence=self._clamp(result.get("confidence"),0.5 if analysis else 0.0)

        perception=SpecialistPacket(
            "PERCEPTION",self.SPECIALISTS["PERCEPTION"],
            str(result.get("evidence_state") or ("OBSERVED" if analysis else "UNKNOWN")).upper(),
            confidence,(analysis,) if analysis else (),() if analysis else ("no supported visible/audio observation",)
        )
        physio=self._sensor_packet("PHYSIO",sensors)
        behavior=self._sensor_packet("BEHAVIOR",sensors)

        temporal_obs=[]
        if previous:
            before=self._text(previous.get("analysis"),700)
            now=self._text(analysis,700)
            if before and now:
                if before==now:temporal_obs.append("no textual change detected from previous retained observation")
                else:temporal_obs.append("current observation differs from the previous retained observation")
        temporal=self._sensor_packet("TEMPORAL",sensors)
        if temporal_obs:
            temporal=SpecialistPacket("TEMPORAL",self.SPECIALISTS["TEMPORAL"],"OBSERVED",0.7,tuple(temporal_obs),())

        diagnostic=self._diagnostic_packet(result,goal)

        supported=[p for p in (perception,physio,behavior,temporal,diagnostic) if p.evidence_state!="UNKNOWN"]
        states={p.evidence_state for p in supported}
        reasoner_obs=[]
        if supported:
            reasoner_obs.append("evidence_sources="+",".join(p.specialist for p in supported))
            reasoner_obs.append("states="+",".join(sorted(states)))
            if len(supported)<2:
                reasoner_obs.append("single-source conclusion; corroboration is still required")
        reasoner=SpecialistPacket(
            "REASONER",self.SPECIALISTS["REASONER"],
            "INFERRED" if supported else "UNKNOWN",
            min([p.confidence for p in supported],default=0.0) if len(supported)>1 else min(confidence,0.5),
            tuple(reasoner_obs),() if len(supported)>1 else ("independent corroborating evidence is limited",)
        )

        packets=[perception,physio,behavior,temporal,diagnostic,reasoner]
        fused={
            "schema":"hawkeye.live-fusion.v1",
            "session_id":session_id,
            "goal":self._text(goal,1000),
            "modality":self._text(modality,40) or "unknown",
            "at":time.time(),
            "specialists":{p.specialist:p.as_dict() for p in packets},
            "supported_specialist_count":len(supported),
            "truth_policy":"MEASURED/OBSERVED are evidence; INFERRED/PREDICTED require corroboration; UNKNOWN is preserved",
        }
        result["hawkeye_fusion"]=fused
        self._append(session_id,{"at":fused["at"],"analysis":analysis,"fusion":fused})
        return result

    def status(self):
        base=self.bhumiputra.status()
        return {
            **base,
            "agent":"HAWKEYE",
            "canonical_live_coordinator":True,
            "specialists":dict(self.SPECIALISTS),
            "bhumiputra_role":"field perception implementation behind HAWKEYE",
            "diagnostic_bound":self.diagnostic is not None,
            "learning_bound":self.learning is not None,
            "field_bound":self.field is not None,
            "geo_bound":self.geo is not None,
        }
