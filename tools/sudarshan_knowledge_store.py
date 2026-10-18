"""Local append-only evidence store for agent handoffs. No external dependencies."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

def connect(path):
    db=sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS agent_evidence (
      digest TEXT PRIMARY KEY, project_id TEXT NOT NULL, feature_id TEXT NOT NULL,
      engine TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL,
      evidence_id TEXT NOT NULL, created_at TEXT NOT NULL)""")
    return db

def record(db, project_id, feature_id, result):
    from .sudarshan_execution_contract import validate_result
    validate_result(result)
    if not project_id.strip() or not feature_id.strip():
        raise ValueError("project and feature required")
    payload=dict(project_id=project_id,feature_id=feature_id,engine=result.engine,
                 status=result.status,summary=result.summary,evidence_id=result.evidence_id)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    with db:
        db.execute("INSERT OR IGNORE INTO agent_evidence VALUES (?,?,?,?,?,?,?,?)",
                   (digest,project_id,feature_id,result.engine,result.status,result.summary,
                    result.evidence_id,datetime.now(timezone.utc).isoformat()))
    return digest

def history(db, project_id, feature_id):
    rows=db.execute("""SELECT digest,engine,status,summary,evidence_id,created_at
       FROM agent_evidence WHERE project_id=? AND feature_id=? ORDER BY created_at,digest""",
       (project_id,feature_id)).fetchall()
    return [dict(zip(("digest","engine","status","summary","evidence_id","created_at"),r)) for r in rows]
