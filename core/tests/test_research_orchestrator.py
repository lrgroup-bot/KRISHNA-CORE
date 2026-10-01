from krishna_core.research_orchestrator import research_execution_plan,provenance_record
from krishna_core.science_atlas import FIELD_RISHI_MAP,KEYWORD_TEAMS

def test_orchestrator_joins_research_layers():
    p=research_execution_plan(question="new rocket avionics computer",rishi_team=["marichi","tvasta","gautama"],
        scientific=True,visual=True,implementation=True,contradictions=2,unresolved=3,current_shishyas=4,audio_video=True)
    assert p["deadline"]["budget_seconds"]==60
    assert p["collectors"]["streaming_collection"] is True
    assert p["acquisition"]["worker"]=="CHANDRADEV"
    assert p["provenance_required"] and p["brahma_qc_required"]
    assert p["shishya_scaling"]["action"] in {"expand","maintain","stop_expansion","contract","hold"}

def test_provenance_keeps_derivation_agent_and_version():
    p=provenance_record(entity_id="claim-1",activity="synthesis",agent="gautama",
                        sources=["doi:1","repo:2"],generated_at="2026-10-01",
                        parent_entities=["finding-1"],content_hash="abc",version="2")
    assert p["derived_from"]==["finding-1"]
    assert p["w3c_prov_mapping"]["derivation"]=="wasDerivedFrom"
    assert p["version"]=="2"

def test_new_rishis_are_reachable_from_atlas():
    assert FIELD_RISHI_MAP["computer science"][0]=="tvasta"
    assert "tvasta" in FIELD_RISHI_MAP["engineering"]
    rocket=[team for keys,team in KEYWORD_TEAMS if "rocket" in keys]
    assert rocket and rocket[0][0]=="marichi"
