from __future__ import annotations

import json
import sqlite3
import time
import uuid
from threading import RLock

QUEUE_STATES=("pending","processing","completed","failed","cancelled")

class DurableQueue:
    """Backend-owned durable mission queue with claim/ACK semantics.

    Completion is determined from SQLite queue state, never from process-local counters.
    Processing items carry leases so interrupted workers can be reclaimed after restart.
    """

    def __init__(self,db_path,event_bus=None,lease_seconds=300):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        self.event_bus=event_bus
        self.lease_seconds=max(15,int(lease_seconds))
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS durable_queue(
              queue_id TEXT PRIMARY KEY,
              mission_id TEXT,
              action TEXT NOT NULL,
              payload TEXT NOT NULL DEFAULT '{}',
              project TEXT NOT NULL DEFAULT 'KRISHNA',
              actor TEXT NOT NULL DEFAULT 'job-runtime',
              permissions TEXT NOT NULL DEFAULT '[]',
              approved INTEGER NOT NULL DEFAULT 0,
              idempotency_key TEXT,
              state TEXT NOT NULL,
              retry_count INTEGER NOT NULL DEFAULT 0,
              max_retries INTEGER NOT NULL DEFAULT 2,
              lease_owner TEXT,
              lease_expires_at REAL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              acked_at REAL,
              last_error TEXT,
              result TEXT
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_durable_queue_state ON durable_queue(state,created_at)")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_durable_queue_mission ON durable_queue(mission_id,state)")
            self.db.commit()

    @staticmethod
    def _loads(value,default,field,expected_type=None):
        if value is None:
            parsed=default
        else:
            try:parsed=json.loads(value)
            except Exception as exc:
                raise RuntimeError(f"durable queue {field} state is unreadable") from exc
        if expected_type is not None and not isinstance(parsed,expected_type):
            raise RuntimeError(f"durable queue {field} state has invalid type")
        return parsed

    @classmethod
    def _row(cls,row):
        if not row:return None
        d=dict(row)
        d["payload"]=cls._loads(d.get("payload"),{},"payload",dict)
        d["permissions"]=cls._loads(d.get("permissions"),[],"permissions",list)
        d["result"]=cls._loads(d.get("result"),None,"result")
        d["approved"]=bool(d.get("approved"))
        return d

    def _emit(self,topic,payload):
        if not self.event_bus:return
        try:self.event_bus.publish(topic,payload,source="durable-queue")
        except Exception:pass

    def enqueue(self,action,payload=None,*,mission_id=None,project="KRISHNA",actor="job-runtime",
                permissions=(),approved=False,idempotency_key=None,max_retries=2):
        action=str(action or "").strip()
        if not action:raise ValueError("queue action is required")
        now=time.time();qid=str(uuid.uuid4())
        with self.lock:
            self.db.execute("""INSERT INTO durable_queue(
              queue_id,mission_id,action,payload,project,actor,permissions,approved,
              idempotency_key,state,retry_count,max_retries,lease_owner,lease_expires_at,
              created_at,updated_at,acked_at,last_error,result
            ) VALUES(?,?,?,?,?,?,?,?,?,'pending',0,?,?,?,?,?,?,?,?)""",(
              qid,mission_id,action,json.dumps(dict(payload or {})),str(project or "KRISHNA"),
              str(actor or "job-runtime"),json.dumps(list(permissions or [])),1 if approved else 0,
              idempotency_key,max(0,int(max_retries)),None,None,now,now,None,None,None,
            ))
            self.db.commit()
        row=self.get(qid);self._emit("QUEUE_ENQUEUED",row);return row

    def get(self,queue_id):
        with self.lock:r=self.db.execute("SELECT * FROM durable_queue WHERE queue_id=?",(str(queue_id),)).fetchone()
        return self._row(r)

    def list(self,state=None,mission_id=None,limit=100):
        clauses=[];args=[]
        if state is not None:
            s=str(state).lower()
            if s not in QUEUE_STATES:raise ValueError("invalid queue state")
            clauses.append("state=?");args.append(s)
        if mission_id is not None:clauses.append("mission_id=?");args.append(str(mission_id))
        q="SELECT * FROM durable_queue"+((" WHERE "+" AND ".join(clauses)) if clauses else "")+" ORDER BY created_at LIMIT ?"
        args.append(max(1,min(int(limit),1000)))
        with self.lock:rows=self.db.execute(q,args).fetchall()
        return [self._row(x) for x in rows]

    def claim(self,worker_id,queue_id=None,lease_seconds=None):
        owner=str(worker_id or "").strip()
        if not owner:raise ValueError("worker_id is required")
        lease=max(15,int(lease_seconds or self.lease_seconds));now=time.time()
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if queue_id:
                    row=self.db.execute("SELECT * FROM durable_queue WHERE queue_id=? AND state='pending'",(str(queue_id),)).fetchone()
                else:
                    row=self.db.execute("SELECT * FROM durable_queue WHERE state='pending' ORDER BY created_at LIMIT 1").fetchone()
                if not row:
                    self.db.commit();return None
                self.db.execute("""UPDATE durable_queue SET state='processing',lease_owner=?,lease_expires_at=?,updated_at=?
                                  WHERE queue_id=? AND state='pending'""",
                                (owner,now+lease,now,row["queue_id"]))
                self.db.commit()
            except Exception:
                self.db.rollback();raise
        out=self.get(row["queue_id"]);self._emit("QUEUE_CLAIMED",out);return out

    def ack(self,queue_id,result=None,worker_id=None):
        row=self.get(queue_id)
        if not row:raise KeyError(queue_id)
        if row["state"]!="processing":raise ValueError("only processing queue items can be ACKed")
        if worker_id and row.get("lease_owner") not in (None,str(worker_id)):
            raise PermissionError("queue lease owner mismatch")
        now=time.time()
        with self.lock:
            self.db.execute("""UPDATE durable_queue SET state='completed',result=?,acked_at=?,
                              lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE queue_id=?""",
                            (json.dumps(result),now,now,str(queue_id)))
            self.db.commit()
        out=self.get(queue_id);self._emit("QUEUE_ACKED",out);return out

    def fail(self,queue_id,error,*,requeue=True,worker_id=None):
        row=self.get(queue_id)
        if not row:raise KeyError(queue_id)
        if row["state"] not in {"processing","pending"}:raise ValueError("queue item cannot fail from current state")
        if worker_id and row.get("lease_owner") not in (None,str(worker_id)):
            raise PermissionError("queue lease owner mismatch")
        retry=int(row["retry_count"])+1
        state="pending" if requeue and retry<=int(row["max_retries"]) else "failed"
        now=time.time()
        with self.lock:
            self.db.execute("""UPDATE durable_queue SET state=?,retry_count=?,last_error=?,
                              lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE queue_id=?""",
                            (state,retry,str(error)[:8000],now,str(queue_id)))
            self.db.commit()
        out=self.get(queue_id);self._emit("QUEUE_REQUEUED" if state=="pending" else "QUEUE_FAILED",out);return out

    def cancel(self,queue_id):
        row=self.get(queue_id)
        if not row:raise KeyError(queue_id)
        if row["state"] in {"completed","failed","cancelled"}:return row
        with self.lock:
            self.db.execute("UPDATE durable_queue SET state='cancelled',lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE queue_id=?",
                            (time.time(),str(queue_id)));self.db.commit()
        return self.get(queue_id)

    def recover_stale_processing(self,force=False):
        now=time.time();recovered=[]
        with self.lock:
            rows=self.db.execute("""SELECT queue_id FROM durable_queue WHERE state='processing'
                                    AND (?=1 OR lease_expires_at IS NULL OR lease_expires_at<=?)""",
                                 (1 if force else 0,now)).fetchall()
        for r in rows:
            recovered.append(self.fail(r["queue_id"],"worker_interrupted_or_lease_expired",requeue=True))
        if recovered:self._emit("QUEUE_RECOVERED",{"count":len(recovered),"items":[x["queue_id"] for x in recovered]})
        return recovered

    def counts(self):
        with self.lock:rows=self.db.execute("SELECT state,COUNT(*) AS n FROM durable_queue GROUP BY state").fetchall()
        counts={x:0 for x in QUEUE_STATES};counts.update({r["state"]:r["n"] for r in rows})
        counts["unacked"]=counts["processing"]
        counts["requeued"]=int(self.db.execute("SELECT COUNT(*) FROM durable_queue WHERE retry_count>0").fetchone()[0])
        counts["retry_count"]=int(self.db.execute("SELECT COALESCE(SUM(retry_count),0) FROM durable_queue").fetchone()[0])
        return counts

    def drained(self):
        c=self.counts()
        return c["pending"]==0 and c["processing"]==0

    def mission_drained(self,mission_id):
        with self.lock:r=self.db.execute("""SELECT
          SUM(CASE WHEN state='pending' THEN 1 ELSE 0 END),
          SUM(CASE WHEN state='processing' THEN 1 ELSE 0 END)
          FROM durable_queue WHERE mission_id=?""",(str(mission_id),)).fetchone()
        return int(r[0] or 0)==0 and int(r[1] or 0)==0

    def status(self):
        c=self.counts()
        return {
            "owner":"KRISHNA Durable Queue","lifecycle":["enqueue","pending","processing","ACK","removed/logically completed"],
            **c,"drained":c["pending"]==0 and c["processing"]==0,
            "completion_rule":"pending == 0 AND processing == 0",
            "authority":"SQLite backend state",
        }

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None
