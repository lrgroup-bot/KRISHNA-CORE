from __future__ import annotations
import hashlib,json,sqlite3,time
class MissionReplayLedger:
    def __init__(self,path):
        self.db=sqlite3.connect(str(path));self.db.execute("CREATE TABLE IF NOT EXISTS mission_replay(mission TEXT,step TEXT,parent TEXT,agent TEXT,tool TEXT,input_hash TEXT,result_hash TEXT,state TEXT,evidence TEXT,created REAL,PRIMARY KEY(mission,step))");self.db.commit()
    @staticmethod
    def _hash(v):return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()
    def record(self,mission,step,*,parent="",agent="",tool="",inputs=None,result=None,state="completed",evidence=None):
        row=(mission,step,parent,agent,tool,self._hash(inputs or {}),self._hash(result or {}),state,json.dumps(evidence or [],default=str),time.time())
        self.db.execute("INSERT OR REPLACE INTO mission_replay VALUES(?,?,?,?,?,?,?,?,?,?)",row);self.db.commit();return {"mission":mission,"step":step,"state":state,"input_hash":row[5],"result_hash":row[6]}
    def resume_point(self,mission):
        rows=self.db.execute("SELECT step,state,created FROM mission_replay WHERE mission=? ORDER BY created",(mission,)).fetchall()
        done=[r for r in rows if r[1]=="completed"];return {"mission":mission,"last_verified_step":done[-1][0] if done else None,"steps":len(rows)}
