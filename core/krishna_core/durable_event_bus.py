from __future__ import annotations

import json
import sqlite3
import time
import uuid
from threading import RLock

LIFECYCLE_EVENTS=frozenset({
    "SESSION_STARTED","SESSION_ENDED","MISSION_CREATED","MISSION_STARTED","MISSION_COMPLETED","MISSION_FAILED",
    "PLAN_CREATED","PLAN_UPDATED","AGENT_SPAWNED","AGENT_FINISHED","AGENT_FAILED",
    "BEFORE_MODEL","AFTER_MODEL","BEFORE_TOOL","AFTER_TOOL","TOOL_ERROR",
    "BEFORE_FILE_WRITE","AFTER_FILE_WRITE","BEFORE_GIT_CHANGE","AFTER_GIT_CHANGE",
    "TEST_STARTED","TEST_PASSED","TEST_FAILED","BUILD_STARTED","BUILD_COMPLETED","BUILD_FAILED",
    "SERVICE_RESTARTED","VERIFICATION_STARTED","VERIFICATION_PASSED","VERIFICATION_FAILED",
    "CONTEXT_COMPACTED","CHECKPOINT_CREATED","ROLLBACK_STARTED","ROLLBACK_COMPLETED","SUDARSHAN_ALERT",
    "MISSION_UPDATED","QUEUE_ENQUEUED","QUEUE_CLAIMED","QUEUE_ACKED","QUEUE_REQUEUED","QUEUE_FAILED","QUEUE_RECOVERED",
})

class DurableEventBus:
    """Persistent KRISHNA lifecycle event journal with compatibility fan-out."""

    def __init__(self,db_path,compatibility_bus=None,history_limit=5000):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        self.compatibility_bus=compatibility_bus
        self.history_limit=max(500,int(history_limit))
        self._subs={}
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS lifecycle_events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              topic TEXT NOT NULL,
              payload TEXT NOT NULL DEFAULT '{}',
              source TEXT NOT NULL,
              created_at REAL NOT NULL
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_events_topic_seq ON lifecycle_events(topic,seq)")
            self.db.commit()

    @staticmethod
    def _row(row):
        if not row:return None
        d=dict(row)
        try:d["payload"]=json.loads(d["payload"])
        except Exception:d["payload"]={}
        return d

    def subscribe(self,topic,handler):
        self._subs.setdefault(str(topic),[]).append(handler)

    def unsubscribe(self,topic,handler):
        handlers=self._subs.get(str(topic),[])
        if handler in handlers:handlers.remove(handler)

    def publish(self,topic,payload=None,source="krishna"):
        topic=str(topic or "").strip()
        if not topic:raise ValueError("event topic is required")
        ev={"event_id":str(uuid.uuid4()),"topic":topic,"payload":dict(payload or {}),
            "source":str(source or "krishna"),"created_at":time.time()}
        with self.lock:
            cur=self.db.execute("INSERT INTO lifecycle_events(event_id,topic,payload,source,created_at) VALUES(?,?,?,?,?)",
                                (ev["event_id"],topic,json.dumps(ev["payload"]),ev["source"],ev["created_at"]))
            ev["seq"]=cur.lastrowid
            self.db.execute("""DELETE FROM lifecycle_events WHERE seq < (
              SELECT COALESCE(MAX(seq),0)-? FROM lifecycle_events)""",(self.history_limit,))
            self.db.commit()
        results=[]
        for h in tuple(self._subs.get(topic,[]))+tuple(self._subs.get("*",[])):
            try:results.append(h(dict(ev)))
            except Exception as exc:results.append({"error":f"{type(exc).__name__}: {exc}"})
        if self.compatibility_bus:
            try:self.compatibility_bus.publish(topic,ev["payload"],source=ev["source"])
            except Exception:pass
        return {"event":ev,"results":results}

    def recent(self,topic=None,limit=100,after_seq=None):
        clauses=[];args=[]
        if topic is not None:clauses.append("topic=?");args.append(str(topic))
        if after_seq is not None:clauses.append("seq>?");args.append(int(after_seq))
        q="SELECT * FROM lifecycle_events"+((" WHERE "+" AND ".join(clauses)) if clauses else "")+" ORDER BY seq DESC LIMIT ?"
        args.append(max(1,min(int(limit),1000)))
        with self.lock:rows=self.db.execute(q,args).fetchall()
        return [self._row(x) for x in reversed(rows)]

    def count(self):
        with self.lock:return int(self.db.execute("SELECT COUNT(*) FROM lifecycle_events").fetchone()[0])

    def status(self):
        return {"owner":"KRISHNA Durable Event Bus","persistent":True,"events":self.count(),
                "lifecycle_events":sorted(LIFECYCLE_EVENTS),
                "compatibility_fanout":bool(self.compatibility_bus)}

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None
