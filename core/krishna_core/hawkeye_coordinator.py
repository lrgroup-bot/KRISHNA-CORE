from __future__ import annotations

"""Unified live HAWKEYE coordinator.

HAWKEYE is the evidence-fusion layer over BHOOMIPUTRA field perception,
measurable physical signals, observable behavior, temporal change, bounded
diagnostics and a reasoner. It is not a second KRISHNA authority and it does
not turn weak proxies into private-state, deception, medical or hardware
certainty.
"""

from pathlib import Path
from threading import RLock
import hashlib
import json
import time


class HawkeyeCoordinator:
    VERSION = "hawkeye-coordinator-v1"
    LANES = ("perception", "physio", "behavior", "temporal", "diagnostic", "reasoner")
    EVIDENCE_STATES = {"MEASURED", "OBSERVED", "INFERRED", "PREDICTED", "UNKNOWN"}
    STATE_WEIGHT = {
        "MEASURED": 1.0,
        "OBSERVED": 0.85,
        "INFERRED": 0.55,
        "PREDICTED": 0.35,
        "UNKNOWN": 0.0,
    }

    SPECIALISTS = {
        "perception": "What do I actually see/hear?",
        "physio": "What measurable physical signal changed?",
        "behavior": "What observable action occurred?",
        "temporal": "What changed over time?",
        "diagnostic": "What may be wrong and what should we test next?",
        "reasoner": "What conclusion is actually supported?",
    }

    def __init__(
        self,
        state_dir: str | Path,
        *,
        bhumiputra,
        diagnostic,
        learning=None,
        field=None,
        geo=None,
        memory=None,
    ):
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.bhumiputra = bhumiputra
        self.diagnostic = diagnostic
        self.learning = learning
        self.field = field
        self.geo = geo
        self.memory = memory
        self.lock = RLock()

    @staticmethod
    def _safe_id(value):
        out = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
        if not out:
            raise ValueError("invalid HAWKEYE session_id")
        return out

    def _path(self, session_id):
        return self.sessions_dir / f"{self._safe_id(session_id)}.json"

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fingerprint(value):
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(",",":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _new_state(self, session_id, project, goal, source="live"):
        now=time.time()
        return {
            "session_id":session_id,
            "agent":"HAWKEYE",
            "version":self.VERSION,
            "project":str(project or "KRISHNA"),
            "goal":str(goal or "live perception")[:2000],
            "source":str(source or "live"),
            "created_at":now,
            "updated_at":now,
            "lanes":{name:[] for name in self.LANES},
            "contradictions":[],
            "reasoning":None,
            "policy":{
                "authority":"KRISHNA",
                "verification":"SUDARSHAN",
                "field_specialist":"BHOOMIPUTRA",
                "no_private_state_inference":True,
                "no_deception_from_behavior_or_physio":True,
                "no_camera_only_hidden_fault_certainty":True,
                "authentication_secrets":"redact-never-learn",
            },
        }

    def _load(self, session_id):
        path=self._path(session_id)
        if not path.is_file():
            raise KeyError(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _ensure_state(self, session_id):
        try:
            return self._load(session_id)
        except KeyError:
            field=self.bhumiputra.get_live_session(session_id)
            state=self._new_state(
                session_id,
                field.get("project"),
                field.get("purpose"),
                "legacy-field-session",
            )
            state["field_session"]={
                "agent":field.get("agent"),
                "version":field.get("version"),
                "scene_hint":field.get("scene_hint"),
                "coordinates":field.get("coordinates") or {},
            }
            with self.lock:self._save(state)
            return state

    def _save(self, state):
        state["updated_at"]=time.time()
        path=self._path(state["session_id"])
        tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(path)

    def bind_evidence_cipher(self, cipher, *, require_encryption=False):
        return self.bhumiputra.bind_evidence_cipher(cipher,require_encryption=require_encryption)

    def start_live_session(self, *, project="KRISHNA", purpose="live field scan",
                           coordinates=None, scene_hint="auto"):
        field=self.bhumiputra.start_live_session(
            project=project,purpose=purpose,coordinates=coordinates,scene_hint=scene_hint
        )
        state=self._new_state(field["session_id"],project,purpose,"bhumiputra-live")
        state["field_session"]={
            "agent":field.get("agent"),
            "version":field.get("version"),
            "scene_hint":field.get("scene_hint"),
            "coordinates":field.get("coordinates") or {},
        }
        with self.lock:self._save(state)
        return {**field,"hawkeye":{"coordinator":self.VERSION,"lanes":list(self.LANES)}}

    def get_live_session(self, session_id):
        field=self.bhumiputra.get_live_session(session_id)
        state=self._ensure_state(session_id)
        return {
            **field,
            "hawkeye":{
                "coordinator":self.VERSION,
                "lane_counts":{k:len(v) for k,v in (state.get("lanes") or {}).items()},
                "reasoning":state.get("reasoning"),
                "contradictions":state.get("contradictions") or [],
            },
        }

    def live_prompt(self, *, scene_hint="auto", user_goal="", sensor_context=None):
        return self.bhumiputra.live_prompt(
            scene_hint=scene_hint,user_goal=user_goal,sensor_context=sensor_context
        )

    def store_mobile_evidence(self, session_id, raw, content_type="image/jpeg", sensor_context=None):
        return self.bhumiputra.store_mobile_evidence(
            session_id,raw,content_type,sensor_context
        )

    def record_lane(
        self,
        session_id,
        lane,
        payload,
        *,
        evidence_state="OBSERVED",
        confidence=0.5,
        source_refs=None,
        limitations=None,
        provenance=None,
    ):
        lane=str(lane or "").strip().lower()
        if lane not in self.LANES:
            raise ValueError(f"unknown HAWKEYE lane: {lane}")
        evidence_state=str(evidence_state or "UNKNOWN").strip().upper()
        if evidence_state not in self.EVIDENCE_STATES:
            raise ValueError(f"invalid evidence state: {evidence_state}")
        state=self._ensure_state(session_id)
        payload=dict(payload or {}) if isinstance(payload,dict) else {"text":str(payload or "")[:8000]}

        if lane=="physio":
            if evidence_state=="MEASURED" and not any(
                isinstance(v,(int,float)) for v in payload.values() if not isinstance(v,bool)
            ):
                raise ValueError("MEASURED physio evidence requires at least one numeric supplied signal")
            payload["interpretation_limit"]="physical signals are measurements, not proof of emotion, deception or diagnosis"
        if lane=="behavior":
            payload["interpretation_limit"]="observable behavior only; do not infer hidden intent, deception or private mental state"
        if lane=="diagnostic":
            payload["verification_limit"]="fault hypotheses require measurement/retest before verified status"

        refs=sorted({str(x) for x in (source_refs or []) if str(x).strip()})[:100]
        row={
            "lane":lane,
            "at":time.time(),
            "evidence_state":evidence_state,
            "confidence":self._clamp(confidence),
            "source_refs":refs,
            "independent_source_count":len(refs),
            "payload":payload,
            "limitations":[str(x)[:1000] for x in (limitations or [])][:30],
            "provenance":dict(provenance or {}),
        }
        row["fingerprint"]=self._fingerprint({
            "lane":lane,"state":evidence_state,"payload":payload,"source_refs":refs
        })
        with self.lock:
            state=self._ensure_state(session_id)
            state["lanes"].setdefault(lane,[]).append(row)
            state["lanes"][lane]=state["lanes"][lane][-200:]
            self._save(state)
        if self.memory:
            self.memory.audit(
                "hawkeye_lane",lane,
                f"{session_id}:{evidence_state}:{row['confidence']}:{row['fingerprint'][:16]}"
            )
        return row

    def record_live_analysis(self, session_id, analysis, *, model=None,
                             sensor_context=None, frame_meta=None):
        field=self.bhumiputra.record_live_analysis(
            session_id,analysis,model=model,sensor_context=sensor_context,frame_meta=frame_meta
        )
        meta=dict(frame_meta or {})
        lane="diagnostic" if bool(meta.get("diagnostic")) else "perception"
        source_refs=[]
        if meta.get("evidence_id"):source_refs.append(meta["evidence_id"])
        if meta.get("sha256"):source_refs.append(meta["sha256"])
        if model:source_refs.append("model:"+str(model))
        row=self.record_lane(
            session_id,lane,
            {
                "analysis":field["latest_analysis"]["analysis"],
                "model":str(model or ""),
                "sensor_context":dict(sensor_context or {}),
                "frame_meta":meta,
            },
            evidence_state="INFERRED" if lane=="diagnostic" else "OBSERVED",
            confidence=float(meta.get("confidence") or (0.6 if lane=="diagnostic" else 0.7)),
            source_refs=source_refs,
            provenance={"field_frame":field["frame_count"]},
        )
        temporal=self._record_temporal_from_latest(session_id)
        reasoning=self.reason(session_id)
        return {
            **field,
            "hawkeye_lane":row,
            "temporal":temporal,
            "reasoning":reasoning,
        }

    def _record_temporal_from_latest(self, session_id):
        state=self._ensure_state(session_id)
        observations=list(state.get("lanes",{}).get("perception") or [])
        if len(observations)<2:
            return {"status":"insufficient_history"}
        previous,current=observations[-2],observations[-1]
        changed=previous.get("fingerprint")!=current.get("fingerprint")
        return self.record_lane(
            session_id,"temporal",
            {
                "changed":changed,
                "previous_fingerprint":previous.get("fingerprint"),
                "current_fingerprint":current.get("fingerprint"),
                "comparison":"frame-level evidence changed" if changed else "no frame-level evidence change detected",
            },
            evidence_state="OBSERVED",
            confidence=min(previous.get("confidence",0),current.get("confidence",0)),
            source_refs=[previous.get("fingerprint"),current.get("fingerprint")],
        )

    def record_physio(self, session_id, measurements, *, source_refs=None, provenance=None):
        return self.record_lane(
            session_id,"physio",measurements,evidence_state="MEASURED",
            confidence=1.0,source_refs=source_refs,provenance=provenance
        )

    def record_behavior(self, session_id, observation, *, confidence=0.8, source_refs=None):
        return self.record_lane(
            session_id,"behavior",observation,evidence_state="OBSERVED",
            confidence=confidence,source_refs=source_refs
        )

    def record_diagnostic_result(self, session_id, result, *, source_refs=None):
        state=str((result or {}).get("evidence_state") or "INFERRED").upper()
        if state not in self.EVIDENCE_STATES:state="INFERRED"
        row=self.record_lane(
            session_id,"diagnostic",result,evidence_state=state,
            confidence=float((result or {}).get("confidence") or 0),
            source_refs=source_refs,
        )
        # A diagnostic measurement changes the evidence set immediately. Keep
        # the fused REASONER state synchronized so live/status consumers never
        # observe fresh diagnostic evidence paired with stale/None reasoning.
        self.reason(session_id)
        return row

    def add_contradiction(self, session_id, left_ref, right_ref, reason):
        state=self._ensure_state(session_id)
        row={
            "left_ref":str(left_ref or "")[:200],
            "right_ref":str(right_ref or "")[:200],
            "reason":str(reason or "")[:2000],
            "status":"open",
            "at":time.time(),
        }
        with self.lock:
            state=self._ensure_state(session_id)
            state["contradictions"].append(row)
            state["contradictions"]=state["contradictions"][-200:]
            self._save(state)
        return row

    def reason(self, session_id):
        state=self._ensure_state(session_id)
        rows=[]
        for lane in ("perception","physio","behavior","temporal","diagnostic"):
            rows.extend(state.get("lanes",{}).get(lane) or [])
        current=[x for x in rows if x.get("evidence_state")!="UNKNOWN"][-100:]
        source_refs={ref for row in current for ref in row.get("source_refs") or []}
        weighted=[]
        for row in current:
            confidence=self._clamp(row.get("confidence"))
            weight=self.STATE_WEIGHT.get(row.get("evidence_state"),0.0)
            weighted.append(confidence*weight)
        base=sum(weighted)/len(weighted) if weighted else 0.0
        independence=min(1.0,len(source_refs)/3.0) if source_refs else 0.0
        open_conflicts=len([x for x in state.get("contradictions") or [] if x.get("status")=="open"])
        confidence=max(0.0,min(1.0,base*(0.75+0.25*independence)*(0.75**open_conflicts)))
        lanes_present=sorted({x["lane"] for x in current})
        strongest=sorted(
            current,
            key=lambda x:self.STATE_WEIGHT.get(x.get("evidence_state"),0)*self._clamp(x.get("confidence")),
            reverse=True,
        )[:8]
        if not current:
            conclusion_state="INSUFFICIENT_EVIDENCE"
        elif open_conflicts:
            conclusion_state="CONTESTED"
        elif len(lanes_present)>=2 and (len(source_refs)>=2 or any(x.get("evidence_state")=="MEASURED" for x in current)):
            conclusion_state="SUPPORTED"
        else:
            conclusion_state="PRELIMINARY"
        result={
            "lane":"reasoner",
            "conclusion_state":conclusion_state,
            "confidence":round(confidence,4),
            "lanes_present":lanes_present,
            "independent_source_refs":len(source_refs),
            "open_contradictions":open_conflicts,
            "supporting_evidence":[
                {
                    "lane":x.get("lane"),
                    "evidence_state":x.get("evidence_state"),
                    "confidence":x.get("confidence"),
                    "fingerprint":x.get("fingerprint"),
                    "source_refs":x.get("source_refs") or [],
                }
                for x in strongest
            ],
            "next_action":(
                "resolve contradictions / collect another independent measurement"
                if open_conflicts else
                "collect another independent measurement or specialist result"
                if conclusion_state in {"INSUFFICIENT_EVIDENCE","PRELIMINARY"} else
                "Sudarshan may verify the supported conclusion against task-specific acceptance criteria"
            ),
            "guardrails":[
                "supported does not mean medically, structurally or mechanically certified",
                "behavior/physio are not deception or private-state proof",
                "camera-only hidden faults remain unverified without measurements",
            ],
            "at":time.time(),
        }
        with self.lock:
            state=self._ensure_state(session_id)
            state["reasoning"]=result
            state["lanes"]["reasoner"].append(result)
            state["lanes"]["reasoner"]=state["lanes"]["reasoner"][-100:]
            self._save(state)
        return result

    def specialist_status(self):
        return {
            name:{
                "question":question,
                "mode":"live-coordinated" if name!="reasoner" else "evidence-fusion",
            }
            for name,question in self.SPECIALISTS.items()
        }

    def status(self):
        sessions=list(self.sessions_dir.glob("*.json"))
        return {
            "agent":"HAWKEYE",
            "version":self.VERSION,
            "role":"coordinated live perception/evidence fusion under KRISHNA",
            "specialists":self.specialist_status(),
            "session_count":len(sessions),
            "bhumiputra":self.bhumiputra.status(),
            "diagnostic":self.diagnostic.status() if self.diagnostic else None,
            "learning_bound":self.learning is not None,
            "field_platform_bound":self.field is not None,
            "geo_engine_bound":self.geo is not None,
            "authority":"KRISHNA",
            "verification":"SUDARSHAN",
            "ready":True,
        }

    def __getattr__(self, name):
        """Compatibility bridge while legacy callers move to coordinator methods."""
        target=object.__getattribute__(self,"bhumiputra")
        if hasattr(target,name):
            return getattr(target,name)
        raise AttributeError(name)
