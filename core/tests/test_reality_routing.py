from krishna_core.reality_grounding import observation_escalation
from krishna_core.field_perception import FieldPerceptionPolicy

def test_physical_observation_routes_by_environment_without_loading_krishna():
    pc=observation_escalation(physical_state_matters=True,environment="pc")
    mobile=observation_escalation(physical_state_matters=True,environment="mobile")
    assert pc["preferred_worker"]=="CHANDRADEV"
    assert mobile["preferred_worker"]=="HAWKEYE"
    assert not pc["krishna_continuous_perception"] and not mobile["krishna_continuous_perception"]

def test_bhoomiputra_is_declared_compatibility_only():
    s=FieldPerceptionPolicy.status()
    assert s["owner"]=="HAWKEYE field perception"
    assert "compatibility" in s["legacy_bhoomiputra_role"]
