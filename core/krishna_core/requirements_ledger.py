from __future__ import annotations
import json
from pathlib import Path

class RequirementsLedger:
    """Machine-readable contract distilled from KRISHNA project conversations."""
    def __init__(self,path=None):
        self.path=Path(path or Path(__file__).resolve().parents[1]/"requirements"/"krishna_chat_requirements.json")
    def load(self):
        raw=json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw,dict) or raw.get("schema") not in {1,2}:
            raise ValueError("unsupported KRISHNA requirements ledger schema")
        return raw
    def snapshot(self):
        raw=self.load()
        groups=list(raw.get("groups") or [])
        count=sum(len(g.get("requirements") or []) for g in groups)
        return {
            "schema":raw.get("schema"),
            "version":raw.get("version"),
            "source":raw.get("source"),
            "non_negotiables":list(raw.get("non_negotiables") or []),
            "groups":groups,
            "release_gates":list(raw.get("release_gates") or []),
            "status_definitions":dict(raw.get("status_definitions") or {}),
            "definition_of_done":list(raw.get("definition_of_done") or []),
            "delivery_pipeline":list(raw.get("delivery_pipeline") or []),
            "implementation_index":list(raw.get("implementation_index") or []),
            "requirement_count":count,
            "group_count":len(groups),
        }
    def prompt_contract(self):
        data=self.snapshot()
        rules="\n".join("- "+x for x in data["non_negotiables"])
        return "Canonical KRISHNA requirements (user-approved project contract):\n"+rules

    def search(self,query):
        q=str(query or "").strip().lower()
        data=self.snapshot()
        if not q:return data
        matches=[]
        for group in data["groups"]:
            for item in group.get("requirements") or []:
                if q in item.lower() or q in str(group.get("title","")).lower():
                    matches.append({"group":group.get("id"),"title":group.get("title"),"requirement":item})
        for item in data["non_negotiables"]:
            if q in item.lower():matches.append({"group":"non_negotiables","title":"Non-negotiables","requirement":item})
        return {"query":q,"matches":matches,"count":len(matches),"version":data["version"]}
