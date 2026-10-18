"""Fail-closed local orchestration of explicitly configured adapters."""
from .sudarshan_execution_contract import ENGINES,prepare_handoff,readiness
from .sudarshan_local_adapters import run_adapter
from .sudarshan_knowledge_store import connect,record

ORDER=("REA","MiroFish","BRAHMAGYAN","VISHWAKARMA","UI_GUARDIAN","MRITYUNJAYA")

def run_pipeline(project_id,feature_id,authorized,config,db_path):
    if not authorized:
        raise PermissionError("owner authorization required")
    if not isinstance(project_id,str) or not project_id.strip() or not isinstance(feature_id,str) or not feature_id.strip():
        raise ValueError("project and feature required")
    if not isinstance(config,dict):
        raise TypeError("adapter configuration required")
    if set(config)-ENGINES:
        raise ValueError("unknown adapter")
    # Reject incomplete or malformed plans before starting any external process.
    for engine in ORDER:
        entry=config.get(engine)
        if not isinstance(entry,dict):
            raise ValueError("missing or malformed adapter: "+engine)
        if not isinstance(entry.get("argv"),(list,tuple)) or not entry["argv"]:
            raise ValueError("missing adapter argv: "+engine)
        if not isinstance(entry.get("cwd"),str):
            raise ValueError("missing adapter cwd: "+engine)
    db=connect(db_path)
    results=[]
    try:
        for engine in ORDER:
            entry=config[engine]
            result=run_adapter(engine,entry["argv"],authorized=True,cwd=entry["cwd"],
                               timeout=entry.get("timeout",60))
            record(db,project_id,feature_id,result)
            results.append(result)
            if result.status!="passed":
                break
        handoff=prepare_handoff(project_id,feature_id,True,results)
        return {"handoff":handoff,"readiness":readiness(handoff),
                "completed_engines":[x.engine for x in results],
                "execution_stopped":len(results)<len(ORDER) or any(x.status!="passed" for x in results),
                "deployment_allowed":False}
    finally:
        db.close()
