"""Original GARUDA Repair Studio extended features, offline and append-only.

Catalog, part fitment, troubleshooting, guide feedback, Q&A and Rishi review
handoff. This module performs no device operations or automatic promotion.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import re

def _identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",value):
        raise ValueError("invalid identifier")
    return value

def _label(value,limit=300):
    if not isinstance(value,str) or not 1<=len(value.strip())<=limit:
        raise ValueError("invalid label")
    return value.strip()

class RepairKnowledgeStore:
    COLLECTIONS={"devices","modules","parts","tools","fitment","fault_trees","questions","answers","corrections","media","outcomes","rishi_reviews"}
    def __init__(self,root):
        self.root=Path(root)/"repair-studio"/"knowledge"
        self.root.mkdir(parents=True,exist_ok=True)

    def add(self,collection,record):
        if collection not in self.COLLECTIONS:
            raise ValueError("unsupported collection")
        if not isinstance(record,dict):
            raise ValueError("record must be an object")
        record=dict(record)
        if collection=="devices":
            for key in ("manufacturer","model","device_kind"):
                record[key]=_label(record.get(key),160)
        elif collection=="modules":
            record["device_id"]=_identifier(record.get("device_id"))
            record["name"]=_label(record.get("name"))
        elif collection=="parts":
            record["name"]=_label(record.get("name"))
            record["part_number"]=_label(record.get("part_number"),160)
        elif collection=="fitment":
            for key in ("device_id","module_id","part_id"):
                record[key]=_identifier(record.get(key))
            record["verified"]=False
        elif collection=="fault_trees":
            record["category"]=_label(record.get("category"),100)
            nodes=record.get("nodes")
            if not isinstance(nodes,list) or not 1<=len(nodes)<=100:
                raise ValueError("fault tree requires 1-100 nodes")
            ids=set()
            for node in nodes:
                if not isinstance(node,dict):raise ValueError("invalid node")
                nid=_identifier(node.get("id"))
                if nid in ids:raise ValueError("duplicate node")
                ids.add(nid)
                _label(node.get("question") or node.get("action"))
                if node.get("action_type") not in (None,"observe","measure","refer_technician"):
                    raise PermissionError("unsafe fault tree action")
            for node in nodes:
                for target in (node.get("yes"),node.get("no")):
                    if target is not None and target not in ids:
                        raise ValueError("unknown fault tree edge")
        elif collection in {"questions","answers","corrections"}:
            record["text"]=_label(record.get("text"),4000)
            record["status"]="pending_review"
        elif collection=="media":
            record["kind"]=_label(record.get("kind"),32)
            if record["kind"] not in ("image","video","audio","diagram"):
                raise ValueError("invalid media type")
            record["sha256"]=_label(record.get("sha256"),64)
            if not re.fullmatch(r"[0-9a-f]{64}",record["sha256"]):
                raise ValueError("invalid media hash")
            record["uri"]=_label(record.get("uri"),1024)
        elif collection=="outcomes":
            record["case_id"]=_identifier(record.get("case_id"))
            record["result"]=_label(record.get("result"),100)
            record["evidence"]=_label(record.get("evidence"),2000)
            record["knowledge_status"]="candidate"
        elif collection=="rishi_reviews":
            record["case_id"]=_identifier(record.get("case_id"))
            record["rishi"]=_label(record.get("rishi"),100)
            record["evidence"]=_label(record.get("evidence"),2000)
            record["decision"]="pending_brahmagyan_exam"
        else:
            record["name"]=_label(record.get("name"))
        canonical=json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)
        digest=sha256((collection+":"+canonical).encode()).hexdigest()
        item={"id":collection[:3]+"_"+digest[:24],"collection":collection,"data":record,
              "created_at":datetime.now(timezone.utc).isoformat(),"verified":False}
        folder=self.root/collection
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(item["id"]+".json")
        try:
            with path.open("x",encoding="utf-8") as f:
                json.dump(item,f,ensure_ascii=False,indent=2)
        except FileExistsError:
            return json.loads(path.read_text(encoding="utf-8"))
        return item

    def list(self,collection,limit=100):
        if collection not in self.COLLECTIONS:raise ValueError("unsupported collection")
        folder=self.root/collection
        if not folder.exists():return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))[:max(1,min(int(limit),500))]]

    def compatible_parts(self,device_id,module_id):
        _identifier(device_id);_identifier(module_id)
        return [row for row in self.list("fitment",500)
                if row["data"]["device_id"]==device_id and row["data"]["module_id"]==module_id]

    def troubleshoot(self,tree_id,answers=None):
        _identifier(tree_id)
        tree=next((r for r in self.list("fault_trees",500) if r["id"]==tree_id),None)
        if tree is None:raise KeyError(tree_id)
        nodes={n["id"]:n for n in tree["data"]["nodes"]}
        current=tree["data"]["nodes"][0]["id"]
        answers=dict(answers or {})
        visited=set()
        while current is not None:
            if current in visited:raise ValueError("cyclic fault tree")
            visited.add(current)
            node=nodes[current]
            if current not in answers or answers[current] not in (True,False):
                return {"node":node,"status":"awaiting_observation","repair_authorized":False}
            current=node.get("yes") if answers[current] else node.get("no")
        return {"status":"observations_complete","repair_authorized":False}

    def brahmagyan_handoff(self,case_id,rishi,evidence):
        return self.add("rishi_reviews",{"case_id":case_id,"rishi":rishi,"evidence":evidence})
