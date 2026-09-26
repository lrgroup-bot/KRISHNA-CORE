from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class CreatorStep:
    step_id:str
    capability:str
    provider_hint:str=""
    requires_paid:bool=False
    requires_owner_approval:bool=False
    def as_dict(self):return asdict(self)


class CreatorWorkflowPlanner:
    """Free-first media workflow graph; it plans but does not start models."""

    VERSION="creator-workflow-v1"

    def plan(self, goal="campaign"):
        steps=[
            CreatorStep("brief","general","mobile-openrouter-zero"),
            CreatorStep("reference","media_reference","local"),
            CreatorStep("image","image_generation","free/local-provider"),
            CreatorStep("upscale","image_upscale","free/local-provider"),
            CreatorStep("motion","avatar_motion","existing-avatar-fabric"),
            CreatorStep("voice","voice","free/local-provider"),
            CreatorStep("lipsync","avatar_lipsync","musetalk"),
            CreatorStep("render","media_render","local"),
            CreatorStep("qc","media_qc","suryadev/chandradev"),
        ]
        return {
            "goal":str(goal),
            "steps":[x.as_dict() for x in steps],
            "automatic_paid_fallback":False,
            "resident_models_started":0,
            "execution":"capability providers are invoked only when a job reaches that step",
        }

    def status(self):
        return {"component":"KRISHNA Creator Workflow Planner","version":self.VERSION,**self.plan("status")}
