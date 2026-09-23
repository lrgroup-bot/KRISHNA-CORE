from __future__ import annotations

"""Sudarshan design planning, design-genome drift and hard acceptance gates."""

from dataclasses import dataclass
from pathlib import Path
import json
import time

from .vishvakarma_curriculum import CURRICULUM


@dataclass(frozen=True)
class DesignJob:
    kind:str
    reference_image:bool=False
    existing_ui:bool=False
    agentic_browser:bool=False
    topic:str=""


class SkillRouter:
    def select(self,j:DesignJob):
        kind=str(j.kind or "").strip().lower()
        skills=[]
        if kind in {"frontend","mobile","dashboard","ui","ux","component"}:
            skills+=["web-design","Taste Skill","design-systems"]
        if j.existing_ui:
            skills+=["redesign-existing-projects"]
        if j.reference_image:
            skills+=["image-to-code"]
        skills+=["Playwright"]
        if j.agentic_browser:
            skills+=["Stagehand"]
        return list(dict.fromkeys(skills))


class DesignGenome:
    SCHEMA="krishna.design-genome.v2"
    SECTIONS=("identity","color","typography","geometry","depth","motion","components","accessibility")

    def __init__(self,**kw):
        self.data={"schema":self.SCHEMA,**{name:{} for name in self.SECTIONS}}
        for key,value in kw.items():
            if key in self.SECTIONS:
                self.data[key]=dict(value or {})

    def save(self,path):
        p=Path(path)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(self.data,indent=2,ensure_ascii=False),encoding="utf-8")
        return str(p)


class DesignDrift:
    @staticmethod
    def _flatten(value,prefix=""):
        out={}
        if isinstance(value,dict):
            for key,item in value.items():
                child=f"{prefix}.{key}" if prefix else str(key)
                out.update(DesignDrift._flatten(item,child))
        else:
            out[prefix]=value
        return out

    def compare(self,expected:dict,actual:dict):
        a=self._flatten(expected or {})
        b=self._flatten(actual or {})
        keys=set(a)|set(b)
        diff={
            k:{"expected":a.get(k),"actual":b.get(k)}
            for k in sorted(keys) if a.get(k)!=b.get(k)
        }
        return {"pass":not diff,"differences":diff,"difference_count":len(diff)}


class AcceptanceGovernor:
    REQUIRED=(
        "functional","visual","responsive","accessibility","keyboard",
        "loading","error","empty","console","performance","security",
    )
    def evaluate(self,checks:dict):
        checks=dict(checks or {})
        failed=[x for x in self.REQUIRED if checks.get(x) is not True]
        return {
            "verified":not failed,
            "failed":failed,
            "required":list(self.REQUIRED),
            "owner":"Sudarshan",
        }


class SudarshanDesignEngine:
    VERSION="sudarshan-design-v2"

    def __init__(self,root,knowledge=None):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.router=SkillRouter()
        self.acceptance=AcceptanceGovernor()
        self.drift=DesignDrift()
        self.knowledge=knowledge

    def plan(self,job:DesignJob):
        topic=str(job.topic or job.kind or "design").strip()
        findings=[]
        if self.knowledge is not None:
            try:
                findings=self.knowledge.retrieve(topic,limit=12,verified_only=True)
            except Exception:
                findings=[]
        return {
            "owner":"Sudarshan",
            "knowledge_owner":"Rishi Vishvakarma",
            "skills":self.router.select(job),
            "curriculum_available":sorted(CURRICULUM),
            "retrieved_verified_findings":findings,
            "krishna_context":"summary-only",
            "created_at":time.time(),
        }

    def status(self):
        return {
            "version":self.VERSION,
            "skills":sorted(CURRICULUM),
            "hard_acceptance_checks":list(self.acceptance.REQUIRED),
            "knowledge_bound":self.knowledge is not None,
            "authority":"Sudarshan executes/verifies; Vishvakarma curates design knowledge",
        }
