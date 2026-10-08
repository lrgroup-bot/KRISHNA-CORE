from krishna_core.knowledge_laws import knowledge_law_gate,invalidate_dependents
from krishna_core.provider_governor import ProviderGovernor,provider_failure_action

def test_high_impact_cannot_become_real_world_verified_from_web_consensus():
    rows=[
      {"source_family":"paper-a","reality_level":"reported","gate":"citation","gate_passed":True},
      {"source_family":"paper-b","reality_level":"inferred","gate":"contradiction","gate_passed":True},
    ]
    g=knowledge_law_gate(claim_type="verified",evidence_records=rows,
        required_gates={"citation","contradiction"},high_impact=True)
    assert not g["allowed"] and "R10" in g["violations"]

def test_retraction_and_staleness_block_promotion():
    rows=[{"source_family":"a","reality_level":"reported","retracted":True},
          {"source_family":"b","reality_level":"reported"}]
    g=knowledge_law_gate(claim_type="verified",evidence_records=rows)
    assert not g["allowed"] and "R8" in g["violations"]

def test_invalidation_propagates_through_derivation_graph():
    edges=[{"parent":"paper","child":"claim"},{"parent":"claim","child":"gyan"},{"parent":"other","child":"x"}]
    r=invalidate_dependents("paper",edges,"retracted")
    assert r["affected"]==["claim","gyan"]

def test_provider_governor_respects_concurrency_and_machine_pressure():
    g=ProviderGovernor()
    assert g.permit("crossref_public",active=0,machine_pressure=.4)["allowed"]
    assert not g.permit("crossref_public",active=1,machine_pressure=.4)["allowed"]
    assert not g.permit("crossref_polite",active=0,machine_pressure=.86)["allowed"]

def test_429_backs_off_and_eventually_breaks_circuit():
    a=provider_failure_action(429,6)
    assert a["retry"] and a["reduce_concurrency"] and a["circuit_breaker"]
