from __future__ import annotations

"""End-to-end BRAHMAGYAN research orchestration contract.

Pure planning layer: joins council routing, deadline lanes, collectors, acquisition,
resource governance and provenance requirements without bypassing existing authority gates.
"""

from .research_deadline import deadline_plan
from .brahmagyan_collectors import collector_team_plan
from .knowledge_acquisition import acquisition_route
from .live_knowledge import source_requirement_plan
from .research_team_governor import research_team_decision
from .knowledge_laws import LAWS

def research_execution_plan(*, question, rishi_team, scientific=False, visual=False,
                            implementation=False, regulated=False, resource_pressure=0.0,
                            contradictions=0, unresolved=0, current_shishyas=0,
                            api_available=False, direct_text=False, document=False,
                            repository=False, audio_video=False):
    team=list(dict.fromkeys(str(x).strip().lower() for x in (rishi_team or []) if str(x).strip()))
    sources=source_requirement_plan(question,live=True,visual=visual,implementation=implementation,
                                    scientific=scientific,regulated=regulated)
    deadline=deadline_plan(question)
    collectors=collector_team_plan(team,contradictions=contradictions,unresolved=unresolved,
                                   resource_pressure=resource_pressure)
    acquisition=acquisition_route(api_available=api_available,direct_text=direct_text,document=document,
                                  repository=repository,audio_video=audio_video,visual_required=visual)
    scaling=research_team_decision(current=current_shishyas,uncovered_specialties=unresolved,
                                   contradictions=contradictions,resource_pressure=resource_pressure)
    return {
        "question":str(question or ""),"rishi_team":team,"deadline":deadline,
        "source_requirements":sources,"collectors":collectors,"acquisition":acquisition,
        "shishya_scaling":scaling,
        "provenance_required":True,"atomic_claims_required":True,"contradiction_check_required":True,
        "freshness_check_required":True,"negative_evidence_required":True,
        "brahma_qc_required":True,"gyan_promotion_requires_verified_evidence":True,
        "non_bypassable_laws":LAWS,
        "execution_rule":"run independent lanes concurrently under shared resource governance; synthesize only evidence completed by deadline and mark the rest unresolved",
    }

def provenance_record(*, entity_id, activity, agent, sources, generated_at,
                      parent_entities=None, content_hash="", version="1"):
    if not entity_id or not activity or not agent:
        raise ValueError("entity_id, activity and agent are required")
    src=[str(x) for x in (sources or []) if str(x).strip()]
    return {
        "schema":"krishna.provenance.v1","entity":str(entity_id),"activity":str(activity),
        "agent":str(agent),"sources":src,"generated_at":generated_at,
        "derived_from":[str(x) for x in (parent_entities or []) if str(x).strip()],
        "content_hash":str(content_hash or ""),"version":str(version),
        "w3c_prov_mapping":{"entity":"entity","activity":"activity","agent":"agent",
                            "derivation":"wasDerivedFrom","association":"wasAssociatedWith"},
    }
