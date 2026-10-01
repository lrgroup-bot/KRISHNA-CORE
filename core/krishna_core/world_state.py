from __future__ import annotations
import json, sqlite3, time, uuid
from threading import RLock

class WorldStateLedger:
    """Persistent observations. Current state is derived only from fresh observations."""
    def __init__(self,db_path):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False);self.db.row_factory=sqlite3.Row;self.lock=RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS world_observations(
              observation_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, property_name TEXT NOT NULL,
              value_json TEXT NOT NULL, reality_level TEXT NOT NULL, observer TEXT NOT NULL,
              source_family TEXT NOT NULL, observed_at REAL NOT NULL, ttl_seconds REAL,
              context TEXT NOT NULL, evidence_ref TEXT NOT NULL, unit TEXT NOT NULL,
              precision REAL, calibration_ref TEXT NOT NULL, frame_ref TEXT NOT NULL, created_at REAL NOT NULL)""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_world_current ON world_observations(object_id,property_name,observed_at DESC)")
            self.db.commit()
    def observe(self,object_id,property_name,value,*,reality_level,observer,source_family,observed_at=None,ttl_seconds=None,context="",evidence_ref="",unit="",precision=None,calibration_ref="",frame_ref=""):
        if not str(object_id).strip() or not str(property_name).strip():raise ValueError("object_id and property_name required")
        oid=str(uuid.uuid4());now=time.time();at=float(observed_at or now)
        with self.lock:
            self.db.execute("INSERT INTO world_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(oid,str(object_id),str(property_name),json.dumps(value,ensure_ascii=False),str(reality_level),str(observer),str(source_family),at,None if ttl_seconds is None else float(ttl_seconds),str(context),str(evidence_ref),str(unit),precision,str(calibration_ref),str(frame_ref),now));self.db.commit()
        return self.get(oid)
    def get(self,observation_id):
        with self.lock:r=self.db.execute("SELECT * FROM world_observations WHERE observation_id=?",(str(observation_id),)).fetchone()
        if not r:return None
        d=dict(r);d["value"]=json.loads(d.pop("value_json"));ttl=d.get("ttl_seconds");d["stale"]=bool(ttl is not None and time.time()-float(d["observed_at"])>max(0.0,float(ttl)));return d
    def current(self,object_id,property_name):
        with self.lock:rows=self.db.execute("SELECT observation_id FROM world_observations WHERE object_id=? AND property_name=? ORDER BY observed_at DESC LIMIT 100",(str(object_id),str(property_name))).fetchall()
        fresh=[self.get(x[0]) for x in rows];fresh=[x for x in fresh if x and not x["stale"]]
        if not fresh:return {"state":"unknown","observations":[]}
        values={json.dumps(x["value"],sort_keys=True) for x in fresh[:4]}
        return {"state":"conflicted" if len(values)>1 else "current","value":fresh[0]["value"],"observations":fresh[:4]}
    def close(self):
        with self.lock:self.db.commit();self.db.close()
