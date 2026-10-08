from __future__ import annotations

"""Acquisition routing for SURYADEV/CHANDRADEV and public data sources."""

SOURCE_PRIORITY=("public_api","direct_text","document","repository","audio_video","visual_screen")
PUBLIC_SOURCE_CLASSES={
    "openalex":{"kind":"scholarly_graph","free_public":True},
    "crossref":{"kind":"scholarly_metadata","free_public":True},
    "github":{"kind":"software_repositories","free_public":True,"auth_improves_limits":True},
    "youtube_data":{"kind":"video_discovery_metadata","free_quota":True},
    "official_web":{"kind":"primary_authoritative_web","free_public":True},
}

def acquisition_route(*, api_available=False, direct_text=False, document=False,
                      repository=False, audio_video=False, visual_required=False):
    if api_available:return {"worker":"SURYADEV","mode":"public_api","chandradev":False}
    if direct_text:return {"worker":"SURYADEV","mode":"direct_text","chandradev":False}
    if document:return {"worker":"SURYADEV","mode":"document","chandradev":False}
    if repository:return {"worker":"SURYADEV","mode":"repository","chandradev":False}
    if audio_video and not visual_required:return {"worker":"SURYADEV","mode":"audio_video_asr","chandradev":False}
    if visual_required:return {"worker":"CHANDRADEV","mode":"visual_screen","chandradev":True}
    return {"worker":"SURYADEV","mode":"web_discovery","chandradev":False}

def device_capacity_plan(*, queued_io_jobs, queued_visual_jobs, io_slots_per_node=4,
                         visual_slots_per_node=1, max_nodes=64):
    io=max(0,int(queued_io_jobs)); visual=max(0,int(queued_visual_jobs))
    io_slots=max(1,int(io_slots_per_node)); visual_slots=max(1,int(visual_slots_per_node))
    io_nodes=(io+io_slots-1)//io_slots
    visual_nodes=(visual+visual_slots-1)//visual_slots
    requested=min(max(0,int(max_nodes)),io_nodes+visual_nodes)
    return {
        "requested_nodes":requested,"io_nodes":io_nodes,"visual_nodes":visual_nodes,
        "purchase_required":False,
        "policy":"schedule onto healthy existing nodes first; add hardware only after measured sustained queue pressure",
    }

def learning_value(*, relevance, authority, novelty, evidence_uniqueness,
                   current_importance, cross_domain_value, estimated_cost):
    benefit=sum(max(0.0,min(1.0,float(x))) for x in (
        relevance,authority,novelty,evidence_uniqueness,current_importance,cross_domain_value))
    return round(benefit/max(.25,float(estimated_cost)),6)
