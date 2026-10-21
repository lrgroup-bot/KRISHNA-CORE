"""Opt-in paired, TLS-pinned SURYADEV fleet collector transport.

A laptop independently checks each Core-offered URL against its own approved
plan. Persistent receipts survive crashes. Neither knowledge nor mastery is
asserted by this evidence-only collector.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path
import time

from suryadev_krishna_mission import load_config, post_core
from suryadev_feeder import read_plan
from suryadev_liveops import atomic_json, _safe_read
from suryadev_sources import source_kind
from suryadev_resources import snapshot

STATE = "krishna-fleet-relay.json"
MAX_STATE_BYTES = 16384
POLL_SECONDS = 10
ERROR_RETRY_SECONDS = 45


class FleetRelay:
    def __init__(self, root, plan_path, config_path, *, transport=post_core, clock=time.time):
        self.root = Path(root).expanduser().resolve()
        self.plan_path = Path(plan_path).expanduser().resolve(strict=True)
        self.config = load_config(config_path)
        if not self.config["device_id"].startswith("suryadev-"):
            raise ValueError("fleet requires owner-paired suryadev- device ID")
        self.transport = transport
        self.clock = clock
        self.next_attempt = 0

    def _read(self):
        row = _safe_read(self.root, STATE, max_bytes=MAX_STATE_BYTES)
        if row and row.get("device_id") not in (None,self.config["device_id"]):
            raise ValueError("fleet state belongs to another paired device")
        return row

    def _write(self, row):
        atomic_json(self.root, STATE, {**row,"device_id":self.config["device_id"]})

    def _post(self, path, payload):
        return self.transport(self.config,path,{
            "device_id":self.config["device_id"], **payload})

    def _heartbeat(self, capacity):
        hw = snapshot(self.root)
        if hw.get("available") is not True:
            return {"status":"telemetry_unavailable","reason":hw.get("reason")}
        now = float(self.clock())
        age = max(0.0, now - float(hw.get("sample_time") or now))
        available = bool(capacity.get("safe"))
        free = max(0,int(capacity.get("max_total") or 0)-
                   int(capacity.get("active_total") or 0)) if available else 0
        local = capacity.get("limits") or {}
        capabilities=[lane for lane in ("website","pdf","youtube")
                      if int(local.get(lane) or 0) > 0]
        hw = dict(hw)
        hw["sample_age_seconds"] = min(age, 86400)
        hw["logical_cpus"] = int(platform.os.cpu_count()) if False else (int(__import__("os").cpu_count() or 1))
        hw["gpu_inference"] = False  # unproven on this laptop; do not infer from display GPU
        reply=self._post("/api/suryadev/device/heartbeat",{
            "node_name":platform.node()[:100],
            "platform":platform.system(),
            "worker_running":True,
            "network_online":True,
            "thermal_state":"unknown",
            "learning_state":"researching" if capacity.get("active_total") else "idle",
            "hardware":hw,
            "capacity":{"available_slots":min(128,free),"capabilities":capabilities}
        })
        if reply.get("accepted") is not True:
            raise ValueError("KRISHNA Core refused fleet heartbeat")
        return {"status":"heartbeat_accepted","free_slots":free,
                "capabilities":capabilities,"fresh_age_seconds":round(age,2)}

    def _job(self, lib, url):
        rows=lib.db.execute("SELECT id,status,error FROM jobs WHERE url=? ORDER BY id DESC LIMIT 1",
                            (url,)).fetchall()
        return rows[0] if rows else None

    def _accept_offer(self, lib, reply):
        if reply.get("status") != "leased":
            return {"state":str(reply.get("status") or "idle")[:100]}
        task=reply.get("task")
        lease_id=reply.get("lease_id")
        if (not isinstance(task,dict) or not isinstance(lease_id,str)
                or len(lease_id)<16 or len(lease_id)>128):
            raise ValueError("invalid paired Core lease")
        url=task.get("url")
        plan=read_plan(self.plan_path)
        if (not isinstance(url,str) or url not in set(plan["approved_urls"])):
            # Fail closed; do not even request source bytes.
            self._post("/api/suryadev/fleet/complete",{
                "task_id":task.get("task_id"),"lease_id":lease_id,
                "outcome":"rejected","detail":"URL missing from exact laptop owner-approved source list"})
            return {"state":"refused_unapproved_source"}
        if task.get("kind") != source_kind(url):
            raise ValueError("leased task source type mismatch")
        task_id=str(task.get("task_id") or "")
        rishi_id=str(task.get("rishi_id") or "")
        if not task_id.startswith("fleet-") or not rishi_id:
            raise ValueError("Core task lacks stable identity or Rishi attribution")
        # Persist BEFORE local SQLite mutation so a crash resumes the same URL.
        record={"task_id":task_id,"rishi_id":rishi_id,
                "mission_id":str(task.get("mission_id") or ""),
                "url":url,"lease_id":lease_id,"job_id":None,
                "state":"accepting","updated_at":self.clock()}
        self._write({"active":record})
        existing=self._job(lib,url)
        if existing:
            job_id=existing[0]
        else:
            job_id=lib.add(url)
        record.update(job_id=job_id,state="local_job_attached",updated_at=self.clock())
        self._write({"active":record})
        return {"state":"local_job_attached","job_id":job_id,"task_id":task_id}

    def _reconcile(self, lib, active):
        url=active["url"]
        current=self._job(lib,url)
        if current is None:
            # Crash between durable acceptance and SQLite enqueue.
            plan=read_plan(self.plan_path)
            if url not in set(plan["approved_urls"]):
                raise ValueError("Previously leased URL no longer laptop-approved")
            job_id=lib.add(url)
            active["job_id"]=job_id
            self._write({"active":active})
            return {"state":"local_job_attached","job_id":job_id}
        job_id,status,error=current
        if active.get("job_id") not in (None,job_id):
            attached=lib.db.execute("SELECT status,error FROM jobs WHERE id=? AND url=?",
                                    (active["job_id"],url)).fetchone()
            if attached:
                job_id=active["job_id"]
                status,error=attached
        active["job_id"]=job_id
        if status=="done":
            evidence=lib.db.execute("SELECT sha256 FROM findings WHERE job_id=? AND url=?",
                                    (job_id,url)).fetchone()
            if not evidence or not isinstance(evidence[0],str) or len(evidence[0])!=64:
                raise RuntimeError("Completed collection has no durable evidence hash")
            outcome="collected"
            payload={"task_id":active["task_id"],"lease_id":active["lease_id"],
                     "outcome":outcome,"evidence_sha256":evidence[0]}
        elif status=="failed":
            outcome="rate_limited" if "429" in str(error or "") else "failed"
            payload={"task_id":active["task_id"],"lease_id":active["lease_id"],
                     "outcome":outcome,"detail":str(error or "collector failed")[:300]}
        else:
            # Renew only the currently authenticated lease. No new job is
            # created if a source is already queued/running.
            reply=self._post("/api/suryadev/fleet/renew",{
                "task_id":active["task_id"],"lease_id":active["lease_id"]})
            if reply.get("renewed") is not True:
                raise RuntimeError("KRISHNA did not renew owned fleet lease")
            active["state"]="waiting_local_"+status
            active["updated_at"]=self.clock()
            self._write({"active":active})
            return {"state":active["state"],"task_id":active["task_id"],"job_id":job_id}
        receipt=self._post("/api/suryadev/fleet/complete",payload)
        if receipt.get("acknowledged") is not True:
            raise RuntimeError("KRISHNA did not acknowledge fleet collection receipt")
        self._write({"active":None,"last_receipt":{
            "task_id":active["task_id"],"job_id":job_id,
            "outcome":outcome,"acknowledged_at":self.clock(),
            "knowledge_verified":False}})
        return {"state":"core_evidence_acknowledged","task_id":active["task_id"],
                "job_id":job_id,"outcome":outcome,"knowledge_verified":False}

    def tick(self, lib, capacity):
        now=float(self.clock())
        if now < self.next_attempt:
            return None
        self.next_attempt=now+POLL_SECONDS
        try:
            local=self._read()
            health=self._heartbeat(capacity)
            if health["status"]!="heartbeat_accepted":
                return health
            active=local.get("active")
            if isinstance(active,dict):
                return self._reconcile(lib,active)
            if not capacity.get("safe") or int(capacity.get("active_total") or 0)>=int(capacity.get("max_total") or 0):
                return {"state":"no_measured_headroom"}
            offer=self._post("/api/suryadev/fleet/claim",{})
            return self._accept_offer(lib,offer)
        except (OSError,RuntimeError,ValueError,KeyError,TypeError) as exc:
            self.next_attempt=now+ERROR_RETRY_SECONDS
            error=type(exc).__name__+": "+str(exc)[:180]
            # Do not overwrite an existing unacknowledged lease record.
            current=self._read()
            if not current.get("active"):
                self._write({"active":None,"last_error":error,"updated_at":now})
            return {"state":"retry_later","error":error,"knowledge_verified":False}
