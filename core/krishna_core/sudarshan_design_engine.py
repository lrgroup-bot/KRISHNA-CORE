"""Sudarshan Design Engine: selective skills, design genome, drift and acceptance."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,time
@dataclass
class DesignJob:
 kind:str; reference_image:bool=False; existing_ui:bool=False; agentic_browser:bool=False
class SkillRouter:
 def select(self,j:DesignJob):
  s=[]
  if j.kind in {"frontend","mobile","dashboard"}: s+=["web-design","taste-skill"]
  if j.existing_ui:s+=["redesign-existing-projects"]
  if j.reference_image:s+=["image-to-code"]
  s+=["playwright-cli"]
  if j.agentic_browser:s+=["stagehand"]
  return list(dict.fromkeys(s))
class DesignGenome:
 def __init__(self,**kw):
  self.data={"schema":"krishna.design-genome.v1","identity":{},"color":{},"typography":{},"geometry":{},"depth":{},"motion":{},"components":{},**kw}
 def save(self,path):
  Path(path).write_text(json.dumps(self.data,indent=2),encoding="utf-8")
class DesignDrift:
 def compare(self,expected:dict,actual:dict):
  keys=set(expected)|set(actual);diff={k:{"expected":expected.get(k),"actual":actual.get(k)} for k in keys if expected.get(k)!=actual.get(k)}
  return {"pass":not diff,"differences":diff}
class AcceptanceGovernor:
 REQUIRED=("functional","visual","responsive","accessibility","keyboard","loading","error","empty","console","performance","security")
 def evaluate(self,checks:dict):
  failed=[x for x in self.REQUIRED if checks.get(x) is not True]
  return {"verified":not failed,"failed":failed,"owner":"Sudarshan"}
class SudarshanDesignEngine:
 def __init__(self,root):
  self.root=Path(root);self.router=SkillRouter();self.acceptance=AcceptanceGovernor()
 def plan(self,job:DesignJob):
  return {"owner":"Sudarshan","skills":self.router.select(job),"krishna_context":"summary-only","created_at":time.time()}
