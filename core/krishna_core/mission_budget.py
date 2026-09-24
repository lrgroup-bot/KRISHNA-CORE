from __future__ import annotations

import json
import sqlite3
import time
from threading import RLock

DEFAULT_LIMITS={
    "max_wall_time":3600,
    "max_model_calls":40,
    "max_tool_calls":120,
    "max_subagents":8,
    "max_agent_depth":4,
    "max_context_tokens":128000,
    "max_retries":3,
    "max_cpu_percent":75,
    "max_ram_percent":80,
    "max_gpu_memory":0,
    "max_network_usage":0,
    "max_disk_growth":0,
}
_COUNTER_MAP={
    "model_calls":"max_model_calls","tool_calls":"max_tool_calls","subagents":"max_subagents",
    "context_tokens":"max_context_tokens","retries":"max_retries","network_usage":"max_network_usage",
    "disk_growth":"max_disk_growth",
}

class MissionBudgetManager:
    """Durable per-mission execution limits and usage counters."""

    def __init__(self,db_path):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS mission_budgets(
              mission_id TEXT PRIMARY KEY,
              limits_json TEXT NOT NULL,
              usage_json TEXT NOT NULL,
              started_at REAL NOT NULL,
              updated_at REAL NOT NULL
            )""")
            self.db.commit()

    @staticmethod
    def _loads(raw):
        try:
            value=json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"mission budget state is unreadable: {type(exc).__name__}") from exc
        if not isinstance(value,dict):
            raise RuntimeError("mission budget state is unreadable: expected JSON object")
        return value

    def configure(self,mission_id,limits=None):
        merged=dict(DEFAULT_LIMITS)
        for k,v in dict(limits or {}).items():
            if k in merged and v is not None:merged[k]=max(0,float(v))
        now=time.time()
        with self.lock:
            existing=self.db.execute("SELECT usage_json,started_at FROM mission_budgets WHERE mission_id=?",(str(mission_id),)).fetchone()
            usage=self._loads(existing["usage_json"]) if existing else {}
            started=float(existing["started_at"]) if existing else now
            self.db.execute("""INSERT INTO mission_budgets(mission_id,limits_json,usage_json,started_at,updated_at)
              VALUES(?,?,?,?,?) ON CONFLICT(mission_id) DO UPDATE SET limits_json=excluded.limits_json,updated_at=excluded.updated_at""",
              (str(mission_id),json.dumps(merged),json.dumps(usage),started,now))
            self.db.commit()
        return self.status(mission_id)

    def status(self,mission_id):
        with self.lock:r=self.db.execute("SELECT * FROM mission_budgets WHERE mission_id=?",(str(mission_id),)).fetchone()
        if not r:return None
        limits=self._loads(r["limits_json"]);usage=self._loads(r["usage_json"])
        elapsed=max(0.0,time.time()-float(r["started_at"]))
        exceeded=[]
        wall=float(limits.get("max_wall_time") or 0)
        if wall>0 and elapsed>wall:exceeded.append("max_wall_time")
        for counter,limit_name in _COUNTER_MAP.items():
            limit=float(limits.get(limit_name) or 0)
            if limit>0 and float(usage.get(counter) or 0)>limit:exceeded.append(limit_name)
        return {"mission_id":r["mission_id"],"limits":limits,"usage":usage,"elapsed_seconds":elapsed,
                "exceeded":sorted(set(exceeded)),"allowed":not exceeded,"started_at":r["started_at"],"updated_at":r["updated_at"]}

    def consume(self,mission_id,counter,amount=1):
        counter=str(counter)
        if counter not in _COUNTER_MAP:raise ValueError("unsupported mission budget counter")
        amount=float(amount)
        if amount<0:raise ValueError("mission budget consumption cannot be negative")
        row=self.status(mission_id)
        if row is None:row=self.configure(mission_id)
        usage=dict(row["usage"]);usage[counter]=float(usage.get(counter) or 0)+amount
        with self.lock:
            self.db.execute("UPDATE mission_budgets SET usage_json=?,updated_at=? WHERE mission_id=?",
                            (json.dumps(usage),time.time(),str(mission_id)));self.db.commit()
        status=self.status(mission_id)
        if not status["allowed"]:
            raise RuntimeError("mission resource budget exceeded: "+",".join(status["exceeded"]))
        return status

    def assert_allowed(self,mission_id,*,cpu_percent=None,ram_percent=None,gpu_memory=None):
        row=self.status(mission_id)
        if row is None:row=self.configure(mission_id)
        exceeded=list(row["exceeded"]);limits=row["limits"]
        checks=(("max_cpu_percent",cpu_percent),("max_ram_percent",ram_percent),("max_gpu_memory",gpu_memory))
        for key,value in checks:
            limit=float(limits.get(key) or 0)
            if value is not None and limit>0 and float(value)>limit:exceeded.append(key)
        if exceeded:raise RuntimeError("mission resource budget exceeded: "+",".join(sorted(set(exceeded))))
        return {**row,"allowed":True}

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None
