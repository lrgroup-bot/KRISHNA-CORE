from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import RLock


class BrahmaProcessQC:
    VERSION="brahma-process-qc-v1"
    FAIL={"action.failed","AGENT_FAILED","MISSION_FAILED","TOOL_ERROR","TEST_FAILED","BUILD_FAILED","VERIFICATION_FAILED","QUEUE_FAILED"}
    WORK={"action.requested","MISSION_STARTED","AGENT_SPAWNED","BEFORE_TOOL","TEST_STARTED","BUILD_STARTED","VERIFICATION_STARTED","QUEUE_CLAIMED","ROLLBACK_STARTED"}
    DONE={"action.completed","MISSION_COMPLETED","AGENT_FINISHED","AFTER_TOOL","TEST_PASSED","BUILD_COMPLETED","VERIFICATION_PASSED","QUEUE_ACKED","ROLLBACK_COMPLETED","QUEUE_RECOVERED","SERVICE_RESTARTED"}
    GODS=(
        ("krishna","KRISHNA","ॐ"),("brahma","BRAHMA","🪷"),("sudarshan","Sudarshan","☸"),
        ("hawkeye","Hawkeye","◉"),("kabach","KABACH","🛡"),("garuda","Garuda","◆"),
        ("garudanetra","Garudanetra","👁"),("narad","NARAD","♬"),("brahmagyan","BRAHMAGYAN","✦"),
        ("gyan","Gyan-Bhandar","▤"),("rishi","Rishi Council","△"),("amcc","aMCC","⚡"),
    )

    def __init__(self,state_root,event_bus,memory=None):
        self.root=Path(state_root);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"process-qc.json";self.event_bus=event_bus;self.memory=memory
        self.lock=RLock();self.retry_dispatch=None;self.investigate=None;self.consult_krishna=None;self.repair_known=None
        self._attached=False;self._handling=set();self._retried=set();now=time.time()
        self.state={"version":self.VERSION,"latest_state":"idle","notifications":[],"open_errors":{},"gods":{
            k:{"id":k,"name":n,"logo":logo,"state":"idle","color":"red","detail":"Idle","updated_at":now}
            for k,n,logo in self.GODS
        }}
        self.load_error=None;self._load()

    @staticmethod
    def color(state):
        state=str(state or "idle").lower()
        if state in {"working","handling"}:return "yellow"
        if state in {"done","healthy","completed","fixed"}:return "green"
        return "red"

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict):self.state.update(raw)
            self.state.setdefault("notifications",[]);self.state.setdefault("open_errors",{});g=self.state.setdefault("gods",{})
            for k,n,logo in self.GODS:
                g.setdefault(k,{"id":k,"name":n,"logo":logo,"state":"idle","color":"red","detail":"Idle","updated_at":time.time()})
        except Exception as exc:self.load_error=f"{type(exc).__name__}: {exc}"

    def _save(self):
        if self.load_error:raise RuntimeError("BRAHMA process QC state unreadable")
        tmp=self.path.with_suffix(".tmp");tmp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding="utf-8");os.replace(tmp,self.path)

    def bind_runtime(self,*,retry_dispatch=None,investigate=None,consult_krishna=None,repair_known=None):
        self.retry_dispatch=retry_dispatch;self.investigate=investigate;self.consult_krishna=consult_krishna;self.repair_known=repair_known;return self

    def attach(self):
        if not self._attached:self.event_bus.subscribe("*",self.on_event);self._attached=True
        return self.status()

    def detach(self):
        if self._attached:self.event_bus.unsubscribe("*",self.on_event);self._attached=False

    @staticmethod
    def compact(value,limit=1200):
        return str(value or "").replace("\r"," ").replace("\n"," ").strip()[:limit]

    def component(self,event):
        p=event.get("payload") if isinstance(event.get("payload"),dict) else {}
        text=" ".join((str(event.get("topic") or ""),str(event.get("source") or ""),str(p.get("action") or ""))).lower()
        for k,tokens in (
            ("brahmagyan",("brahmagyan",)),("garudanetra",("garudanetra",)),("hawkeye",("hawkeye","bhumiputra")),
            ("kabach",("kabach","privacy")),("narad",("narad",)),("garuda",("garuda",)),("gyan",("gyan",)),
            ("rishi",("rishi",)),("amcc",("amcc","cognition.")),("brahma",("brahma",)),("sudarshan",("sudarshan","shared-action-bus","action.")),
        ):
            if any(x in text for x in tokens):return k
        return "krishna"

    def notify(self,state,title,detail="",*,component="brahma",topic="",project="KRISHNA",metadata=None):
        if component not in self.state["gods"]:component="krishna"
        row={"notification_id":str(uuid.uuid4()),"created_at":time.time(),"state":state,"color":self.color(state),
             "title":self.compact(title,240),"detail":self.compact(detail,1600),"component":component,
             "topic":self.compact(topic,160),"project":self.compact(project,160),"metadata":dict(metadata or {})}
        with self.lock:
            self.state["latest_state"]=state;self.state["notifications"].append(row);self.state["notifications"]=self.state["notifications"][-500:]
            self.state["gods"][component].update({"state":state,"color":row["color"],"detail":row["title"] or row["detail"],"updated_at":row["created_at"]})
            if component!="brahma":
                bs="handling" if state in {"error","working","handling"} else ("done" if state in {"done","fixed"} else "idle")
                self.state["gods"]["brahma"].update({"state":bs,"color":self.color(bs),"detail":"QC "+row["title"],"updated_at":row["created_at"]})
            self._save()
        if self.memory:
            try:self.memory.audit("brahma_process_qc",state,f"{component}:{row['title']}")
            except Exception:pass
        return row

    def _consult(self,event,error):
        if not callable(self.consult_krishna):return ""
        try:return self.compact(self.consult_krishna({"topic":event.get("topic"),"payload":event.get("payload") or {},"failure":error}),1600)
        except Exception as exc:return f"KRISHNA consultation unavailable: {type(exc).__name__}"

    def _retry(self,event):
        if event.get("topic")!="action.failed" or not callable(self.retry_dispatch):return None
        p=event.get("payload") if isinstance(event.get("payload"),dict) else {};spec=p.get("spec") if isinstance(p.get("spec"),dict) else {}
        aid=str(p.get("action_id") or event.get("event_id") or "");action=str(p.get("action") or "").strip()
        if not aid or not action:return None
        if str(p.get("actor") or "").strip().lower()=="brahma-qc":
            return {"attempted":False,"blocked":True,"reason":"BRAHMA retry already failed; recursive retry blocked"}
        if spec.get("mutating") or spec.get("requires_approval"):
            return {"attempted":False,"blocked":True,"reason":"change requires KRISHNA approval/verified promotion"}
        if aid in self._retried:return {"attempted":False,"blocked":True,"reason":"safe retry already attempted"}
        self._retried.add(aid)
        try:
            result=self.retry_dispatch({"action_id":aid,"action":action,"payload":p.get("payload") or {},"project":p.get("project") or "KRISHNA","permissions":p.get("permissions") or []})
            return {"attempted":True,"fixed":True,"result":result}
        except Exception as exc:return {"attempted":True,"fixed":False,"error":f"{type(exc).__name__}: {self.compact(exc,500)}"}

    def _known_repair(self,event,error):
        if not callable(self.repair_known):return None
        p=event.get("payload") if isinstance(event.get("payload"),dict) else {}
        try:
            return self.repair_known(
                str(p.get("project") or "KRISHNA"),
                str(error or ""),
                str(p.get("action") or ""),
            )
        except Exception as exc:
            return {"available":True,"error":f"{type(exc).__name__}: {self.compact(exc,500)}"}

    def on_event(self,event):
        topic=str(event.get("topic") or "");source=str(event.get("source") or "")
        if source=="brahma-process-qc" or topic.startswith("BRAHMA_QC_"):return None
        comp=self.component(event);p=event.get("payload") if isinstance(event.get("payload"),dict) else {};project=str(p.get("project") or "KRISHNA")
        name=self.state["gods"][comp]["name"]
        if topic in self.WORK:return self.notify("working",f"{name} working",topic,component=comp,topic=topic,project=project)
        if topic in self.DONE:return self.notify("done",f"{name} completed",topic,component=comp,topic=topic,project=project)
        if topic not in self.FAIL:return None
        if topic=="action.failed" and str(p.get("actor") or "").strip().lower()=="brahma-qc":
            error=str(p.get("error") or "safe retry failed")
            return self.notify("error","BRAHMA safe retry failed",error,component="brahma",topic=topic,project=project)
        key=str(event.get("event_id") or uuid.uuid4())
        if key in self._handling:return None
        self._handling.add(key)
        try:
            error=str(p.get("error") or p.get("last_error") or topic)
            with self.lock:
                self.state.setdefault("open_errors",{})[key]={"component":comp,"project":project,"topic":topic,"error":self.compact(error,800),"created_at":time.time()}
                self._save()
            self.notify("error",f"{name} error detected",error,component=comp,topic=topic,project=project)
            self.notify("handling","BRAHMA handling error",f"{name}: {error}",component="brahma",topic=topic,project=project)
            discussion=self._consult(event,error);retry=self._retry(event)
            if retry and retry.get("fixed"):
                with self.lock:
                    self.state.setdefault("open_errors",{}).pop(key,None);self._save()
                self.notify("done",f"{name} fixed",topic,component=comp,topic=topic,project=project,metadata={"recovery":retry})
                return self.notify("done","BRAHMA QC done",discussion or "Safe retry verified",component="brahma",topic=topic,project=project)
            repair=self._known_repair(event,error)
            if isinstance(repair,dict) and repair.get("fixed"):
                with self.lock:
                    self.state.setdefault("open_errors",{}).pop(key,None);self._save()
                self.notify("done",f"{name} fixed",topic,component=comp,topic=topic,project=project,metadata={"repair":repair})
                return self.notify("done","BRAHMA repair verified",discussion or "Verified recovery completed",component="brahma",topic=topic,project=project)
            if isinstance(repair,dict) and repair.get("candidate_ready"):
                return self.notify("handling","BRAHMA verified repair candidate ready","Waiting for normal KRISHNA promotion approval.",component="brahma",topic=topic,project=project,metadata={"repair":repair,"krishna_discussion":discussion})
            investigation=None
            if callable(self.investigate):
                try:investigation=self.investigate(project,error)
                except Exception as exc:investigation={"error":f"{type(exc).__name__}: {self.compact(exc,500)}"}
            reason=(retry or {}).get("reason") or (retry or {}).get("error") or "No safe automatic repair was proven."
            return self.notify("error","BRAHMA needs verified repair",reason+((" KRISHNA: "+discussion) if discussion else ""),component="brahma",topic=topic,project=project,metadata={"recovery":retry,"repair":locals().get("repair"),"investigation":investigation})
        finally:self._handling.discard(key)

    def status(self):
        with self.lock:
            notes=list(self.state.get("notifications") or []);gods=[dict(self.state["gods"][k]) for k,_,_ in self.GODS];latest=str(self.state.get("latest_state") or "idle")
            open_errors=dict(self.state.get("open_errors") or {})
        open_components={str(v.get("component") or "") for v in open_errors.values() if isinstance(v,dict)}
        for god in gods:
            if god.get("id") in open_components and god.get("state") not in {"working","handling"}:
                god["state"]="error";god["color"]="red"
        overall=("yellow" if latest in {"working","handling"} else ("red" if open_errors else self.color(latest)))
        return {"agent":"BRAHMA","version":self.VERSION,"role":"global KRISHNA process QC + safe automatic recovery",
                "attached":self._attached,"latest_state":latest,"latest_color":overall,
                "color_contract":{"red":"idle or error","yellow":"working or handling","green":"completed or healthy"},
                "gods":gods,"notifications":notes[-100:],"open_error_count":len(open_errors),"open_errors":list(open_errors.values())[-20:],
                "unresolved_recent":[x for x in notes if x.get("state")=="error"][-20:],
                "krishna_discussion":callable(self.consult_krishna),"ready":self.load_error is None,"load_error":self.load_error}
