"""Offline GARUDA Repair Studio coordinator: HAWKEYE observation -> case -> guide.

Original data only. External iFixit links are optional reference pointers.
No commands run, no implicit device authorization or knowledge promotion.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json
import re
from .garuda_repair_studio import create_repair_case, export_case
from .garuda_repair_guides import GuideStep, create_guide, save_guide
from .garuda_diagnostics import plan_diagnostics

class GarudaRepairWorkflow:
    def __init__(self, state_root, *, reference_provider=None):
        self.root=Path(state_root)
        self.reference_provider=reference_provider

    def open_case(self, *, device_id, device_kind, category, symptom, paired=False, evidence_refs=(), module=None):
        plan=plan_diagnostics(device_id,device_kind,paired=paired)
        case=create_repair_case(device_id,category,symptom,evidence_refs)
        folder=self.root/"repair-studio"/case.case_id
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/"case.json"
        if path.exists():
            existing=json.loads(path.read_text(encoding="utf-8"))
            if existing!=json.loads(json.dumps(asdict(case))):
                # JSON tuple/list normalization makes the comparison stable.
                raise ValueError("case id collision or changed case")
        else:
            export_case(case,path)
        references=[]
        reference_error=None
        if module and self.reference_provider is not None:
            try:
                card=self.reference_provider.hawkeye_module_card(device_id,module,measured_evidence=evidence_refs)
                references=card["repair_references"]
            except (OSError,ValueError,RuntimeError,PermissionError,KeyError,TypeError) as exc:
                reference_error=type(exc).__name__
        return {"case_id":case.case_id,"case":asdict(case),
                "diagnostic_plan":asdict(plan),"references":references,
                "reference_error":reference_error,"state":"awaiting_diagnostics",
                "repair_authorized":False,"knowledge_verified":False}

    def create_original_guide(self, *, model, title, difficulty, minutes, steps, source="first-party technician"):
        guide=create_guide(model,title,difficulty,minutes,
                           [GuideStep(**s) for s in steps],source=source)
        save_guide(guide,self.root/"repair-studio"/"guides")
        return {"guide_id":guide.guide_id,"status":"draft","steps":len(guide.steps)}

    def module_summary(self, *, device_model, module, evidence_refs=()):
        if self.reference_provider is None:
            return {"device_model":device_model,"module":module,"observations":list(evidence_refs),
                    "repair_references":[],"reference_error":"provider_not_configured",
                    "repair_authorized":False,"diagnosis":"not_established"}
        try:
            return self.reference_provider.hawkeye_module_card(device_model,module,measured_evidence=evidence_refs)
        except (OSError,ValueError,RuntimeError,PermissionError,KeyError,TypeError) as exc:
            return {"device_model":device_model,"module":module,"observations":list(evidence_refs),
                    "repair_references":[],"reference_error":type(exc).__name__,
                    "repair_authorized":False,"diagnosis":"not_established"}
