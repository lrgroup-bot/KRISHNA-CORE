from krishna_core.rishi_council import RishiCouncil
from krishna_core.lab_bot import LabBot

def test_tvasta_and_marichi_are_permanent_specialists(tmp_path):
    council = RishiCouncil()
    tvasta = council.get("tvasta")
    marichi = council.get("marichi")
    assert "biological computing" in tvasta["domains"]
    assert "computer architecture" in tvasta["domains"]
    assert "rocket science" in marichi["domains"]
    assert "reusable launch vehicles" in marichi["domains"]

def test_lab_research_proposal_captures_discovery_fields(tmp_path):
    lab = LabBot(tmp_path)
    row = lab.request({
        "rishi": "tvasta",
        "domain": "computing",
        "mode": "simulation",
        "hypothesis": "A new computing substrate may improve a defined workload.",
        "objective": "Compare the proposed substrate with a conventional baseline.",
        "controls": ["conventional baseline"],
        "measurements": ["accuracy", "energy estimate"],
        "success_criteria": ["predefined improvement without loss of validity"],
        "novelty": "cross-domain computing substrate",
        "prior_work": ["paper:example"],
        "collaborating_rishis": ["gautama", "bharadvaja"],
        "failure_criteria": ["cannot reproduce claimed advantage"],
        "contradictory_evidence": ["record negative and conflicting studies"],
        "ip_patent_refs": ["patent-search-required"],
        "possible_applications": ["low-energy adaptive computing"],
        "what_else_can_this_become": ["new sensing-compute interface"],
        "technology_maturity": "research prototype",
    })
    p = row["proposal"]
    assert p["technology_maturity"] == "research prototype"
    assert p["collaborating_rishis"] == ["gautama", "bharadvaja"]
    assert p["what_else_can_this_become"]
