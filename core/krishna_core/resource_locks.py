from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path
from threading import RLock

LOCK_TYPES=("EXACT_LOCK","TREE_LOCK","PROJECT_LOCK","REPOSITORY_LOCK","DATABASE_LOCK","MODEL_LOCK","DEPLOYMENT_LOCK")
MODES=("read","write")

class ResourceLockManager:
    """Durable lock manager for concurrent KRISHNA missions/agents."""

    def __init__(self,db_path,default_ttl=900,event_bus=None):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        self.default_ttl=max(30,int(default_ttl))
        self.event_bus=event_bus
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS resource_locks(
              lock_id TEXT PRIMARY KEY,
              lock_type TEXT NOT NULL,
              target TEXT NOT NULL,
              mode TEXT NOT NULL,
              owner_token TEXT NOT NULL,
              mission_id TEXT,
              agent_id TEXT,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              expires_at REAL NOT NULL,
              metadata TEXT NOT NULL DEFAULT '{}'
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_resource_locks_target ON resource_locks(lock_type,target,expires_at)")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_resource_locks_owner ON resource_locks(owner_token,expires_at)")
            self.db.commit()

    @staticmethod
    def _norm_target(lock_type,target):
        raw=str(target or "").strip()
        if not raw:raise ValueError("lock target is required")
        if lock_type in {"EXACT_LOCK","TREE_LOCK"}:
            return os.path.normcase(str(Path(raw).expanduser().resolve()))
        return raw.strip().lower()

    @staticmethod
    def _path_overlap(a_type,a,b_type,b):
        if a_type=="EXACT_LOCK" and b_type=="EXACT_LOCK":return a==b
        if a_type=="TREE_LOCK" and b_type=="TREE_LOCK":
            return a==b or a.startswith(b+os.sep) or b.startswith(a+os.sep)
        tree,target=(a,b) if a_type=="TREE_LOCK" else (b,a)
        return target==tree or target.startswith(tree+os.sep)

    @classmethod
    def _conflicts(cls,requested,existing):
        if requested["owner_token"]==existing["owner_token"]:return False
        if requested["mode"]=="read" and existing["mode"]=="read":return False
        rt,et=requested["lock_type"],existing["lock_type"]
        if rt in {"EXACT_LOCK","TREE_LOCK"} and et in {"EXACT_LOCK","TREE_LOCK"}:
            return cls._path_overlap(rt,requested["target"],et,existing["target"])
        if rt==et:return requested["target"]==existing["target"]
        # A project/repository/deployment write lock protects the same logical target namespace.
        logical={"PROJECT_LOCK","REPOSITORY_LOCK","DEPLOYMENT_LOCK"}
        if rt in logical and et in logical:return requested["target"]==existing["target"]
        return False

    def cleanup_stale(self):
        now=time.time()
        with self.lock:
            cur=self.db.execute("DELETE FROM resource_locks WHERE expires_at<=?",(now,))
            self.db.commit()
            return int(cur.rowcount or 0)

    def list(self,active_only=True,limit=500):
        if active_only:self.cleanup_stale()
        q="SELECT * FROM resource_locks"
        args=[]
        if active_only:q+=" WHERE expires_at>?";args.append(time.time())
        q+=" ORDER BY created_at LIMIT ?";args.append(max(1,min(int(limit),2000)))
        with self.lock:rows=self.db.execute(q,args).fetchall()
        return [dict(x) for x in rows]

    def acquire(self,lock_type,target,*,mode="write",owner_token=None,mission_id=None,agent_id=None,ttl=None,metadata=None):
        lt=str(lock_type or "").upper();mode=str(mode or "").lower()
        if lt not in LOCK_TYPES:raise ValueError("invalid lock type")
        if mode not in MODES:raise ValueError("lock mode must be read or write")
        owner=str(owner_token or uuid.uuid4())
        normalized=self._norm_target(lt,target);now=time.time();expires=now+max(30,int(ttl or self.default_ttl))
        requested={"lock_type":lt,"target":normalized,"mode":mode,"owner_token":owner}
        with self.lock:
            self.db.execute("DELETE FROM resource_locks WHERE expires_at<=?",(now,))
            rows=[dict(x) for x in self.db.execute("SELECT * FROM resource_locks").fetchall()]
            conflicts=[x for x in rows if self._conflicts(requested,x)]
            if conflicts:
                self.db.commit()
                raise RuntimeError("resource lock conflict: "+",".join(x["lock_id"] for x in conflicts))
            lock_id=str(uuid.uuid4())
            import json
            self.db.execute("INSERT INTO resource_locks VALUES(?,?,?,?,?,?,?,?,?,?)",(
                lock_id,lt,normalized,mode,owner,mission_id,agent_id,now,now,expires,json.dumps(dict(metadata or {}))
            ))
            self.db.commit()
        row=self.get(lock_id)
        if self.event_bus:
            try:self.event_bus.publish("LOCK_ACQUIRED",row,source="resource-locks")
            except Exception:pass
        return row

    def get(self,lock_id):
        with self.lock:r=self.db.execute("SELECT * FROM resource_locks WHERE lock_id=?",(str(lock_id),)).fetchone()
        return dict(r) if r else None

    def renew(self,lock_id,owner_token,ttl=None):
        row=self.get(lock_id)
        if not row:raise KeyError(lock_id)
        if row["owner_token"]!=str(owner_token):raise PermissionError("resource lock owner mismatch")
        now=time.time()
        with self.lock:
            self.db.execute("UPDATE resource_locks SET updated_at=?,expires_at=? WHERE lock_id=?",
                            (now,now+max(30,int(ttl or self.default_ttl)),str(lock_id)))
            self.db.commit()
        return self.get(lock_id)

    def release(self,lock_id,owner_token):
        row=self.get(lock_id)
        if not row:return False
        if row["owner_token"]!=str(owner_token):raise PermissionError("resource lock owner mismatch")
        with self.lock:
            self.db.execute("DELETE FROM resource_locks WHERE lock_id=?",(str(lock_id),));self.db.commit()
        if self.event_bus:
            try:self.event_bus.publish("LOCK_RELEASED",row,source="resource-locks")
            except Exception:pass
        return True

    def release_owner(self,owner_token):
        with self.lock:
            cur=self.db.execute("DELETE FROM resource_locks WHERE owner_token=?",(str(owner_token),));self.db.commit()
            return int(cur.rowcount or 0)

    def status(self):
        rows=self.list()
        return {"owner":"KRISHNA Resource Lock Manager","types":list(LOCK_TYPES),"modes":list(MODES),
                "active":len(rows),"locks":rows,
                "policy":"read/read may coexist; overlapping writes are blocked; stale leases are cleaned automatically"}

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None
