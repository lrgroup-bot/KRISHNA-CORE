"""Persistent daily PARIKSHA examination orchestration.

The examiner stores score history and failure fingerprints. It never writes exam answers
into learner memory before scoring, and improvement requires delayed/unseen transfer.
"""
from __future__ import annotations
import json,sqlite3,time,uuid
from .pariksha import ABILITIES,capability_report,next_difficulty

class ParikshaLedger:
    def __init__(self,path):
        self.db=sqlite3.connect(str(path),check_same_thread=False);self.db.row_factory=sqlite3.Row
        self.db.executescript("""CREATE TABLE IF NOT EXISTS pariksha_runs(
        run_id TEXT PRIMARY KEY,domain TEXT NOT NULL,examiner TEXT NOT NULL,started_at REAL NOT NULL,
        completed_at REAL,kcci REAL,difficulty REAL NOT NULL,abilities TEXT NOT NULL,failures TEXT NOT NULL,
        unseen_ratio REAL NOT NULL,transfer_score REAL,calibration REAL,status TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_pariksha_domain_time ON pariksha_runs(domain,started_at DESC);
        CREATE TABLE IF NOT EXISTS pariksha_retests(
        retest_id TEXT PRIMARY KEY,parent_run_id TEXT NOT NULL,due_at REAL NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
        ability TEXT NOT NULL,reason TEXT NOT NULL,created_at REAL NOT NULL,completed_at REAL);""");self.db.commit()
    def record(self,*,domain,examiner,scores,difficulty,failures=(),unseen_ratio=1.0,transfer_score=None,calibration=None):
        unseen=max(0,min(1,float(unseen_ratio)))
        if unseen<.8: raise ValueError("daily capability run requires >=80% unseen items")
        previous=self.latest(domain);r=capability_report(scores,previous=previous["kcci"] if previous else None,difficulty=difficulty)
        rid=str(uuid.uuid4());now=time.time()
        self.db.execute("INSERT INTO pariksha_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,domain,examiner,now,now,r["kcci"],r["difficulty"],json.dumps(r["abilities"]),json.dumps(list(failures)),unseen,None if transfer_score is None else float(transfer_score),None if calibration is None else float(calibration),"completed"));self.db.commit()
        out=dict(r);out.update({"run_id":rid,"domain":domain,"examiner":examiner,"unseen_ratio":unseen,"failures":list(failures)})
        return out
    def latest(self,domain):
        r=self.db.execute("SELECT * FROM pariksha_runs WHERE domain=? AND status='completed' ORDER BY started_at DESC LIMIT 1",(domain,)).fetchone()
        if not r:return None
        d=dict(r);d["abilities"]=json.loads(d["abilities"]);d["failures"]=json.loads(d["failures"]);return d
    def history(self,domain,limit=30):
        rows=self.db.execute("SELECT * FROM pariksha_runs WHERE domain=? ORDER BY started_at DESC LIMIT ?",(domain,max(1,min(int(limit),365)))).fetchall()
        return [dict(x) for x in rows]
    def schedule_retests(self,run_id,failures,delay_seconds=86400):
        now=time.time();out=[]
        for f in failures:
            rid=str(uuid.uuid4());ability=str(f.get("ability","reasoning"));reason=str(f.get("failure_type","unknown"))
            self.db.execute("INSERT INTO pariksha_retests VALUES(?,?,?,?,?,?,?,NULL)",(rid,run_id,now+max(3600,float(delay_seconds)),"pending",ability,reason,now));out.append(rid)
        self.db.commit();return out
    def due_retests(self,now=None):
        rows=self.db.execute("SELECT * FROM pariksha_retests WHERE status='pending' AND due_at<=? ORDER BY due_at",(float(now or time.time()),)).fetchall()
        return [dict(x) for x in rows]
    def training_plan(self,report):
        abilities=report.get("abilities",{});ordered=sorted(abilities.items(),key=lambda x:x[1])
        return [{"ability":k,"score":v,"action":"research+generated_variants+delayed_unseen_retest"} for k,v in ordered[:3]]
    def owner_dashboard(self,domain):
        latest=self.latest(domain);hist=self.history(domain,7)
        if not latest:return {"domain":domain,"state":"no_measured_run"}
        return {"domain":domain,"state":"measured","latest_kcci":latest["kcci"],"difficulty":latest["difficulty"],
                "unseen_ratio":latest["unseen_ratio"],"abilities":latest["abilities"],"failures":latest["failures"],
                "recent_kcci":[x["kcci"] for x in reversed(hist)]}
    def close(self):self.db.commit();self.db.close()
