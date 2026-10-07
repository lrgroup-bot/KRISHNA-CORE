from core.krishna.lr_qaqc_observer import LRQAQCObservation, build_lr_qaqc_request, decide_qaqc_gate, human_brief

def test_krishna_is_primary_authority():
    p=build_lr_qaqc_request(LRQAQCObservation("p","research","improve outcome"),company_id="lr-commerce",domain="commerce")
    assert p["authority"]["krishna"]=="PRIMARY_SYSTEM_AUTHORITY"
    assert p["authority"]["human_contact"]=="KRISHNA_ONLY"

def test_protected_action_requires_krishna_to_human_path():
    x=decide_qaqc_gate(gate="GO",protected_action="purchase",evidence_complete=True,conclusion="ready")
    assert x["decision"]=="ASK_HUMAN_THROUGH_KRISHNA"
    assert x["advance"] is False

def test_human_brief_has_krishna_as_speaker():
    x=human_brief(project_id="p",conclusion="repair",recommendation="replace creative")
    assert x["speaker"]=="KRISHNA"
    assert x["specialist_direct_contact"] is False
