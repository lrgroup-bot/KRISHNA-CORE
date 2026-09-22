from __future__ import annotations

import json
import sqlite3
import time
import uuid
from threading import RLock

MISSION_STATES=(
    "QUEUED","PLANNING","RUNNING","WAITING","BLOCKED","ACTION_REQUIRED",
    "VERIFYING","COMPLETED","FAILED","ROLLING_BACK","ROLLED_BACK","CANCELLED",
)
_TERMINAL={"COMPLETED","FAILED","ROLLED_BACK","CANCELLED"}
_INTERRUPTED={"PLANNING","RUNNING","VERIFYING","ROLLING_BACK"}

class MissionEngine:
    """Durable authoritative mission ledger.

    UI/browser/mobile connections are observers. Mission state lives in SQLite and
    survives KRISHNA restarts.
    """

    def __init__(self,db_path,event_bus=None):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        self.event_bus=event_bus
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS missions(
              mission_id TEXT PRIMARY KEY,
              parent_mission_id TEXT,
              session_id TEXT,
              project_id TEXT NOT NULL,
              goal TEXT NOT NULL,
              status TEXT NOT NULL,
              priority INTEGER NOT NULL DEFAULT 50,
              created_at REAL NOT NULL,
              started_at REAL,
              completed_at REAL,
              current_step TEXT NOT NULL DEFAULT '',
              progress REAL NOT NULL DEFAULT 0,
              assigned_agents TEXT NOT NULL DEFAULT '[]',
              required_tools TEXT NOT NULL DEFAULT '[]',
              permission_profile TEXT NOT NULL DEFAULT 'default',
              resource_budget TEXT NOT NULL DEFAULT '{}',
              checkpoints TEXT NOT NULL DEFAULT '[]',
              artifacts TEXT NOT NULL DEFAULT '[]',
              evidence TEXT NOT NULL DEFAULT '[]',
              errors TEXT NOT NULL DEFAULT '[]',
              retry_count INTEGER NOT NULL DEFAULT 0,
              verification_status TEXT NOT NULL DEFAULT 'pending',
              rollback_point TEXT,
              metadata TEXT NOT NULL DEFAULT '{}',
              updated_at REAL NOT NULL
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_missions_project_status ON missions(project_id,status,updated_at)")
            self.db.execute("""CREATE TABLE IF NOT EXISTS mission_checkpoints(
              checkpoint_id TEXT PRIMARY KEY,
              mission_id TEXT NOT NULL,
              seq INTEGER NOT NULL,
              label TEXT NOT NULL,
              state TEXT NOT NULL,
              trusted INTEGER NOT NULL DEFAULT 1,
              created_at REAL NOT NULL,
              UNIQUE(mission_id,seq)
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_mission_checkpoints ON mission_checkpoints(mission_id,seq)")
            self.db.commit()

    @staticmethod
    def _j(v,default):
        try:return json.loads(v) if v is not None else default
        except Exception:return default

    @classmethod
    def _row(cls,row):
        if not row:return None
        d=dict(row)
        for key,default in (
            ("assigned_agents",[]),("required_tools",[]),("resource_budget",{}),
            ("checkpoints",[]),("artifacts",[]),("evidence",[]),("errors",[]),("metadata",{}),
        ):
            d[key]=cls._j(d.get(key),default)
        d["progress"]=float(d.get("progress") or 0)
        return d

    def _emit(self,topic,payload):
        if not self.event_bus:return
        try:self.event_bus.publish(topic,payload,source="mission-engine")
        except Exception:pass

    def create(self,goal,project_id="KRISHNA",parent_mission_id=None,session_id=None,
               priority=50,assigned_agents=None,required_tools=None,
               permission_profile="default",resource_budget=None,metadata=None):
        goal=str(goal or "").strip()
        if not goal:raise ValueError("mission goal is required")
        mid=str(uuid.uuid4());now=time.time()
        with self.lock:
            self.db.execute("""INSERT INTO missions(
              mission_id,parent_mission_id,session_id,project_id,goal,status,priority,
              created_at,started_at,completed_at,current_step,progress,assigned_agents,
              required_tools,permission_profile,resource_budget,checkpoints,artifacts,
              evidence,errors,retry_count,verification_status,rollback_point,metadata,updated_at
            ) VALUES(?,?,?,?,?,'QUEUED',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
              mid,parent_mission_id,session_id,str(project_id or "KRISHNA"),goal,int(priority),
              now,None,None,"",0.0,json.dumps(list(assigned_agents or [])),
              json.dumps(list(required_tools or [])),str(permission_profile or "default"),
              json.dumps(dict(resource_budget or {})),json.dumps([]),json.dumps([]),
              json.dumps([]),json.dumps([]),0,"pending",None,json.dumps(dict(metadata or {})),now,
            ))
            self.db.commit()
        row=self.get(mid);self._emit("MISSION_CREATED",row);return row

    def get(self,mission_id):
        with self.lock:
            row=self.db.execute("SELECT * FROM missions WHERE mission_id=?",(str(mission_id),)).fetchone()
        return self._row(row)

    def list(self,project_id=None,status=None,limit=100):
        clauses=[];args=[]
        if project_id is not None:clauses.append("project_id=?");args.append(str(project_id))
        if status is not None:
            s=str(status).upper()
            if s not in MISSION_STATES:raise ValueError("invalid mission status")
            clauses.append("status=?");args.append(s)
        q="SELECT * FROM missions"+((" WHERE "+" AND ".join(clauses)) if clauses else "")+" ORDER BY updated_at DESC LIMIT ?"
        args.append(max(1,min(int(limit),1000)))
        with self.lock:rows=self.db.execute(q,args).fetchall()
        return [self._row(x) for x in rows]

    def transition(self,mission_id,status,*,current_step=None,progress=None,error=None,
                   verification_status=None,rollback_point=None,metadata_patch=None):
        status=str(status or "").upper()
        if status not in MISSION_STATES:raise ValueError("invalid mission status")
        row=self.get(mission_id)
        if not row:raise KeyError(mission_id)
        now=time.time();started=row.get("started_at");completed=row.get("completed_at")
        if status in {"PLANNING","RUNNING"} and started is None:started=now
        if status in _TERMINAL:completed=now
        errors=list(row["errors"])
        if error:errors.append({"at":now,"error":str(error)[:8000]})
        meta=dict(row["metadata"]);meta.update(dict(metadata_patch or {}))
        step=row["current_step"] if current_step is None else str(current_step)
        prog=row["progress"] if progress is None else max(0.0,min(float(progress),1.0))
        verify=row["verification_status"] if verification_status is None else str(verification_status)
        rb=row["rollback_point"] if rollback_point is None else rollback_point
        with self.lock:
            self.db.execute("""UPDATE missions SET status=?,started_at=?,completed_at=?,
              current_step=?,progress=?,errors=?,verification_status=?,rollback_point=?,
              metadata=?,updated_at=? WHERE mission_id=?""",(
              status,started,completed,step,prog,json.dumps(errors),verify,rb,
              json.dumps(meta),now,str(mission_id),
            ))
            self.db.commit()
        out=self.get(mission_id)
        event={"RUNNING":"MISSION_STARTED","COMPLETED":"MISSION_COMPLETED","FAILED":"MISSION_FAILED"}.get(status,"MISSION_UPDATED")
        self._emit(event,out)
        return out

    def append(self,mission_id,field,value):
        if field not in {"assigned_agents","required_tools","artifacts","evidence"}:
            raise ValueError("unsupported mission list field")
        row=self.get(mission_id)
        if not row:raise KeyError(mission_id)
        values=list(row[field]);values.append(value)
        with self.lock:
            self.db.execute(f"UPDATE missions SET {field}=?,updated_at=? WHERE mission_id=?",
                            (json.dumps(values),time.time(),str(mission_id)))
            self.db.commit()
        return self.get(mission_id)

    def increment_retry(self,mission_id,error=None):
        row=self.get(mission_id)
        if not row:raise KeyError(mission_id)
        with self.lock:
            self.db.execute("UPDATE missions SET retry_count=retry_count+1,updated_at=? WHERE mission_id=?",
                            (time.time(),str(mission_id)))
            self.db.commit()
        if error:self.transition(mission_id,row["status"],error=error)
        return self.get(mission_id)

    def checkpoint(self,mission_id,label,state=None,trusted=True):
        mission=self.get(mission_id)
        if not mission:raise KeyError(mission_id)
        now=time.time();cid=str(uuid.uuid4())
        with self.lock:
            seq=int(self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM mission_checkpoints WHERE mission_id=?",(mission_id,)).fetchone()[0])
            payload=dict(state or {})
            payload.setdefault("mission_status",mission["status"])
            payload.setdefault("current_step",mission["current_step"])
            payload.setdefault("progress",mission["progress"])
            self.db.execute("INSERT INTO mission_checkpoints VALUES(?,?,?,?,?,?,?)",
                            (cid,str(mission_id),seq,str(label or f"checkpoint-{seq}"),json.dumps(payload),1 if trusted else 0,now))
            cps=list(mission["checkpoints"]);cps.append(cid)
            self.db.execute("UPDATE missions SET checkpoints=?,rollback_point=?,updated_at=? WHERE mission_id=?",
                            (json.dumps(cps),cid if trusted else mission.get("rollback_point"),now,str(mission_id)))
            self.db.commit()
        row=self.checkpoint_get(cid);self._emit("CHECKPOINT_CREATED",row);return row

    def checkpoint_get(self,checkpoint_id):
        with self.lock:r=self.db.execute("SELECT * FROM mission_checkpoints WHERE checkpoint_id=?",(str(checkpoint_id),)).fetchone()
        if not r:return None
        d=dict(r);d["state"]=self._j(d["state"],{});d["trusted"]=bool(d["trusted"]);return d

    def checkpoints(self,mission_id,limit=100):
        with self.lock:rows=self.db.execute("SELECT * FROM mission_checkpoints WHERE mission_id=? ORDER BY seq DESC LIMIT ?",
                                            (str(mission_id),max(1,min(int(limit),1000)))).fetchall()
        return [self.checkpoint_get(x["checkpoint_id"]) for x in rows]

    def latest_trusted_checkpoint(self,mission_id):
        with self.lock:r=self.db.execute("""SELECT checkpoint_id FROM mission_checkpoints
            WHERE mission_id=? AND trusted=1 ORDER BY seq DESC LIMIT 1""",(str(mission_id),)).fetchone()
        return self.checkpoint_get(r[0]) if r else None

    def recover_interrupted(self):
        recovered=[]
        with self.lock:
            rows=self.db.execute("SELECT mission_id,status FROM missions WHERE status IN ('PLANNING','RUNNING','VERIFYING','ROLLING_BACK')").fetchall()
        for r in rows:
            cp=self.latest_trusted_checkpoint(r["mission_id"])
            recovered.append(self.transition(
                r["mission_id"],"WAITING",current_step="recovery_required",
                metadata_patch={"interrupted_status":r["status"],"recovered_at":time.time(),
                                "latest_trusted_checkpoint":cp["checkpoint_id"] if cp else None},
            ))
        return recovered

    def counts(self):
        with self.lock:rows=self.db.execute("SELECT status,COUNT(*) AS n FROM missions GROUP BY status").fetchall()
        counts={x:0 for x in MISSION_STATES};counts.update({r["status"]:r["n"] for r in rows})
        return counts

    def status(self):
        return {
            "owner":"KRISHNA Mission Engine","states":list(MISSION_STATES),
            "counts":self.counts(),"interrupted_states":sorted(_INTERRUPTED),
            "authority":"SQLite durable backend; UI connections are observers only",
        }

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None
