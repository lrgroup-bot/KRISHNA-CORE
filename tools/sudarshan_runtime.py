"""Local-only SUDARSHAN pipeline runner.

Executes configured local adapters in sequence, records evidence and stops on failure.
No automatic code modification, merge, release or rollback.
"""
from .sudarshan_execution_contract import ENGINES,prepare_handoff,readiness
from .sudarshan_local_adapters import run_adapter
from .sudarshan_knowledge_store import connect,record

ORDER=("REA","MiroFish","BRAHMAGYAN","VISHWAKARMA","UI_GUARDIAN","MRITYUNJAYA")

def run_pipeline(project_id,feature_id,authorized,config,db_path):
    if not authorized:raise PermissionError("owner authorization required")
    if not project_id or not feature_id:raise ValueError("project and feature required")
    if not isinstance(config,dict):raise TypeError("adapter configuration required")
    if set(config)-ENGINES:raise ValueError("unknown adapter")
    db=connect(db_path)
    results=[]
    try:
        for engine in ORDER:
            entry=config.get(engine)
            if entry is None:break
            if not isinstance(entry,dict):raise ValueError("adapter settings must be an object")
            result=run_adapter(engine,entry["argv"],authorized=True,cwd=entry["cwd"],
                               timeout=entry.get("timeout",60))
            record(db,project_id,feature_id,result)
            results.append(result)
            if result.status!="passed":break
        handoff=prepare_handoff(project_id,feature_id,True,results)
        return {"handoff":handoff,"readiness":readiness(handoff),
                "completed_engines":[x.engine for x in results],
                "execution_stopped":len(results)<len(ORDER) or any(x.status!="passed" for x in results)}
    finally:
        db.close()
